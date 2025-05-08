import os
import json
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import boto3
from botocore.exceptions import ClientError
import logging


logger = logging.getLogger()
logger.setLevel(logging.INFO)


# MongoDB Configuration
MONGODB_URI = os.environ.get('MONGODB_URI')


# AWS Configuration
batch_client = boto3.client('batch')


# CORS header
cors_headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'OPTIONS,GET,POST'
}


def create_job_definition(job_definition_name, ecr_image_uri):
    try:
        logger.info(f"Checking if job definition: '{job_definition_name}' already exists...")
        existing_defs = batch_client.describe_job_definitions(
            jobDefinitionName=job_definition_name,
            status='ACTIVE'
        )
        
        if existing_defs['jobDefinitions']:
            logger.info(f"Job definition '{job_definition_name}' already exists.")
            return {
                'ResponseMetadata': {'HTTPStatusCode': 200},
                'status': 'ALREADY_EXISTS'
            }
    
    except ClientError as e:
        logger.exception("Error describing job definitions.")
        raise

    logger.info(f"Job Definition '{job_definition_name}' does not exist. Proceeding to register.")

    try:
        logger.info(f"Registering job definition: {job_definition_name} with image: {ecr_image_uri}")
        response = batch_client.register_job_definition(
            jobDefinitionName=job_definition_name,
            platformCapabilities=['FARGATE'],
            type='container',
            containerProperties={
                'image': ecr_image_uri,
                'command': ['python', 'post_product.py'],
                "executionRoleArn": "arn:aws:iam::654654551634:role/AWSBatchExecutionRole",
                "networkConfiguration": {
                    "assignPublicIp": "ENABLED"
                },
                "resourceRequirements": [
                    {
                        "value": "1.0",
                        "type": "VCPU"
                    },
                    {
                        "value": "2048",
                        "type": "MEMORY"
                    }
                ]
            },
            # The following parameter allows environment variables to be passed
            # from the job submission to the container
            propagateTags=True
        )

        logger.info(f"Job definition registered successfully: {response}")
        return response
    
    except ClientError:
        logger.exception("Failed to register job definition.")
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
                'headers': cors_headers,
                'body': json.dumps({'error': 'Missing path parameters: client and connector are required'})
            }
        
        client_name = client_name.lower()
        connector = connector.lower()

        logger.info(f"Processing request of client: {client_name} for connector: {connector}")

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
            
            logger.info(f"Fetching the job definition name and ECR Image URI from the configuraiton collection for the connector: {connector}")
            job_definition_name = config_doc.get(f"{connector.upper()}_JOB_DEFINITION_NAME")
            ecr_image_uri = config_doc.get(f"{connector.upper()}_ECR_IMAGE_URI")

            if not job_definition_name or not ecr_image_uri:
                logger.warning(f"Job Definition name or ECR Image URI is missing in configuration document for connector: {connector}")
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({'error': f'Job definition name or ECR Image URI is missing in configuration document for connector: {connector}'})
                }
            
            logger.info(f"Fetched job definition name: {job_definition_name} and ECR Image URI: {ecr_image_uri}")

            logger.info(f"Creating Job Definition: {job_definition_name} with ECR Image URI: {ecr_image_uri}")
            response = create_job_definition(job_definition_name=job_definition_name, ecr_image_uri=ecr_image_uri)
            status_code = response['ResponseMetadata']['HTTPStatusCode']
            status = response.get('status', 'CREATED')

            logger.info(f"Job Definition creation result: {status}")
            return {
                'statusCode': status_code,
                'headers': cors_headers,
                'body': json.dumps({'status': status})
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
        return  {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': str(e)})
        }
