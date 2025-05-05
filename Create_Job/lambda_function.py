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


def submit_job(job_name, job_queue, job_definition, connector, client_key):
    try:
        logger.info(f"Submitting job: {job_name} to queue: {job_queue} using definition: {job_definition}")

        job_params = {
            'jobName': job_name,
            'jobQueue': job_queue,
            'jobDefinition': job_definition,
            'containerOverrides': {
                'environment': [
                    {"name": "TARGET_CLIENT_KEY", "value": client_key}
                ]
            }
        }

        match connector.lower():
            case 'shopify':
                job_params['containerOverrides']['command'] = ["python", "post_product.py"]
            
            case 'walmart':
                job_params['containerOverrides']['command'] = ["python", "main.py"]
            
            case 'lazada':
                job_params['containerOverrides']['command'] = ["python", "create_lazada_product.py"]
            case _:
                logger.warning(f"Unsupported connector: {connector}")
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': f'Unsupported connector: {connector}'})
                }
            
        response = batch_client.submit_job(**job_params)
        logger.info(f"Job Submitted Successfully: {response}")
        return response
    
    except ClientError:
        logger.exception("Failed to submit AWS Batch job.")
        raise


def lambda_handler(event, context):
    try:
        # extract path parameters
        path_params = event.get("pathParameters", {})
        client_name = path_params.get("client")
        connector = path_params.get("connector")

        if not client_name or not connector:
            logger.warning("Missing path parameters")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing path parameters: client and connector are required'})
            }
        
        client_name = client_name.lower()
        connector = connector.lower()

        logger.info(f"Processing request of client: {client_name} for connector: {connector}")

        # connect to MongoDB
        client = MongoClient(MONGODB_URI)
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
                'body': json.dumps({'error': f"Job name or Job definition name or Job Queue name is missing in configuration document for connector: {connector}"})
            }
        
        logger.info(f"Fetched job name: {job_name}, job defintion name: {job_definition} and job queue name: {job_queue}")

        response = submit_job(job_name=job_name, job_queue=job_queue, job_definition=job_definition, connector=connector, client_key=client_name)
        job_id = response.get('jobId')
        return {
            'statusCode': 200,
            'body': json.dumps({
                'status': 'SUMBITTED',
                'jobName': job_name,
                'jobId': job_id
            })
        }
    
    except ConnectionFailure:
        logger.exception("Failed to connect to MongoDB")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Failed to connect to MongoDB'})
        }
    
    except Exception as e:
        logger.exception("Unhandled exception occurred")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
