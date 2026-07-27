# Data Flow

## Overview

This project implements a serverless batch data pipeline for collecting, validating, transforming, and analyzing stock market quote data on AWS.

The pipeline separates ingestion from transformation:

- **Ingestion runs automatically** on a weekday schedule.
- **Transformation runs on demand** when updated curated data is needed.
- **Analytics runs on demand** through Amazon Athena.

```text
Amazon EventBridge Scheduler
        ↓
AWS Lambda ingestion
        ↓
Twelve Data API
        ↓
Amazon S3 raw and standardized zones
        ↓
AWS Glue ETL job (on demand)
        ↓
Amazon S3 curated and rejected zones
        ↓
AWS Glue Data Catalog
        ↓
Amazon Athena
```

---

## 1. Scheduled ingestion

Amazon EventBridge Scheduler invokes the ingestion Lambda function during configured weekday market hours. The schedule triggers ingestion only; it does not start the Glue ETL job or Glue Crawlers.

The Lambda function:

1. Loads configuration and the stock watchlist.
2. Retrieves the Twelve Data API key from AWS Secrets Manager.
3. Requests quote data for the configured stock symbols.
4. Validates the API response.
5. Writes original records to the raw zone.
6. Writes validated and normalized records to the standardized zone.
7. Emits logs and metrics to Amazon CloudWatch.

---

## 2. Raw data zone

The raw zone preserves original API responses in JSONL format.

```text
s3://<stock-data-bucket>/raw/quotes/
    year=YYYY/
    month=MM/
    day=DD/
    hour=HH/
    quotes_<timestamp>.jsonl
```

Characteristics:

- Original API values are retained.
- Files are treated as immutable.
- The zone supports troubleshooting and historical replay.
- No analytical transformations are applied.

---

## 3. Standardized data zone

The standardized zone contains validated and normalized JSONL records produced by Lambda.

```text
s3://<stock-data-bucket>/standardized/quotes/
    year=YYYY/
    month=MM/
    day=DD/
    quotes_<timestamp>.jsonl
```

Typical standardization includes:

- trimming string values
- normalizing symbol and exchange casing
- validating required fields
- converting values to consistent representations
- adding ingestion metadata

New files accumulate here until the Glue ETL job is run.

---

## 4. Glue Data Catalog source table

A Glue Crawler discovers the standardized S3 structure and creates or updates the standardized source table in the AWS Glue Data Catalog.

The crawler:

- does not move data
- does not transform data
- does not start the Glue job
- is run on demand when schema or metadata discovery needs to be refreshed

The Glue ETL job reads standardized data through this catalog table.

---

## 5. On-demand Glue ETL transformation

The `standardized_to_curated.py` Glue job is run manually when refreshed analytics data is needed.

Typical analyst workflow:

1. Allow scheduled Lambda ingestion to accumulate standardized records.
2. Start the Glue ETL job in AWS Glue.
3. Wait for the job to complete.
4. Query the refreshed curated table in Athena.

The Glue job:

- reads records visible through the standardized catalog table
- casts fields to analytical data types
- normalizes text fields
- validates final data quality rules
- separates valid and rejected records
- deduplicates valid records
- retains the newest ingestion for each symbol and market timestamp
- derives partition columns from the market timestamp
- writes Snappy-compressed Parquet output

The Glue ETL script is stored in a separate Glue assets bucket:

```text
s3://<glue-assets-bucket>/scripts/standardized_to_curated.py
```

Temporary Glue files are stored under:

```text
s3://<glue-assets-bucket>/temporary/
```

---

## 6. Rejected data zone

Records that fail final Glue quality checks are written to the rejected zone as partitioned Parquet.

```text
s3://<stock-data-bucket>/rejected/quotes/
    year=YYYY/
    month=MM/
    day=DD/
    part-*.snappy.parquet
```

Current rejection conditions include:

- missing symbol
- invalid or non-positive price
- invalid market timestamp
- invalid ingestion timestamp
- negative volume
- high price below low price

Rejected records also include `rejection_reason`, `rejected_at`, source file information, and rejection-date partition columns.

---

## 7. Curated data zone

Valid records are written to the curated zone as partitioned Parquet.

```text
s3://<stock-data-bucket>/curated/quotes/
    year=YYYY/
    month=MM/
    day=DD/
    part-*.snappy.parquet
```

Curated data is:

- typed
- normalized
- deduplicated
- analytics-ready
- partitioned by market date
- compressed using Snappy

The curated layer is the authoritative analytical dataset for the project.

---

## 8. Curated catalog table

A second Glue Crawler discovers the curated Parquet structure and creates or updates the curated table in the Glue Data Catalog.

The curated crawler is run on demand. It usually does not need to run after every ETL execution when the S3 location and schema are unchanged.

Run it again when metadata, schema, or partition discovery needs to be refreshed.

---

## 9. Athena analytics

Amazon Athena queries curated Parquet data through the Glue Data Catalog.

Athena is used for:

- data validation
- duplicate detection
- freshness checks
- price and volume analysis
- latest quote analysis
- gainers and losers
- exchange summaries
- moving averages
- volatility analysis

Query files are stored in:

```text
sql/
├── analytics_queries.sql
└── validation_queries.sql
```

Athena query results are written to:

```text
s3://<stock-data-bucket>/athena-results/
```

This location contains CSV query results, metadata files, and the `Unsaved/` folder created by Athena.

---

## 10. Monitoring and alerting

Amazon CloudWatch collects logs and operational metrics for Lambda and Glue.

CloudWatch Alarms monitor conditions such as:

- Lambda errors
- Lambda throttles
- Lambda duration

Amazon SNS provides email notifications for configured alarm actions. AWS Secrets Manager stores the Twelve Data API key so it is not committed to source control or embedded in the Lambda package.

---

## 11. Infrastructure deployment

AWS SAM and CloudFormation define and deploy the project infrastructure.

The Glue ETL script is uploaded separately to the Glue assets bucket because the Glue job references its S3 location.

---

## Operational summary

### Automatic

- EventBridge invokes Lambda on the configured weekday schedule.
- Lambda retrieves stock data.
- Lambda writes raw and standardized JSONL files.
- CloudWatch captures logs and metrics.
- SNS sends configured alarm notifications.

### On demand

- Standardized Glue Crawler
- Glue ETL job
- Curated Glue Crawler
- Athena queries

---

## Design intent

This design intentionally keeps ingestion automated and transformation on demand.

That approach:

- reduces unnecessary Glue executions
- keeps costs low
- reflects a batch analytics workflow
- allows data to accumulate before transformation
- preserves separation between ingestion and analytics processing
- avoids unnecessary orchestration complexity at the current project scale

If the project expands into a production reporting system, the Glue ETL job could be automated with EventBridge, AWS Step Functions, or another orchestration service.
