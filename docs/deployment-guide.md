# Deployment Guide

This guide describes how to deploy and verify the AWS Stock Market Data Pipeline after the implementation freeze.

## Prerequisites

- An AWS account with permission to deploy the project resources.
- AWS CLI configured with the intended profile.
- AWS SAM CLI installed.
- Python environment containing the project dependencies.
- A Twelve Data API key.
- An existing or deployable S3 location for the Glue ETL script.

The project was developed with the AWS CLI profile:

```text
stock-pipeline
```

and AWS Region:

```text
us-east-2
```

Adjust commands when using a different profile or Region.

## 1. Prepare local configuration

Create the local environment from the repository configuration or install the required packages.

Do not commit credentials or the environment-specific `infrastructure/samconfig.toml` file.

Use these files as references:

```text
.env.example
infrastructure/samconfig.example.toml
```

## 2. Configure the API secret

Store the Twelve Data API key in AWS Secrets Manager. Record the secret ARN because it is required by the deployment configuration.

The API key should not appear in:

- source code;
- `.env.example`;
- CloudFormation source files;
- committed SAM configuration;
- test fixtures.

## 3. Review deployment parameters

Confirm the values expected by `infrastructure/template.yaml`, including:

- environment name;
- Twelve Data secret ARN;
- stock watchlist or related ingestion settings;
- Glue assets bucket or script location;
- notification email or SNS configuration, when enabled;
- schedule state and time zone.

The implemented scheduler uses the `America/Chicago` time zone.

## 4. Upload the Glue ETL script

AWS SAM does not automatically upload arbitrary Glue scripts referenced by `ScriptLocation`. Upload the script before deploying or updating the Glue job.

From the repository root, run:

```bash
aws s3 cp \
  src/stockpipeline/transformation/standardized_to_curated.py \
  s3://<glue-assets-bucket>/scripts/standardized_to_curated.py \
  --profile stock-pipeline \
  --region us-east-2
```

The `scripts/` prefix is created automatically when the object is uploaded.

## 5. Validate the SAM template

From the `infrastructure/` directory:

```bash
sam validate --lint
```

Resolve validation errors before building. All CloudFormation resources must be nested under the template's `Resources:` section.

## 6. Build the application

```bash
sam build
```

The build packages the Lambda application and prepares the CloudFormation deployment artifacts.

## 7. Deploy the stack

For the first deployment, use guided mode:

```bash
sam deploy --guided --profile stock-pipeline --region us-east-2
```

For later deployments, use the saved configuration:

```bash
sam deploy --profile stock-pipeline --region us-east-2
```

Review the CloudFormation change set before confirming deployment.

## 8. Confirm deployed resources

Verify the expected resources in AWS:

- ingestion Lambda function;
- EventBridge Scheduler schedule;
- S3 data bucket;
- Glue assets bucket or configured script location;
- standardized and curated Glue Crawlers;
- standardized-to-curated Glue ETL job;
- Glue Data Catalog database;
- Athena result location;
- CloudWatch alarms;
- SNS topic and confirmed email subscription, when enabled;
- IAM roles and least-privilege policies.

## 9. Perform initial catalog discovery

Run the standardized-data crawler after standardized files exist in S3.

The crawler should create or update the standardized source table in the Glue Data Catalog. Confirm that its table location points to the `standardized/` prefix.

Crawlers discover metadata; they do not move or transform records.

## 10. Verify ingestion

Invoke the Lambda function manually or wait for the enabled EventBridge schedule.

Confirm that a successful run writes data under the expected prefixes:

```text
raw/
standardized/
```

Review Lambda logs in CloudWatch for API, validation, serialization, or S3 errors.

## 11. Run the Glue ETL job

The implementation intentionally uses on-demand Glue transformation.

Start the standardized-to-curated job in AWS Glue. The job reads the standardized Data Catalog table and writes:

```text
curated/
rejected/
```

Expected behavior:

- valid records are converted to partitioned Snappy-compressed Parquet;
- duplicate `symbol` and `market_timestamp` records retain the latest ingestion within the run;
- invalid records are written to the rejected layer with a rejection reason.

Wait for the job status to become `Succeeded` before querying newly arrived data.

## 12. Run the curated crawler

Run the curated crawler during initial setup so Athena can discover the curated Parquet table.

After initial discovery, rerun the crawler only when:

- the schema changes;
- table locations change;
- partition design changes;
- catalog metadata must be refreshed.

The crawler is not scheduled in the frozen implementation.

## 13. Verify Athena

Select the deployed Glue Data Catalog database and confirm that `curated_quotes` is available.

Run the validation queries in:

```text
sql/validation_queries.sql
```

Priority checks include:

- required-field validation;
- invalid-price validation;
- high-versus-low consistency;
- duplicate business-key validation;
- partition correctness;
- aggregate validation summary.

Then run representative analytical queries in:

```text
sql/analytics_queries.sql
```

Examples include latest quote by symbol, gainers and losers, volume analysis, daily summaries, moving averages, volatility, freshness, and partition summaries.

## 14. Run local unit tests

From the repository root:

```bash
pytest -v
```

The local test suite covers non-Spark Python components, including API behavior, Lambda handling, storage, models, pipeline logic, and validation.

The frozen implementation intentionally excludes local PySpark tests. Glue transformation behavior is validated through successful AWS Glue execution and Athena SQL checks.

## Normal operating workflow

After deployment, routine use is:

1. EventBridge Scheduler invokes Lambda automatically.
2. Lambda writes raw and standardized JSONL records to S3.
3. Standardized records accumulate until refreshed analytics are needed.
4. An analyst or operator manually starts the Glue ETL job.
5. The job updates curated and rejected Parquet data.
6. The analyst queries `curated_quotes` in Athena.
7. Crawlers are rerun only when metadata discovery is required.

## Updating the Glue script

When `standardized_to_curated.py` changes:

1. Upload the revised script to the same S3 `ScriptLocation`.
2. Run the Glue job against test data.
3. Confirm curated and rejected outputs.
4. Run the Athena validation suite.
5. Commit the validated code and documentation.

A SAM deployment is required only when the Glue job resource definition, IAM permissions, arguments, paths, or other CloudFormation-managed configuration changes.

## Troubleshooting quick reference

### Glue job cannot find the script

- Confirm the object exists in the Glue assets bucket.
- Confirm `ScriptLocation` matches the exact S3 URI.
- Confirm the Glue role can read the script object.

### Glue job cannot find the source table

- Run the standardized crawler.
- Confirm the database and table argument values.
- Confirm the catalog table points to the standardized S3 prefix.

### Athena does not show new records

- Confirm Lambda wrote the new standardized files.
- Run the Glue ETL job and wait for success.
- Confirm new Parquet objects exist under `curated/`.
- Rerun the curated crawler only if metadata or schema discovery is required.
- Verify that the Athena query is not filtering out the new partitions.

### Duplicate curated results appear after repeated job runs

The current job deduplicates records within each run but does not use Glue job bookmarks or an incremental source filter. Repeated full-source executions may write additional Parquet output for records processed previously. For this portfolio-scale implementation, validate results with the supplied SQL and manage runs intentionally.

### Lambda schedule does not run

- Confirm the EventBridge Scheduler resource is enabled.
- Confirm the schedule uses the intended `America/Chicago` time zone.
- Confirm the scheduler execution role can invoke the Lambda function.
- Review Scheduler history and Lambda CloudWatch logs.