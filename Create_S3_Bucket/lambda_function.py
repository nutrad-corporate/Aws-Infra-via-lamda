import json
import os
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
s3_client = boto3.client('s3')

def lambda_handler(event, context):
    try:
        # extract path parameters
        path_params = event.get("pathParameters", {})
        client_name = path_params.get("client")

        if not client_name:
            logger.warning(f"Missing path parameters")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing path parameters: client is required'})
            }

        client_name = client_name.lower()

        # Parse body
        body = event.get('body')
        if isinstance(body, str):
            body = json.loads(body)
        
        public_access_block = body.get("public_access_block")
        ownership_controls = body.get("ownership_controls")
        acl = body.get("acl")
        policy = body.get("policy")


        logger.info(f"Processing request of client: {client_name}")
        
        # connect to MongoDB
        client = MongoClient(MONGODB_URI)
        client.admin.command('ping')

        # select the appropriate database and configuration collection
        logger.info(f"Connecting to the database")
        db = client[client_name]
        config_collection = db[f'{client_name}_Configuration']
        config_doc = config_collection.find_one()

        if not config_doc:
            logger.warning(f"No configuration found for client: {client_name}")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f'No configuration found for client: {client_name}'})
            }
        
        logger.info(f"Fetching the bucket name and the region from the Configuration collection")
        bucket_name = config_doc.get("S3_BUCKET_NAME")
        region = config_doc.get("AWS_REGION", None) 

        if not bucket_name:
            logger.warning(f"S3_BUCKET_NAME is missing in configuration document of client: {client_name}")
            return {
                'statusCode': 400,
                'body': json.dumps({"error": f"S3_BUCKET_NAME is missing in configuration document of client: {client_name}"})
            }
        
        logger.info(f"Fetched bucket name: {bucket_name}, region: {region}")
        
        try:
            logger.info("Creating the S3 Bucket")
            if region is None or region == 'us-east-1':
                s3_client.create_bucket(Bucket=bucket_name)
            else:
                location = {'LocationConstraint': region}
                s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration=location)
            
            # apply optional configurations
            if public_access_block:
                logger.info("Applying public access block configuration")
                s3_client.put_public_access_block(
                    Bucket=bucket_name,
                    PublicAccessBlockConfiguration=public_access_block
                )

            if ownership_controls:
                logger.info("Applying ownership controls")
                s3_client.put_bucket_ownership_controls(
                    Bucket=bucket_name,
                    OwnershipControls=ownership_controls
                )

            if acl:
                logger.info(f"Applying ACL: {acl}")
                s3_client.put_bucket_acl(
                    Bucket=bucket_name,
                    ACL=acl
                )   

            if policy:
                logger.info("Injecting actual bucket name into policy resource ARNs")
                for statement in policy.get("Statement", []):
                    resource = statement.get("Resource")
                    if isinstance(resource, str):
                        statement["Resource"] = resource.replace("${bucket}", bucket_name)
                
                logger.info("Applying bucket policy")
                s3_client.put_bucket_policy(
                    Bucket=bucket_name,
                    Policy=json.dumps(policy)
                )

            logger.info(f"Bucket '{bucket_name}' created and configured successfully")
            return {
                'statusCode': 200,
                'body': json.dumps({"message": f"Bucket '{bucket_name}' created and configured successfully"})
            }
        
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'BucketAlreadyOwnedByYou':
                logger.info(f"Bucket '{bucket_name}' already exists and is owned by you.")
                return {
                    'statusCode': 200,
                    'body': json.dumps({"message": f"Bucket '{bucket_name}' already exists and is owned by you."})
                }
            elif error_code == 'BucketAlreadyExists':
                logger.warning(f"Bucket '{bucket_name}' already exists and is owned by another account.")
                return {
                    'statusCode': 409,
                    'body': json.dumps({"error": f"Bucket '{bucket_name}' already exists and is owned by another account."})
                }
            else:
                logger.exception("Unhandled exception occurred")
                return {
                    'statusCode': 500,
                    'body': json.dumps({"error": str(e)})
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
