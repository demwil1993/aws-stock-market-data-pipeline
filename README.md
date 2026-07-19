# AWS Stock Market Data Pipeline

An end-to-end cloud data engineering pipeline that ingests stock market data from the Twelve Data API, validates and standardizes the records, transforms the data with AWS Glue, stores analytics-ready Parquet files in Amazon S3, and queries the curated layer with Amazon Athena.

The project uses a medallion-style architecture with raw, standardized, curated, and rejected data layers. Infrastructure is deployed using AWS SAM and AWS CloudFormation.

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

```markdown
## Data Lake Layers

### Raw

Stores unmodified responses from the Twelve Data API.

```text
raw/quotes/year=YYYY/month=MM/day=DD/

standardized/quotes/year=YYYY/month=MM/day=DD/

curated/quotes/year=YYYY/month=MM/day=DD/

rejected/quotes/year=YYYY/month=MM/day=DD/
```


## 4. AWS services

```markdown
## AWS Services

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
```

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


## 7. Analytics

```markdown
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