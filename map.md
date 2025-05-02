# Understand the working

#### Lambda Functions
1. configurationCollection
    - API Gateway: https://9eaalgwdl5.execute-api.ap-south-1.amazonaws.com/prod/init/{client}/{connector}
    - Directory: [Create_Config_Mongo](Create_Config_Mongo)
    - Description: 
        1. Responsible for creation of the database on the MongoDB for the client if not exist and create/update configuration document in the configuration collection of the database.
        2. It takes the configuration document for respective connector from the collection of connector's name in the Infrastructure_Configuration database.

2. connectorCollection
    - API Gateway: https://s2emxkbodf.execute-api.ap-south-1.amazonaws.com/prod/init/{client}/{connector}
    - Directory: [Create_Connector_Collection_Mongo](Create_Connector_Collection_Mongo)
    - Description:
        1. Responsible for the creation of the collections required by the respective connector in the database.
        2. It takes the name of the collection from the configuration document along with that it insert the docuemnts in the collections where needed.

3. createS3Bucket
    - API Gateway: https://m890ytvhy4.execute-api.ap-south-1.amazonaws.com/prod/init/{client}
    - Directory: [Create_S3_Bucket](Create_S3_Bucket)
    - Description:
        1. Responsible for creating the S3 Bucket for the respective client along with that it provides the ACL (public-read) for all its objects.
        2. This Lambda function requires to create the IAM role, such that it can able take action for the S3.
        3. It takes the name of the S3 Bucket from the configuration document. 