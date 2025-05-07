# Payload to create S3 Bucket

```md
{
  "pathParameters": {
    "client": "demo_client"
  },
  "body": {
    "public_access_block": {
      "BlockPublicAcls": false,
      "IgnorePublicAcls": false,
      "BlockPublicPolicy": false,
      "RestrictPublicBuckets": false
    },
    "ownership_controls": {
      "Rules": [
        {
          "ObjectOwnership": "ObjectWriter"
        }
      ]
    },
    "acl": "public-read",
    "policy": {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": "*",
          "Action": "s3:GetObject",
          "Resource": "arn:aws:s3:::${bucket}/*"
        },
        {
          "Effect": "Allow",
          "Principal": "*",
          "Action": "s3:PutObject",
          "Resource": "arn:aws:s3:::${bucket}/archive/*"
        },
        {
          "Effect": "Allow",
          "Principal": "*",
          "Action": "s3:PutObject",
          "Resource": "arn:aws:s3:::${bucket}/*"
        },
        {
          "Effect": "Allow",
          "Principal": "*",
          "Action": "s3:DeleteObject",
          "Resource": "arn:aws:s3:::${bucket}/*"
        }
      ]
    }
  }
}
```
