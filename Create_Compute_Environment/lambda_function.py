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


def create_compute_environment(compute_environment_name):
    try:
        # Check if the compute environment already exists
        logger.info(f"Describing compute environment: {compute_environment_name}")
        existing_envs = batch_client.describe_compute_environments(
            computeEnvironments=[compute_environment_name]
        )
        logger.info(f"Existing compute environments: {existing_envs}")

        if existing_envs['computeEnvironments']:
            logger.info(f"Compute environment '{compute_environment_name}' already exists.")
            return {
                'ResponseMetadata': {'HTTPStatusCode': 200},
                'status': 'ALREADY_EXISTS'
            }

    except ClientError as e:
        logger.exception("Error describing compute environments.")
        raise

    logger.info(f"Compute environment '{compute_environment_name}' does not exist. Proceeding to create.")

    try:
        response = batch_client.create_compute_environment(
            computeEnvironmentName=compute_environment_name,
            type='MANAGED',
            state='ENABLED',
            computeResources={
                'type': 'FARGATE',
                'maxvCpus': 1,
                'subnets': [
                    'subnet-099dbb7898fe530b3',
                    'subnet-081e532a49f06d23f',
                    'subnet-058335622aeac0d67'
                ],
                'securityGroupIds': [
                    'sg-05965867a588003a0'
                ]
            }
        )
        logger.info(f"Create compute environment response: {response}")
        return response

    except ClientError as e:
        logger.exception("Failed to create compute environment.")
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

        # select the appropriate database and configuraiton collection
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
        
        logger.info(f"Fetching the compute environment name from the configuration collection for the connector: {connector}")
        compute_environment_name = config_doc.get(f"{connector.upper()}_COMPUTE_ENVIRONMENT_NAME")

        if not compute_environment_name:
            logger.warning(f"Compute environment name is missing in configuration document for connector: {connector}")
            return {
                'statusCode': 400,
                'body': json.dumps({"error": f"Compute environment name is missing in configuration document for connector: {connector}"})
            }
        
        logger.info(f"Fetched compute environment name: {compute_environment_name}")

        logger.info("Creating Compute Environment")
        response = create_compute_environment(compute_environment_name=compute_environment_name)
        status_code = response['ResponseMetadata']['HTTPStatusCode']
        status = response.get('status', 'CREATED')
        
        logger.info(f"Compute environment creation result: {status}")
        return {
            'statusCode': status_code,
            'body': json.dumps({"status": status})
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
