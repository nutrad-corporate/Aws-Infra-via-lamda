import os
import logging


logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    # the expected access key
    expected_key = os.environ.get('ACCESS_KEY')

    # extract AccessKey from headers
    headers = event.get("headers", {})
    access_key = headers.get("accesskey")

    logger.info("Lambda Authorizer Triggered")
    logger.info(f"Received AccessKey: {access_key}")
    logger.info(f"Expected AccessKey: {expected_key}")
    logger.info(f"Received Headers: {headers}")

    # Check if AccessKey is valid
    if access_key == expected_key:
        logger.info("AccessKey is valid")
        return {
            "isAuthorized": True,
        }
    else:
        logger.info("AccessKey is invalid")
        return {
            "isAuthorized": False
        }
