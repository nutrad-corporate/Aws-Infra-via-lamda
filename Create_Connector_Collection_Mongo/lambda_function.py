import json
import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from bson import ObjectId
import logging


logger = logging.getLogger()
logger.setLevel(logging.INFO)


# MongoDB connection
MONGODB_URI = os.environ.get('MONGODB_URI')

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

        # Parse JSON body
        body = event.get("body")
        if isinstance(body, str):
            body = json.loads(body)

        collections_to_create = body.get("collections", [])
        template_files = body.get("template_files", {})

        if not collections_to_create:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No collections specified in the request'})
            }
        
        # connect to MongoDB
        client = MongoClient(MONGODB_URI)
        client.admin.command('ping')

        # select the appropriate database and configuraiton collection
        logger.info("Connecting to the database")
        db = client[client_name]
        logger.info("Connected to MongoDB")
        
        created_collections = []

        for collection_name in collections_to_create:
            if not collection_name:
                continue

            collection = db[collection_name]

            # Handle template file insertion if present
            template_file = template_files.get(collection_name)

            if template_file:
                try:
                    with open(template_file, 'r') as f:
                        data = json.load(f)
                    
                    # Handle $oid
                    if isinstance(data, list):
                        for doc in data:
                            if '_id'in doc and isinstance(doc['_id'], dict) and '$oid' in doc['_id']:
                                doc['_id'] = ObjectId(doc['_id']['$oid'])
                        
                        collection.insert_many(data)
                    
                    else:
                        doc = data
                        if '_id' in doc and isinstance(doc['_id'], dict) and '$oid' in doc['_id']:
                            doc['_id'] = ObjectId(doc['_id']['$oid'])
                        
                        collection.insert_one(doc)
                
                except FileNotFoundError:
                    logger.exception(f"{template_file} not found in directory")
                    return {
                        'statusCode': 500,
                        'body': json.dumps({'error': f'{template_file} not found in Lambda directory'})
                    }
                
                except json.JSONDecodeError:
                    logger.exception(f"Invalid JSON format in {template_file}")
                    return {
                        'statusCode': 500,
                        'body': json.dumps({'error': f'Invalid JSON format in {template_file}'})
                    }
                
            else:
                # create collection by inserting a dummy doc then deleting it
                collection.insert_one({"init": True})
                collection.delete_one({"init": True})

            created_collections.append(collection_name)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Collections initialized successfully for client {client_name}.',
                'created_collections': created_collections
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
