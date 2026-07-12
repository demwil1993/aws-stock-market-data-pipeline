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

### Pending Operational check

Confirm the EventBridge Scheduler automatically invokes the Lambda during
the next weekday market-hours window and creates matching raw and curated
S3 objects.

aws logs tail /aws/lambda/stock-pipeline-ingestion-dev ^
  --since 30m ^
  --region us-east-2 ^
  --profile stock-pipeline

aws s3 ls s3://YOUR-BUCKET-NAME/raw/quotes/ ^
  --recursive ^
  --region us-east-2 ^
  --profile stock-pipeline