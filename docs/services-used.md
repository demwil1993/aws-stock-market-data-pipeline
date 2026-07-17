```
Twelve Data Stock API
          │
          ▼
Amazon EventBridge Scheduler
          │
          ▼
AWS Lambda — Ingestion
          │
          ├── Retrieve quotes
          ├── Normalize schema
          ├── Validate records
          └── Create JSONL batches
          │
          ▼
Amazon S3 — Ingestion Data
          │
          ├── raw/quotes — Original API responses
          └── standardized/quotes — Typed, validated JSONL
          │
          ▼
AWS Glue ETL Job
          │
          ├── Enforce final schema
          ├── Remove duplicates
          ├── Apply data-quality rules
          ├── Route rejected records
          └── Convert JSONL to Parquet
          │
          ▼
Amazon S3 — Analytics Data
          │
          ├── curated/quotes — Partitioned Parquet
          ├── rejected/quotes — Invalid records
          └── athena-results — Query output
          │
          ▼
AWS Glue Data Catalog
          │
          ▼
Amazon Athena
          │
          ▼
SQL Analysis / Dashboard
```


##### Supporting services:

AWS Secrets Manager
- Stores the Twelve Data API key.

AWS CloudWatch Logs
- Stores Lambda execution logs.

AWS CloudWatch Alarms
- Monitors Lambda errors, throttles, and duration.

Amazon SNS
- Sends operational alerts by email.

AWS IAM
- Enforces least-privilege access.

AWS SAM / AWS CloudFormation
- Defines and deploys the infrastructure as code.

GitHub
- Stores source code, infrastructure templates, tests, and documentation.
