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


def create_job_queue(job_queue_name, compute_environment_name):
    try:
        # Check if job queue already exists
        logger.info(f"Describing job queue: {job_queue_name}")
        existing_queues = batch_client.describe_job_queues(
            jobQueues=[job_queue_name]
        )
        logger.info(f"Existing job queues: {existing_queues}")

        if existing_queues['jobQueues']:
            logger.info(f"Job queue '{job_queue_name}' already exists.")
            return {
                'ResponseMetadata': {'HTTPStatusCode': 200},
                'status': 'ALREADY_EXISTS'
            }
    
    except ClientError as e:
        logger.exception("Error describing job queues.")
        raise

    logger.info(f"Job queue: '{job_queue_name}' does not exist. Proceeding to create.")

    try:
        response = batch_client.create_job_queue(
            jobQueueName=job_queue_name,
            priority=1,
            state='ENABLED',
            computeEnvironmentOrder=[
                {
                    'order': 1,
                    'computeEnvironment': compute_environment_name
                }
            ]
        )

        logger.info(f"Create job queue response: {response}")
        return response
    
    except ClientError as e:
        logger.exception("Failed to create job queue.")
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
            
            logger.info(f"Fetching the job queue name from the configuration collection for the connector: {connector}")
            job_queue_name = config_doc.get(f"{connector.upper()}_JOB_QUEUE_NAME")
            compute_environment_name = config_doc.get(f"{connector.upper()}_COMPUTE_ENVIRONMENT_NAME")

            if not job_queue_name or not compute_environment_name:
                logger.warning(f"Job Queue name or Compute Environment name is missing in configuration document for connector: {connector}")
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({"error": f"Job queue name or Compute Environment name is missing in configuration document for connector: {connector}"})
                }
            
            logger.info(f"Fetched job queue name: {job_queue_name}")

            logger.info(f"Creating Job Queue: {job_queue_name} with compute environment: {compute_environment_name}")
            response = create_job_queue(job_queue_name=job_queue_name, compute_environment_name=compute_environment_name)
            status_code = response['ResponseMetadata']['HTTPStatusCode']
            status = response.get('status', 'CREATED')

            logger.info(f"Job queue creation result: {status}")
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
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': str(e)})
        }
