# Project Phases

## Phase 1 — Local ingestion proof of concept

- Create a Twelve Data account and API key.
- Call the quote endpoint from Python.
- Normalize stock symbols.
- Convert API strings into typed application models.
- Validate required fields and business rules.
- Support multiple stock symbols.
- Add structured logging.
- Add unit tests with pytest.
- Store raw and standardized JSONL records locally.

### Status

Completed.

---

## Phase 2 — Reusable application architecture

- Organize the application as an installable Python package.
- Separate configuration, API access, models, validation, orchestration,
  storage, and Lambda handling.
- Introduce configurable storage writers.
- Support both local filesystem and Amazon S3 storage.
- Add simulated EventBridge events for local Lambda testing.
- Add unit tests for API, validation, storage, orchestration, and Lambda logic.

### Status

Completed.

---

## Phase 3 — AWS ingestion infrastructure

- Store the Twelve Data API key in AWS Secrets Manager.
- Create an encrypted Amazon S3 data-lake bucket.
- Block all public access.
- Enable bucket-owner-enforced object ownership.
- Add lifecycle policies for raw, curated, and rejected data.
- Deploy the ingestion Lambda with AWS SAM.
- Grant least-privilege S3 and Secrets Manager permissions.
- Store raw and standardized JSONL records in partitioned S3 prefixes.

### Status

Completed.

---

## Phase 4 — Scheduling and automation

- Add EventBridge Scheduler resources through AWS SAM.
- Run ingestion every five minutes during regular U.S. market hours.
- Use the America/New_York timezone to align with NYSE and Nasdaq hours.
- Support daylight saving time automatically.
- Provide an enable/disable deployment parameter.
- Verify successful unattended weekday execution.

### Status

Completed.

---

## Phase 5 — Monitoring and notifications

- Configure CloudWatch log retention.
- Create Lambda error, throttle, and duration alarms.
- Create an SNS alarm topic.
- Add an email subscription.
- Test direct SNS delivery.
- Test Lambda error detection and alarm notifications.
- Troubleshoot and repair Lambda deployment packaging.

### Status

Completed.

---

## Architecture decision — Amazon Data Firehose

The original design included Amazon Data Firehose between Lambda and S3.

The implemented architecture uses direct Lambda-to-S3 delivery because:

- The pipeline processes only five symbols every five minutes.
- The expected volume is approximately 395 records per weekday.
- Lambda can write the resulting JSONL objects directly to S3.
- Direct delivery simplifies testing and troubleshooting.
- Firehose buffering does not provide meaningful value at the current scale.
- Removing Firehose reduces infrastructure, permissions, monitoring, and cost.

Firehose remains a possible future enhancement if the project moves to:

- WebSocket tick data.
- A substantially larger symbol universe.
- Multiple event producers.
- Higher-throughput streaming ingestion.

---

## Phase 6 — Data-lake transformation

- Create an AWS Glue ETL job.
- Read standardized JSONL data from S3.
- Apply the final schema.
- Enforce data-quality rules.
- Remove duplicate stock observations.
- Route rejected records to the rejected zone.
- Write validated records as compressed Parquet.
- Partition curated records by year, month, and day.

### Status

Planned.

---

## Phase 7 — Data Catalog and Athena

- Create an AWS Glue Data Catalog database.
- Create an external table for curated Parquet data.
- Configure partition projection or automated partition registration.
- Create an Athena workgroup.
- Configure an S3 query-results location.
- Add query-scan limits.
- Create validation and analytical SQL queries.

### Status

Planned.

---

## Phase 8 — Production hardening

- Publish custom CloudWatch metrics for partial symbol failures.
- Add duplicate-run protection and idempotency controls.
- Add a dead-letter queue for failed scheduled invocations.
- Add market-calendar handling for holidays and early-close days.
- Improve retry and backoff behavior.
- Add data-quality metrics and rejected-record reporting.

### Status

Planned.

---

## Phase 9 — Portfolio polish

- Complete the README.
- Create the final architecture diagram.
- Create a data-flow diagram.
- Complete the data dictionary.
- Document deployment and teardown procedures.
- Document actual AWS cost.
- Capture Athena query results.
- Add dashboard or analytical screenshots.
- Add resume bullets and interview talking points.

### Status

Planned.