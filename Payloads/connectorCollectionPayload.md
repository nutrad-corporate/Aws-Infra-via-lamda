# Payload for connectorCollection

### 1. Shopify Payload
```md
{
  "pathParameters": {
    "client": "demo_client",
    "connector": "shopify"
  },
  "body": {
    "collections": [
      "SHOPIFY_PRODUCT_COLLECTION",
      "SHOPIFY_LOGS_COLLECTION"
    ]
  }
}
```

### 2. Walmart Payload
```md
{
  "pathParameters": {
    "client": "demo_client",
    "connector": "walmart"
  },
  "body": {
    "collections": [
      "WALMART_PRODUCT_TEMPLATE",
      "WALMART_PRODUCT_COLLECTION",
      "WALMART_FINAL_FEED_TEMP",
      "WALMART_PRODUCT_INVENTORY",
      "WALMART_LOGS_COLLECTION"
    ],
    "template_files": {
      "WALMART_PRODUCT_TEMPLATE": "Walmart_Templates.json"
    }
  }
}
```

### 3. Lazada Payload
```md
{
  "pathParameters": {
    "client": "demo_client",
    "connector": "lazada"
  },
  "body": {
    "collections": [
      "LAZADA_PRODUCT_COLLECTION",
      "LAZADA_LOGS_COLLECTION",
      "LAZADA_CATEGORY_ID_COLLECTION",
      "LAZADA_BRAND_ID_COLLECTION"
    ],
    "template_files": {
      "LAZADA_CATEGORY_ID_COLLECTION": "category_id.json",
      "LAZADA_BRAND_ID_COLLECTION": "brand_id.json"
    }
  }
}
```
