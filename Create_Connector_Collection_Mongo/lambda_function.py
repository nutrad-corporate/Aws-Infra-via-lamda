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
        
        logger.info(f"Creating collections for the connector: {connector}")
        match connector:
            case 'shopify':
                collections_to_create = [
                    config_doc.get("SHOPIFY_PRODUCT_COLLECTION"),
                    config_doc.get("SHOPIFY_LOGS_COLLECTION")
                ]
            case 'walmart':
                collections_to_create = [
                    config_doc.get("WALMART_PRODUCT_TEMPLATE"),
                    config_doc.get("WALMART_PRODUCT_COLLECTION"),
                    config_doc.get("WALMART_FINAL_FEED_TEMP"),
                    config_doc.get("WALMART_PRODUCT_INVENTORY"),
                    config_doc.get("WALMART_LOGS_COLLECTION")
                ]

                # Load JSON file if Template is present
                logger.info("Inserting Walmart_Templates.json in the WALMART_PRODUCT_TEMPLATE collection")
                template_collection = config_doc.get("WALMART_PRODUCT_TEMPLATE")
                if template_collection:
                    try:
                        with open('Walmart_Templates.json', 'r') as f:
                            template_data = json.load(f)
                        
                        if isinstance(template_data, list):
                            for doc in template_data:
                                if '_id' in doc and isinstance(doc['_id'], dict) and '$oid' in doc['_id']:
                                    doc['_id'] = ObjectId(doc['_id']['$oid'])
                            db[template_collection].insert_many(template_data)
                        else:
                            doc = template_data
                            if '_id' in doc and isinstance(doc['_id'], dict) and '$oid' in doc['_id']:
                                doc['_id'] = ObjectId(doc['_id']['$oid'])
                            db[template_collection].insert_one(doc)
                    except FileNotFoundError:
                        logger.exception("Walmart_Template.json not found in the directory")
                        return {
                            'statusCode': 500,
                            'body': json.dumps({'error': 'Walmart_Templates.json not found in Lambda directory'})
                        }
                    except json.JSONDecodeError:
                        logger.exception("Invalid JSON format in Walmart_Template.json")
                        return {
                            'statusCode': 500,
                            'body': json.dumps({'error': 'Invalid JSON format in Walmart_Templates.json'})
                        }
                collections_to_create.remove(template_collection)    
            case 'lazada':
                collections_to_create = [
                    config_doc.get("LAZADA_PRODUCT_COLLECTION"),
                    config_doc.get("LAZADA_LOGS_COLLECTION"),
                    config_doc.get("LAZADA_CATEGORY_ID_COLLECTION"),
                    config_doc.get("LAZADA_BRAND_ID_COLLECTION")
                ]

                logger.info("Inserting category_id.json in LAZADA_CATEGORY_ID_COLLECTION")
                category_collection = config_doc.get("LAZADA_CATEGORY_ID_COLLECTION")
                if category_collection:
                    try:
                        with open('category_id.json', 'r') as f:
                            category_data = json.load(f)
                        
                        db[category_collection].insert_one(category_data)
                    except FileNotFoundError:
                        logger.exception("category_id.json not found in the directory")
                        return {
                            'statusCode': 500,
                            'body': json.dumps({'error': 'category_id.json not found in Lambda directory'})
                        }
                    except json.JSONDecodeError:
                        logger.exception("Invalid JSON format in category_id.json")
                        return {
                            'statusCode': 500,
                            'body': json.dumps({'error': 'Invalid JSON format in category_id.json'})
                        }
                collections_to_create.remove(category_collection)

                logger.info("Inserting brand_id.json in LAZADA_BRAND_ID_COLLECTION")
                brand_collection = config_doc.get("LAZADA_BRAND_ID_COLLECTION")
                if brand_collection:
                    try:
                        with open('brand_id.json', 'r') as f:
                            brand_data = json.load(f)

                        db[brand_collection].insert_one(brand_data)
                    except FileNotFoundError:
                        logger.exception("brand_id.json not found in the directory")
                        return {
                            'statusCode': 500,
                            'body': json.dumps({'error': 'brand_id.json not found in Lambda directory'})
                        }
                    except json.JSONDecodeError:
                        logger.exception("Invalid JSON format in the brand_id.json")
                        return {
                            'statusCode': 500,
                            'body': json.dumps({'error': 'Invalid JSON format in brand_id.json'})
                        }
                collections_to_create.remove(brand_collection)
            case _:
                logger.warning(f"Unsupprted connector: {connector}")
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': f'Unsupported connector: {connector}'})
                }
        
        for collection_name in collections_to_create:
            if not collection_name:
                continue

            collection = db[collection_name]
            collection.insert_one({"init": True})
            collection.delete_one({"init": True})
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Collections for {connector} initialized successfully for client {client_name}.',
                'created_collections': collections_to_create
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
