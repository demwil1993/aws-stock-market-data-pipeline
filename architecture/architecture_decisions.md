# Architecture Decisions

## ADR-001: Use direct Lambda-to-S3 delivery instead of Amazon Data Firehose

### Status

Accepted

### Context

The initial architecture placed Amazon Data Firehose between the ingestion
Lambda and Amazon S3.

The implemented pipeline retrieves five stock symbols every five minutes
during regular weekday market hours. This produces approximately 395 stock
records per trading day.

### Decision

The ingestion Lambda writes JSONL batches directly to Amazon S3.

Amazon Data Firehose is not part of the core architecture.

### Rationale

- Current data volume is very small.
- Lambda can write each batch directly to S3.
- Firehose buffering is unnecessary for five-record batches.
- Direct delivery simplifies testing and troubleshooting.
- The design requires fewer AWS resources and IAM permissions.
- The simplified design reduces operational overhead and potential cost.

### Consequences

Positive:

- Simpler infrastructure.
- Immediate and predictable S3 object creation.
- Easier unit and integration testing.
- Lower operational complexity.

Negative:

- No managed buffering or batching layer.
- No built-in Firehose failed-delivery prefix.
- Lambda owns S3 serialization and delivery.

### Future reconsideration

Firehose may be introduced if the pipeline expands to WebSocket tick data,
a much larger stock universe, multiple producers, or higher-throughput
streaming ingestion.

---

## ADR-002: Reserve curated data for Parquet

### Status

Accepted

### Context

The initial Lambda implementation stored its typed JSONL output under the
curated prefix. The original analytics design defined curated data as
partitioned Parquet produced by AWS Glue.

### Decision

Use four data zones:

- raw — original API responses in JSONL
- standardized — typed and validated JSONL from Lambda
- curated — deduplicated Parquet from Glue
- rejected — records that fail final quality checks

### Rationale

This naming clearly separates ingestion processing from analytics-ready data.

### Consequences

The existing Lambda S3 writer must change its output prefix from curated to
standardized before the Glue transformation is implemented.

---

## ADR-003: Exclude Amazon Redshift

### Status

Accepted

### Decision

Use Amazon Athena to query Parquet data directly in S3. Do not add Amazon
Redshift to the project.

### Rationale

- Redshift is unnecessary at this scale.
- It would increase cost and operational complexity.
- Athena is aligned with the serverless data-lake architecture.
- Redshift was not part of the original project scope or budget.