import os
import json
import requests
import logging


logger = logging.getLogger()
logger.setLevel(logging.INFO)


ACCESS_KEY = os.environ.get("ACCESS_KEY")
# API Headers
headers = {
    'AccessKey': ACCESS_KEY
}


# Map each step name to its corresponding service URL
STEP_URL_CONFIG = {
    "create_configuration": {
        "url": "https://9eaalgwdl5.execute-api.ap-south-1.amazonaws.com/prod/init/{client}/{connector}",
        "method": "GET"
    },
    "create_collections": {
        "url": "https://s2emxkbodf.execute-api.ap-south-1.amazonaws.com/prod/init/{client}/{connector}",
        "method": "POST"
    },
    "create_s3_bucket": {
        "url": "https://m890ytvhy4.execute-api.ap-south-1.amazonaws.com/prod/init/{client}",
        "method": "POST"
    },
    "create_compute_environment": {
        "url": "https://i8c4gggymd.execute-api.ap-south-1.amazonaws.com/prod/init/{client}/{connector}",
        "method": "GET"
    },
    "create_job_queue": {
        "url": "https://yarbf8k83a.execute-api.ap-south-1.amazonaws.com/prod/init/{client}/{connector}",
        "method": "GET"
    },
    "create_job_definition": {
        "url": "https://4li7upsuzh.execute-api.ap-south-1.amazonaws.com/prod/init/{client}/{connector}",
        "method": "GET"
    }
}


# CORS header
cors_headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'OPTIONS,GET,POST'
}


def lambda_handler(event, context):
    try:
        # extract path parameters
        path_params = event.get("pathParameters", {})
        client_name = path_params.get("client")
        connector = path_params.get("connector")
        body = event.get('body')

        if not client_name or not connector:
            logger.warning("Missing path parameters")
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Missing path parameters: client and connectors are required'})
            }
        
        client_name = client_name.lower()
        connector = connector.lower()
        
        if isinstance(body, str):
            body = json.loads(body)
        
        setupsteps = body.get('setupsteps', {})

        for step_key in sorted(setupsteps.keys()):
            step = setupsteps[step_key]
            step_name = step.get('name')
            payload = step.get('payload', {})

            config = STEP_URL_CONFIG.get(step_name)
            if not config:
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({'error': f'No config found for step: {step_name}'})
                }
            
            url = config['url'].format(
                client=client_name,
                connector=connector or ""
            )

            method = config['method'].upper()

            logger.info(f"Executing step: {step_name}")
            # choose HTTP method and create request
            match method:
                case 'GET':
                    response = requests.get(url=url, headers=headers)
                case 'POST':
                    response = requests.post(url=url, json=payload, headers=headers)
                case _:
                    return {
                        'statusCode': 400,
                        'headers': cors_headers,
                        'body': json.dumps({'error': f'Unsupported HTTP method: {method}'})
                    }
            
            response.raise_for_status()
            logger.info(f"Step {step_name} response: {response.json()}")

        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({'message': 'All steps executed successfully'})
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Unhandled exception', 'details': str(e)})
        }
