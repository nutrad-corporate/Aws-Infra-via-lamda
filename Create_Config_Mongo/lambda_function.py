import json
import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import logging


logger = logging.getLogger()
logger.setLevel(logging.INFO)


# MongoDB connection
MONGODB_URI = os.environ.get('MONGODB_URI')

def lambda_handler(event, context):
    client = None  # ensure it's defined
    try:
        path_params = event.get("pathParameters", {})
        dbName = path_params.get('client')
        connector = path_params.get('connector')

        if not dbName or not connector:
            logger.warning(f"Missing path parameters")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing path parameters: client and connector are required'})
            }
        
        dbName = dbName.lower()
        connector = connector.lower()

        logger.info(f"Processing request of client: {dbName} for connector: {connector}")

        # connect to MongoDB
        client = MongoClient(MONGODB_URI)
        client.admin.command('ping')
        
        # fetch template
        logger.info(f"Fetching template configuration for connector: {connector}")
        template_db = client['Infrastructure_Configuration']
        template_collection = template_db.get_collection(connector)
        template_doc = template_collection.find_one()
        if not template_doc:
            logger.warning(f"No template configuration found for connector: {connector}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': f'Template configuration not found for {connector}'})
            }

        template_doc.pop('_id', None)
        template_str = json.dumps(template_doc)

        # dynamic values
        random_string = '76hy8r07fjk3gu6ghin'
        template_str = template_str.replace("${database_name}", dbName)
        template_str = template_str.replace("${random_string}", random_string)

        config_doc = json.loads(template_str)

        # save to target collection
        logger.info("Connecting to database and creating the configuration collection along with configuration document")
        db = client[dbName]
        config_collection = db[f'{dbName}_Configuration']
        existing_databases = client.list_database_names()
        db_exists = dbName in existing_databases

        if db_exists:
            config_collection.update_one({}, {'$set': config_doc}, upsert=True)
            message = 'Configuration document updated successfully'
        else:
            config_collection.insert_one(config_doc)
            message = 'Configuration document inserted successfully'

        return {
            'statusCode': 200,
            'body': json.dumps({
                "message": message,
                "database": dbName,
                "connector": connector
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
    finally:
        if client:
            client.close()
