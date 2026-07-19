# Architecture Decisions

This document records the major technical decisions for the AWS Stock Market Data Pipeline. These decisions represent the implementation at the point of the project freeze.

## ADR-001: Use direct Lambda-to-S3 delivery instead of Amazon Data Firehose

### Status

Accepted

### Context

The initial architecture placed Amazon Data Firehose between the ingestion Lambda function and Amazon S3. The implemented pipeline retrieves five stock symbols every five minutes during regular weekday market hours, producing approximately 395 stock records per trading day.

### Decision

The ingestion Lambda function writes JSONL batches directly to Amazon S3. Amazon Data Firehose is not part of the implemented architecture.

### Rationale

- The current data volume is small.
- Lambda can serialize and write each batch directly to S3.
- Firehose buffering is unnecessary for five-record batches.
- Direct delivery simplifies testing and troubleshooting.
- The design requires fewer AWS resources and IAM permissions.
- The simplified architecture reduces operational overhead and cost.

### Consequences

**Positive**

- Simpler infrastructure.
- Immediate and predictable S3 object creation.
- Easier unit and integration testing.
- Lower operational complexity.

**Negative**

- No managed buffering or batching layer.
- No built-in Firehose failed-delivery prefix.
- Lambda owns JSONL serialization and S3 delivery.

### Future reconsideration

Firehose may be appropriate if the project expands to WebSocket tick data, a much larger stock universe, multiple producers, or higher-throughput streaming ingestion.

---

## ADR-002: Use separate raw, standardized, curated, and rejected data zones

### Status

Accepted

### Context

An early version of the ingestion workflow stored typed JSONL output under the `curated/` prefix. The intended analytics architecture defines curated data as deduplicated, partitioned Parquet produced by AWS Glue.

### Decision

Use four S3 data zones:

- `raw/` — original API responses stored as JSONL.
- `standardized/` — typed and validated JSONL produced by Lambda.
- `curated/` — deduplicated, analytics-ready Parquet produced by AWS Glue.
- `rejected/` — records that fail final Glue transformation quality checks.

### Rationale

- Each layer has one clear purpose.
- Source fidelity is preserved in the raw layer.
- Lambda performs lightweight ingestion-time validation and standardization.
- Glue performs analytics-oriented typing, validation, deduplication, and Parquet conversion.
- Invalid records remain available for investigation instead of being silently discarded.

### Consequences

- Storage paths and IAM policies must support all four prefixes.
- Analysts should query the curated layer rather than raw or standardized files.
- New standardized data does not appear in curated data until the Glue ETL job runs.

---

## ADR-003: Use AWS Glue for batch transformation to partitioned Parquet

### Status

Accepted

### Context

The standardized layer contains JSONL records that are suitable for durable storage but are not optimized for analytical querying.

### Decision

Use the `standardized_to_curated.py` AWS Glue ETL job to:

- normalize selected string fields;
- enforce numeric and timestamp data types;
- assign rejection reasons to invalid records;
- separate valid and rejected records;
- retain the latest ingestion for duplicate `symbol` and `market_timestamp` combinations;
- write valid records as Snappy-compressed Parquet;
- partition curated output by market year, month, and day;
- partition rejected output by rejection year, month, and day.

### Rationale

- Parquet reduces scanned data and improves Athena query performance.
- Spark window functions provide a clear deduplication strategy.
- Partitioning supports date-oriented analytical queries.
- Rejected output creates an auditable data-quality path.

### Consequences

- The Glue script must be uploaded separately to the Glue assets S3 bucket before deployment or execution.
- The Glue job depends on a Data Catalog table for the standardized source.
- Without job bookmarks or an incremental filter, each run may reprocess previously cataloged standardized files.

---

## ADR-004: Run the Glue ETL job on demand

### Status

Accepted

### Context

Ingestion is automated, but the project does not serve a continuously refreshed dashboard or a strict reporting service-level agreement. Adding orchestration for the Glue job would increase implementation complexity.

### Decision

Keep the ingestion Lambda schedule automated and run the Glue ETL job manually when refreshed curated data is needed.

The operating workflow is:

1. Lambda continues writing new raw and standardized records.
2. An analyst or operator starts the Glue ETL job before querying newly arrived data.
3. After the job succeeds, Athena queries use the refreshed curated Parquet data.

### Rationale

- On-demand processing is sufficient for the project scale and portfolio objective.
- It separates ingestion from analytical batch processing.
- It avoids unnecessary Glue executions when no analysis is planned.
- The design can later be automated with EventBridge, Step Functions, or Glue Workflows without changing the transformation logic.

### Consequences

- Curated data can lag behind standardized data.
- Analysts must confirm that the Glue job has completed before expecting the newest records in Athena.
- The manual operating step must be documented clearly.

---

## ADR-005: Run Glue Crawlers only when metadata discovery is required

### Status

Accepted

### Context

Glue Crawlers discover S3 schemas and update Data Catalog metadata. Re-running them for every batch is unnecessary when schemas and table locations remain stable.

### Decision

Do not schedule the standardized or curated crawlers. Run them during initial deployment and again only when the schema, partition structure, or table location changes, or when new metadata must be discovered.

### Rationale

- The current schemas are stable.
- Athena can query newly written partitions through the existing table design when metadata remains compatible.
- Avoiding unnecessary crawler runs reduces operational work and cost.

### Consequences

- Schema changes require an explicit crawler run and validation.
- Operators must distinguish between transformation execution and metadata discovery; crawlers do not move or transform data.

---

## ADR-006: Use Athena instead of Amazon Redshift

### Status

Accepted

### Context

The project requires SQL analytics over a small volume of curated Parquet data in Amazon S3.

### Decision

Use Amazon Athena to query curated Parquet data directly in S3. Do not add Amazon Redshift.

### Rationale

- Redshift is unnecessary at the current scale.
- Athena aligns with the serverless data-lake architecture.
- Athena avoids cluster provisioning and administration.
- Query costs remain low because curated data is compressed and partitioned.
- Redshift was outside the project scope and budget.

### Consequences

- Query performance depends on good partition filtering and efficient file layout.
- Athena results are written to the configured `athena-results/` S3 prefix.
- A warehouse may be reconsidered if concurrency, performance, governance, or dimensional-model requirements grow substantially.

---

## ADR-007: Use AWS SAM and CloudFormation for infrastructure

### Status

Accepted

### Context

The project contains multiple related AWS resources, permissions, schedules, alarms, crawlers, and a Glue job that should be reproducible.

### Decision

Define deployable infrastructure in `infrastructure/template.yaml` and deploy it with AWS SAM/CloudFormation.

The Glue ETL Python script remains an external S3 asset and is uploaded separately because SAM does not automatically package arbitrary Glue script files referenced by `ScriptLocation`.

### Rationale

- Infrastructure as Code makes the environment reproducible.
- CloudFormation records resource dependencies and changes.
- SAM simplifies Lambda packaging and deployment.
- Separating the Glue script upload reflects how the Glue job consumes an S3-hosted script.

### Consequences

- Deployment requires both an S3 script upload and `sam deploy`.
- Local `samconfig.toml` may contain environment-specific values and should not be committed.
- `samconfig.example.toml` documents the expected configuration shape.

---

## ADR-008: Store the market-data API key in AWS Secrets Manager

### Status

Accepted

### Decision

Store the Twelve Data API key in AWS Secrets Manager and pass only the secret ARN to the Lambda function through configuration.

### Rationale

- Credentials are not embedded in source code or committed files.
- Secrets Manager supports controlled access through IAM.
- The design is safer than storing the key directly in environment files or CloudFormation parameters.

### Consequences

- The secret must exist before deployment or be provided as a valid deployment parameter.
- The Lambda execution role requires permission to retrieve the configured secret.

---

## ADR-009: Validate Glue transformations through end-to-end checks instead of local PySpark tests

### Status

Accepted

### Context

Local unit testing of the Glue Spark transformation would require installing and maintaining Java and PySpark. The project already validates the transformation in AWS using real Glue, S3, Data Catalog, and Athena resources.

### Decision

Do not add `test_transformation.py` or `test_data_quality.py` to the local test suite. Retain the existing Python unit tests for ingestion, storage, validation, models, and Lambda behavior. Validate the Glue transformation through integration execution and Athena SQL checks.

### Validation evidence

- The Glue ETL job completes successfully.
- Curated Parquet files are written to S3.
- Rejected records are routed to the rejected prefix when applicable.
- The curated crawler registers the analytics table.
- `sql/validation_queries.sql` verifies data-quality expectations.
- `sql/analytics_queries.sql` verifies analytical usability.

### Consequences

- Spark logic is not unit tested locally.
- Transformation validation requires access to the deployed AWS environment.
- The README and deployment guide must clearly describe the integration-test procedure.

---

## ADR-010: Freeze core implementation after successful end-to-end validation

### Status

Accepted

### Context

The ingestion, storage, transformation, cataloging, monitoring, validation, and analytics components have been deployed and tested successfully. Additional orchestration or services would expand scope without being necessary to demonstrate the project goals.

### Decision

Freeze the core implementation at the current architecture. Subsequent work should focus on documentation, diagrams, screenshots, cost reporting, repository cleanup, and portfolio presentation rather than new pipeline features.

### Included at freeze

- EventBridge Scheduler-driven Lambda ingestion.
- Twelve Data API integration through Secrets Manager.
- Raw and standardized JSONL storage in S3.
- On-demand Glue ETL to curated and rejected Parquet layers.
- Glue Data Catalog and Crawlers.
- Athena validation and analytics queries.
- CloudWatch alarms and SNS notification support.
- AWS SAM/CloudFormation infrastructure.
- Local unit tests for the non-Spark Python components.

### Explicitly excluded

- Amazon Data Firehose.
- Amazon Redshift.
- Automatic Glue ETL scheduling.
- Scheduled crawler execution.
- Step Functions or Glue Workflow orchestration.
- Local PySpark transformation tests.
- CI/CD automation.