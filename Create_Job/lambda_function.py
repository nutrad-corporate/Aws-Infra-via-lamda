import os
import json
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import boto3
from botocore.exceptions import ClientError
import logging


logger = logging.getLogger()
logger.setLevel(logging.INFO)


# MongoDB Configuraiton
MONGODB_URI = os.environ.get('MONGODB_URI')


# AWS Configuration
batch_client = boto3.client('batch')
events_client = boto3.client('events')


# CORS header
cors_headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'OPTIONS,GET,POST'
}


def submit_job(job_name, job_queue, job_definition, client_key, command):
    try:
        logger.info(f"Submitting job: {job_name} to queue: {job_queue} using definition: {job_definition}")

        job_params = {
            'jobName': job_name,
            'jobQueue': job_queue,
            'jobDefinition': job_definition,
            'containerOverrides': {
                'environment': [
                    {"name": "TARGET_CLIENT_KEY", "value": client_key}
                ],
                'command': command
            }
        }
            
        response = batch_client.submit_job(**job_params)
        logger.info(f"Job Submitted Successfully: {response}")
        return response
    
    except ClientError:
        logger.exception("Failed to submit AWS Batch job.")
        raise


def create_recurring_job_rule(rule_name, schedule_expression, job_name, job_queue, job_definition, client_key, command, role_arn):
    try:
        logger.info(f"Creating/updating EventBridge rule: {rule_name}")

        # Step 1: Create or update the EventBridge rule
        rule_response = events_client.put_rule(
            Name=rule_name,
            ScheduleExpression=schedule_expression,
            State='ENABLED',
            Description='Recurring rule to trigger Batch job as per schedule expression',
            RoleArn=role_arn
        )

        logger.info(f"Rule created/updated: {rule_response}")
        
        # Create a proper JSON input with the containerOverrides
        input_template = {
            "ContainerOverrides": {
                "Command": command,
                "Environment": [
                    {"Name": "TARGET_CLIENT_KEY", "Value": client_key}
                ]
            }
        }
        
        # Step 2: Define the target Batch job details
        target = {
            'Id': '1',
            'Arn': f'arn:aws:batch:ap-south-1:654654551634:job-queue/{job_queue}',
            'RoleArn': role_arn,
            'BatchParameters': {
                "JobName": job_name,
                "JobDefinition": job_definition
            },
            # Use the direct input format instead of InputTransformer
            'Input': json.dumps(input_template)
        }

        # Step 3: Set the target
        target_response = events_client.put_targets(
            Rule=rule_name,
            Targets=[target]
        )

        logger.info(f"Target set for rule: {target_response}")

        return rule_response
    
    except ClientError:
        logger.exception("Failed to create or update EventBridge rule")
        raise


def lambda_handler(event, context):
    try:
        # extract path parameters
        path_params = event.get("pathParameters", {})
        job_type = path_params.get("job_type")
        client_name = path_params.get("client")
        connector = path_params.get("connector")

        if not client_name or not connector or not job_type:
            logger.warning("Missing path parameters")
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Missing path parameters: client, connector and job_type are required'})
            }
        
        job_type = job_type.lower()
        client_name = client_name.lower()
        connector = connector.lower()

        logger.info(f"Processing job type: {job_type} request of client: {client_name} for connector: {connector}")

        body = event.get("body")
        if isinstance(body, str):
            body = json.loads(body)
        command = body.get("command")

        if not command:
            logger.warning("Missing command in request body")
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Missing command in request body'})
            }
        
        if not isinstance(command, list):
            logger.warning("Command must be a list")
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Command must be a list'})
            }

        # connect to MongoDB
        with MongoClient(MONGODB_URI) as client:
            client.admin.command('ping')

            # select the appropriate database and configuration collection
            logger.info("Connecting to the database")
            db = client[client_name]
            config_collection = db[f'{client_name}_Configuration']
            config_doc = config_collection.find_one()

            if not config_doc:
                logger.warning(f"No configuration found for client: {client_name}")
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({'error': f'No configuration found for client: {client_name}'})
                }
            
            logger.info(f"Fetching the job name, job definition name and job queue name from the configuration collection for the connector: {connector}")
            job_name = config_doc.get(f"{connector.upper()}_JOB_NAME")
            job_definition = config_doc.get(f"{connector.upper()}_JOB_DEFINITION_NAME")
            job_queue = config_doc.get(f"{connector.upper()}_JOB_QUEUE_NAME")

            if not job_name or not job_definition or not job_queue:
                logger.warning(f"Job name or Job definition name or Job Queue name is missing in configuration document for connector: {connector}")
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({'error': f"Job name or Job definition name or Job Queue name is missing in configuration document for connector: {connector}"})
                }
            
            logger.info(f"Fetched job name: {job_name}, job defintion name: {job_definition} and job queue name: {job_queue}")

            match job_type:
                case 'submit':
                    response = submit_job(
                        job_name=job_name,
                        job_queue=job_queue,
                        job_definition=job_definition,
                        client_key=client_name,
                        command=command
                    )
                    job_id = response.get('jobId')
                    return {
                        'statusCode': 200,
                        'headers': cors_headers,
                        'body': json.dumps({'status': 'SUBMITTED', 'jobName': job_name, 'jobId': job_id})
                    }
                
                case 'check_feed_status':
                    rule_name = config_doc.get("WALMART_CHECK_FEED_STATUS_RULE_NAME")
                    if not rule_name:
                        logger.warning("Missing rule name in configuration for check_feed_status")
                        return {
                            'statusCode': 400,
                            'headers': cors_headers,
                            'body': json.dumps({'error': 'Missing rule name in configuration for check_feed_status'})
                        }
                    
                    schedule_expression = "rate(5 minutes)"

                    eventbridge_role_arn = os.environ.get('EVENTBRIDGE_ROLE_ARN')
                    if not eventbridge_role_arn:
                        return {
                            'statusCode': 500,
                            'headers': cors_headers,
                            'body': json.dumps({'error': 'Missing EVENTBRIDGE_ROLE_ARN environment variable'}) 
                        }
                    
                    create_recurring_job_rule(
                        rule_name=rule_name,
                        schedule_expression=schedule_expression,
                        job_name=job_name,
                        job_queue=job_queue,
                        job_definition=job_definition,
                        client_key=client_name,
                        command=command,
                        role_arn=eventbridge_role_arn
                    )

                    return {
                        'statusCode': 200,
                        'headers': cors_headers,
                        'body': json.dumps({'status': 'SCHEDULED', 'ruleName': rule_name, 'jobName': job_name})
                    }

                case _:
                    return {
                        'statusCode': 400,
                        'headers': cors_headers,
                        'body': json.dumps({'error': f'Unsupported job_type: {job_type}'})
                    }                          
    
    except ConnectionFailure:
        logger.exception("Failed to connect to MongoDB")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Failed to connect to MongoDB'})
        }
    
    except Exception as e:
        logger.exception("Unhandled exception occurred")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': str(e)})
        }
