# Data Dictionary

This document describes the primary fields used by the AWS Stock Market Data Pipeline. The pipeline stores records across raw, standardized, curated, and rejected S3 zones.

## Data zones

| Zone | Format | Purpose |
|---|---|---|
| `raw/` | JSONL | Preserves the source API response with minimal modification. |
| `standardized/` | JSONL | Stores normalized records produced by Lambda after ingestion-time validation. |
| `curated/` | Parquet | Stores typed, deduplicated, analytics-ready records produced by AWS Glue. |
| `rejected/` | Parquet | Stores records rejected by the Glue transformation with a rejection reason. |
| `athena-results/` | Athena output files | Stores Athena query results and metadata. |

## Curated quotes table

The Glue ETL job writes curated stock quotes as Snappy-compressed Parquet partitioned by `year`, `month`, and `day` derived from `market_timestamp`.

| Column | Type | Nullable | Description |
|---|---|---:|---|
| `symbol` | string | No | Uppercase stock ticker symbol, such as `AAPL`. |
| `company_name` | string | Yes | Trimmed company name returned by the market-data provider. |
| `exchange` | string | Yes | Uppercase exchange identifier, such as `NASDAQ`. |
| `currency` | string | Yes | Uppercase trading currency code, such as `USD`. |
| `price` | double | No | Current or most recent quoted price. Must be greater than zero. |
| `open_price` | double | Yes | Opening price for the quoted market session. |
| `high_price` | double | Yes | Highest quoted price for the session. When both high and low exist, high must not be below low. |
| `low_price` | double | Yes | Lowest quoted price for the session. |
| `previous_close` | double | Yes | Previous session's closing price. |
| `change` | double | Yes | Absolute price change from the previous close. |
| `change_percent` | double | Yes | Percentage price change from the previous close. |
| `volume` | bigint | Yes | Trading volume. Null is permitted; negative values are rejected. |
| `market_timestamp` | timestamp | No | Timestamp associated with the market quote. Used in the deduplication key and curated date partitions. |
| `ingestion_timestamp` | timestamp | No | Timestamp when the pipeline ingested the record. Used to retain the latest duplicate. |
| `source` | string | Yes | Lowercase source-system identifier, such as `twelve_data`. |
| `year` | string | No | Four-digit year derived from `market_timestamp`; curated partition column. |
| `month` | string | No | Two-digit month derived from `market_timestamp`; curated partition column. |
| `day` | string | No | Two-digit day derived from `market_timestamp`; curated partition column. |

## Curated business key and deduplication

The Glue job treats the following pair as the logical duplicate key:

```text
symbol + market_timestamp
```

When multiple records share that key, the record with the latest `ingestion_timestamp` is retained for the current Glue run.

## Rejected quotes table

Rejected records retain the transformed source columns and add audit fields.

| Column | Type | Description |
|---|---|---|
| `rejection_reason` | string | First quality rule that failed. |
| `source_file` | string | S3 source filename identified by Spark. |
| `rejected_at` | timestamp | Timestamp when Glue rejected the record. |
| `year` | string | Rejection year; rejected partition column. |
| `month` | string | Rejection month; rejected partition column. |
| `day` | string | Rejection day; rejected partition column. |

All other transformed quote columns are preserved when available.

## Rejection reasons

Rules are evaluated in the order shown. The first failed rule determines the rejection reason.

| Rejection reason | Condition |
|---|---|
| `MISSING_SYMBOL` | `symbol` is null or empty after trimming. |
| `INVALID_PRICE` | `price` is null after casting or is less than or equal to zero. |
| `INVALID_MARKET_TIMESTAMP` | `market_timestamp` cannot be parsed as a timestamp. |
| `INVALID_INGESTION_TIMESTAMP` | `ingestion_timestamp` cannot be parsed as a timestamp. |
| `NEGATIVE_VOLUME` | `volume` is present and less than zero. |
| `HIGH_BELOW_LOW` | Both high and low are present and `high_price < low_price`. |

## Normalization rules

| Field | Rule |
|---|---|
| `symbol` | Trim whitespace and convert to uppercase. |
| `company_name` | Trim whitespace. |
| `exchange` | Trim whitespace and convert to uppercase. |
| `currency` | Trim whitespace and convert to uppercase. |
| `source` | Trim whitespace and convert to lowercase. |
| Price fields | Cast to `double`. |
| `volume` | Cast to `long`. |
| Timestamp fields | Parse with Spark `to_timestamp`. |

## Analytical guidance

- Query `curated_quotes` for analysis, reporting, and validation.
- Filter on `year`, `month`, and `day` whenever possible to reduce Athena data scanned.
- Treat raw and standardized layers as operational or troubleshooting data rather than the primary analytical interface.
- Run the Glue ETL job before analysis when standardized data has accumulated since the last curated refresh.