import json
import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from bson import ObjectId
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

MONGODB_URI = os.environ.get('MONGODB_URI')

cors_headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'OPTIONS,GET,POST'
}

def lambda_handler(event, context):
    try:
        path_params = event.get("pathParameters", {})
        client_name = path_params.get("client")
        connector = path_params.get("connector")

        if not client_name or not connector:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Missing path parameters: client and connector are required'})
            }

        client_name = client_name.lower()
        connector = connector.upper()

        logger.info(f"Initializing collections for client: {client_name}, connector: {connector}")

        body = event.get("body")
        if isinstance(body, str):
            body = json.loads(body)

        requested_keys = body.get("collections", [])
        template_files = body.get("template_files", {})

        if not requested_keys:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'No collection keys specified in request'})
            }

        client = MongoClient(MONGODB_URI)
        client.admin.command('ping')
        db = client[client_name]
        logger.info("Connected to MongoDB")

        config_collection = db[f"{client_name}_Configuration"]
        config_doc = config_collection.find_one({"DATABASE_NAME": client_name})

        if not config_doc:
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps({'error': f'No configuration found for client: {client_name}'})
            }

        created_collections = []

        for key in requested_keys:
            collection_name = config_doc.get(key)
            if not collection_name:
                logger.warning(f"Key '{key}' not found in config document.")
                continue

            collection = db[collection_name]
            template_file = template_files.get(key)

            if template_file:
                try:
                    with open(template_file, 'r') as f:
                        data = json.load(f)

                    if isinstance(data, list):
                        for doc in data:
                            if '_id' in doc and isinstance(doc['_id'], dict) and '$oid' in doc['_id']:
                                doc['_id'] = ObjectId(doc['_id']['$oid'])
                        collection.insert_many(data)
                    else:
                        doc = data
                        if '_id' in doc and isinstance(doc['_id'], dict) and '$oid' in doc['_id']:
                            doc['_id'] = ObjectId(doc['_id']['$oid'])
                        collection.insert_one(doc)
                except FileNotFoundError:
                    logger.exception(f"{template_file} not found")
                    return {
                        'statusCode': 500,
                        'headers': cors_headers,
                        'body': json.dumps({'error': f'{template_file} not found in Lambda directory'})
                    }
                except json.JSONDecodeError:
                    logger.exception(f"Invalid JSON in {template_file}")
                    return {
                        'statusCode': 500,
                        'headers': cors_headers,
                        'body': json.dumps({'error': f'Invalid JSON format in {template_file}'})
                    }
            else:
                collection.insert_one({"init": True})
                collection.delete_one({"init": True})

            created_collections.append(collection_name)

        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'message': f'Successfully initialized collections for {client_name}.',
                'created_collections': created_collections
            })
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
