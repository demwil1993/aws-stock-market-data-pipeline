# AWS Stock Market Data Pipeline

An end-to-end cloud data engineering pipeline that ingests stock market data from the Twelve Data API, validates and standardizes the records, transforms the data with AWS Glue, stores analytics-ready Parquet files in Amazon S3, and queries the curated layer with Amazon Athena.

The project uses a medallion-style architecture with raw, standardized, curated, and rejected data layers. Infrastructure is deployed using AWS SAM and AWS CloudFormation.

### Repository Structure

```
aws-stock-market-data-pipeline/
│
├── README.md
├── LICENSE
├── .gitignore
├── .env.example
├── environment.yml
├── requirements.txt
├── pytest.ini
│
├── architecture/
│   ├── architecture-diagram.png
│   └── data-flow.md
│
├── docs/
│   ├── architecture-decisions.md
│   ├── data-dictionary.md
│   └── deployment-guide.md
│
├── infrastructure/
│   ├── template.yaml
│   ├── samconfig.example.toml
│   └── samconfig.toml
│
├── scripts/
│   ├── run_local.py
│   └── run_lambda_local.py
│
├── sql/
│   ├── analytics_queries.sql
│   └── validation_queries.sql
│
├── src/
│   ├── requirements.txt
│   │
│   └── stockpipeline/
│       ├── __init__.py
│       ├── logging_config.py
│       │
│       ├── ingestion/
│       │   ├── __init__.py
│       │   ├── api_client.py
│       │   ├── config.py
│       │   ├── exceptions.py
│       │   ├── lambda_function.py
│       │   ├── models.py
│       │   ├── pipeline.py
│       │   ├── validation.py
│       │   └── watchlist.py
│       │
│       ├── storage/
│       │   ├── __init__.py
│       │   ├── local_storage.py
│       │   └── s3_storage.py
│       │
│       └── transformation/
│           ├── __init__.py
│           └── standardized_to_curated.py
│
└── tests/
    ├── test_api_client.py
    ├── test_lambda_function.py
    ├── test_local_storage.py
    ├── test_models.py
    ├── test_pipeline.py
    ├── test_s3_storage.py
    └── test_validation.py
```

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
```

## Architecture

```text
Twelve Data API
        |
        v
Amazon EventBridge Scheduler
        |
        v
AWS Lambda
        |
        +-----------------------------+
        |                             |
        v                             v
S3 Raw Layer                  S3 Standardized Layer
JSON API responses            Validated JSONL records
                                      |
                                      v
                              AWS Glue Crawler
                                      |
                                      v
                              AWS Glue Data Catalog
                                      |
                                      v
                                AWS Glue ETL
                                  /       \
                                 v         v
                       S3 Curated Layer   S3 Rejected Layer
                       Parquet + Snappy   Invalid records
                                 |
                                 v
                         Curated Glue Crawler
                                 |
                                 v
                           Amazon Athena
```


## Data layers

### Raw

Stores unmodified responses from the Twelve Data API.

```text
raw/quotes/year=YYYY/month=MM/day=DD/
```

### Standardized

Stores validated responses from the raw layer.

```text
standardized/quotes/year=YYYY/month=MM/day=DD/
```

### Curated

Stores cleaned responses from the standardized layer in the form of parquet.

```text
curated/quotes/year=YYYY/month=MM/day=DD/
```

### Rejected

Stores invalid respones from standardized layer 

```text
rejected/quotes/year=YYYY/month=MM/day=DD/
```


## AWS services

| Service | Purpose |
|---|---|
| AWS Lambda | Calls the stock API and processes quote records |
| Amazon EventBridge Scheduler | Invokes the ingestion function on weekdays |
| Amazon S3 | Stores raw, standardized, curated, rejected, and Athena data |
| AWS Secrets Manager | Stores the Twelve Data API key |
| AWS Glue Data Catalog | Stores table schemas and partition metadata |
| AWS Glue Crawlers | Discovers standardized JSONL and curated Parquet schemas |
| AWS Glue ETL | Validates, deduplicates, and converts JSONL to Parquet |
| Amazon Athena | Queries curated stock data using SQL |
| Amazon CloudWatch | Stores logs, metrics, and alarms |
| Amazon SNS | Sends pipeline alarm notifications |
| AWS SAM | Defines and deploys the serverless infrastructure |

## Data Quality

The ingestion and transformation layers apply validation at multiple stages.

### Lambda validation

Lambda validates incoming API responses before writing standardized records.

### Glue validation

The Glue ETL job rejects records when:

- `symbol` is missing or blank
- `price` is missing or less than or equal to zero
- `market_timestamp` is invalid
- `ingestion_timestamp` is invalid
- `volume` is negative
- `high_price` is lower than `low_price`

Valid records are deduplicated using:

```text
symbol + market_timestamp
```


## Athena Analytics

The curated layer supports analytical queries including:

- Latest quote by stock symbol
- Market gainers and losers
- Highest-volume stocks
- Daily price ranges
- Exchange-level summaries
- Seven-observation moving averages
- Day-over-day price changes
- Historical volatility
- Data freshness monitoring
- Partition-level record summaries

Queries are stored in:

```text
sql/analytics_queries.sql
```


## Deployment flow

### 1. Upload the Glue ETL script

```bash
aws s3 cp \
  src/stockpipeline/transformation/standardized_to_curated.py \
  s3://<glue-assets-bucket>/scripts/standardized_to_curated.py \
  --profile stock-pipeline
```

## Verification

A successful deployment can be verified by confirming:

- Lambda writes records to `raw/` and `standardized/`
- The standardized crawler creates the standardized Glue table
- The Glue ETL job completes successfully
- Parquet files appear under `curated/quotes/`
- Invalid records appear under `rejected/quotes/`, when applicable
- The curated crawler creates `curated_quotes`
- Athena successfully queries the curated table
- Validation queries return the expected results
