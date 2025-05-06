# Understand the working

#### Lambda Functions
1. configurationCollection
    - API Gateway: https://9eaalgwdl5.execute-api.ap-south-1.amazonaws.com/prod/init/{client}/{connector}
    - API Method: GET
    - Directory: [Create_Config_Mongo](Create_Config_Mongo)
    - Description: 
        1. Responsible for creation of the database on the MongoDB for the client if not exist and create/update configuration document in the configuration collection of the database.
        2. It takes the configuration document for respective connector from the collection of connector's name in the Infrastructure_Configuration database.

2. connectorCollection
    - API Gateway: https://s2emxkbodf.execute-api.ap-south-1.amazonaws.com/prod/init/{client}/{connector}
    - API Method: POST
    - Payload: [Payload](connectorCollectionPayload.md)
    - Directory: [Create_Connector_Collection_Mongo](Create_Connector_Collection_Mongo)
    - Description:
        1. Responsible for the creation of the collections required by the respective connector in the database.
        2. It takes the name of the collection from the configuration document along with that it insert the docuemnts in the collections where needed.

3. createS3Bucket
    - API Gateway: https://m890ytvhy4.execute-api.ap-south-1.amazonaws.com/prod/init/{client}
    - API Method: POST
    - Directory: [Create_S3_Bucket](Create_S3_Bucket)
    - Payload: [Payload](s3BucketPayload.md) 
    - Description:
        1. Responsible for creating the S3 Bucket for the respective client along with that it provides the ACL (public-read) for all its objects.
        2. This Lambda function requires to add permission to the IAM role of it, such that it can able to take action for the S3.
        3. It takes the name of the S3 Bucket from the configuration document.

4. createComputeEnvironment
    - API Gateway: https://i8c4gggymd.execute-api.ap-south-1.amazonaws.com/prod/init/{client}/{connector}
    - API Method: GET
    - Directory: [Create_Compute_Environment](Create_Compute_Environment)
    - Description:
        1. Responsible for creating the Compute Environment for the respective connector of the respective client.
        2. This Lambda function requires to add permission to the IAM role of it, such that it can able to take action for the Batch.
        3. It takes the name of the Compute Environment from the configuration document.

5. createJobQueue
    - API Gateway: https://yarbf8k83a.execute-api.ap-south-1.amazonaws.com/prod/init/{client}/{connector}
    - API Method: GET
    - Directory: [Create_Job_Queue](Create_Job_Queue)
    - Description:
        1. Responsible for creating the Job Queue for the respective connector for the respective client.
        2. This lambda function requires to add permission to the IAM role of it, such that it can able to take action for the Batch.
        3. It takes the name of the Job Queue and Compute Environment from the configuration document.

6. createJobDefinition
    - API Gateway: https://4li7upsuzh.execute-api.ap-south-1.amazonaws.com/prod/init/{client}/{connector}
    - API Method: GET
    - Directory: [Create_Job_Definition](Create_Job_Definition)
    - Description:
        1. Responsible for creating the Job Definition for the respective connector for the respective client.
        2. This lambda function requires to add permission to the IAM role of it, such that it can able to take action for the Batch.
        3. It takes the name of the Job Definition and ECR Image URI from the configuration document.

7. createJob
    - API Gateway: https://s97690e06j.execute-api.ap-south-1.amazonaws.com/default/init/{job_type}/{client}/{connector}
    - API Method: POST
    - Payload: [Payload](createJobPayload.md)
    - Directory: [Create_Job](Create_Job)
    - Description:
        1. Responsible for submit the job to the relevant connector.
        2. This lambda function requires to add permission to the IAM role of it, such that it can able to take action for the Batch.
        3. It takes the name of the Job Name, Job Definition, Job Queue, and WALMART_CHECK_FEED_STATUS_RULE_NAME from the configuration document.
