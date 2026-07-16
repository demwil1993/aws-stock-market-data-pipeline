## Deployment

This project uses AWS SAM for infrastructure deployment.

### Prerequisites

- AWS CLI
- AWS SAM CLI
- Python 3.12
- An AWS CLI profile with deployment permissions
- A Twelve Data API key stored in AWS Secrets Manager

### Configure SAM

Copy the example configuration:

```cmd
copy infrastructure\samconfig.example.toml infrastructure\samconfig.toml

## Architecture

```text
Twelve Data API
        │
        ▼
Amazon EventBridge Scheduler
        │
        ▼
AWS Lambda
        │
        ├── API retrieval
        ├── Schema normalization
        ├── Validation
        └── JSONL serialization
        │
        ▼
Amazon S3
        ├── raw/quotes
        └── standardized/quotes
        │
        ▼
AWS Glue ETL
        ├── Final schema enforcement
        ├── Deduplication
        ├── Data-quality checks
        └── Parquet conversion
        │
        ▼
Amazon S3
        ├── curated/quotes
        └── rejected/quotes
        │
        ▼
AWS Glue Data Catalog
        │
        ▼
Amazon Athena