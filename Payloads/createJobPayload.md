# Create Job Payload

### Payload for Shopify
```md
{
  "pathParameters": {
    "client": "demo_client",
    "connector": "shopify",
    "job_type": "submit"
  },
  "body": {
    "command": ["python", "post_product.py"]
  }
}
```

### Payload for Walmart
```md
{
  "pathParameters": {
    "client": "demo_client",
    "connector": "walmart",
    "job_type": "submit"
  },
  "body": {
    "command": ["python", "main.py"]
  }
}
```

### Payload for Lazada
```md
{
  "pathParameters": {
    "client": "demo_client",
    "connector": "lazada",
    "job_type": "submit"
  },
  "body": {
    "command": ["python", "create_lazada_product.py"]
  }
}
```

### Payload for Walmart (Check Feed Status)
```md
{
  "pathParameters": {
    "client": "demo_client",
    "connector": "walmart",
    "job_type": "check_feed_status"
  },
  "body": {
    "command": ["python", "check_feed_status.py"]
  }
}
```
