import os
import json
from pymongo import MongoClient
from bson import ObjectId
import logging


logger = logging.getLogger()
logger.setLevel(logging.INFO)


# MongoDB Configuration
MONGODB_URI = os.environ.get('MONGODB_URI')
DOCUMENT_ID = os.environ.get('DOCUMENT_ID')

# CORS header
cors_headers = {
    'Access-Control-Allow-Origin': "*",
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'OPTIONS,GET,POST'
}


def lambda_handler(event, context):
    try:
        path_params = event.get("pathParameters", {})
        client_name = path_params.get("client")

        if not client_name:
            logger.warning("Missing path parameters")
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Missing path parameters: client required'})
            }
        
        client_name = client_name.lower()

        logger.info(f"Processing request for client: {client_name}")

        # connect to MongoDB
        client = MongoClient(MONGODB_URI)
        client.admin.command('ping')
        
        client_db_mapping = client['clientInfo']
        collection = client_db_mapping['clientDbMapping']
        document = collection.find_one({"_id": ObjectId(DOCUMENT_ID)})

        # Check whether the key-value pair already exists
        if document and document.get(client_name) == client_name:
            logger.info(f"Key-value pair `{client_name}: {client_name}` already exists")
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({'message': f'Key-value pair `{client_name}: {client_name}` already exists'})
            }        
        else:
            logger.info(f"Key-value pair `{client_name}: {client_name}` is not present")
            logger.info("Creating new key-value pair...")
            try:
                collection.update_one(
                    {"_id": ObjectId(DOCUMENT_ID)},
                    {
                        "$set": {
                            client_name: client_name
                        }
                    }
                )
                logger.info("Updated the 'clientInfo' database")
                return {
                    'statusCode': 200,
                    'headers': cors_headers,
                    'body': json.dumps({'message': "Updated the client name and database on 'ClientInfo' database"})
                }
            except Exception as e:
                logger.exception(f"Failed to update the client name and database on 'ClientInfo' database: {e}")
                return {
                    'statusCode': 500,
                    'headers': cors_headers,
                    'body': json.dumps({'error': str(e)})
                }
    except Exception as e:
        logger.exception("Unhandled exception occurred")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': str(e)})
        }
