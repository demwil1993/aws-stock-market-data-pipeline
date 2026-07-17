"""Amazon S3 storage utilities for stock-market records."""

import json
from collections.abc import Iterable
from datetime import datetime
from typing import Any

import boto3

from stockpipeline.ingestion.models import StockQuote


def create_raw_s3_key(run_timestamp: datetime) -> str:
    """Create the partitioned S3 key for raw quote records.

    Args:
        run_timestamp: UTC timestamp for the ingestion run.

    Returns:
        Partitioned S3 object key.
    """
    return (
        "raw/quotes/"
        f"year={run_timestamp:%Y}/"
        f"month={run_timestamp:%m}/"
        f"day={run_timestamp:%d}/"
        f"hour={run_timestamp:%H}/"
        f"quotes_{run_timestamp:%Y%m%dT%H%M%SZ}.jsonl"
    )


def create_standardized_s3_key(run_timestamp: datetime) -> str:
    """Create the partitioned S3 key for standardized quote records.

    Args:
        run_timestamp: UTC timestamp for the ingestion run.

    Returns:
        Partitioned S3 object key.
    """
    return (
        "standardized/quotes/"
        f"year={run_timestamp:%Y}/"
        f"month={run_timestamp:%m}/"
        f"day={run_timestamp:%d}/"
        f"quotes_{run_timestamp:%Y%m%dT%H%M%SZ}.jsonl"
    )


def _serialize_jsonl(
    records: Iterable[dict[str, Any]],
) -> bytes:
    """Serialize records as UTF-8 newline-delimited JSON."""
    lines = (
        json.dumps(record, ensure_ascii=False)
        for record in records
    )

    content = "\n".join(lines)

    if content:
        content += "\n"

    return content.encode("utf-8")


def write_raw_quotes_to_s3(
    records: Iterable[dict[str, Any]],
    run_timestamp: datetime,
    bucket_name: str,
    s3_client: Any | None = None,
) -> str:
    """Write raw API responses to Amazon S3.

    Args:
        records: Original responses returned by the API.
        run_timestamp: UTC timestamp used for partitioning.
        bucket_name: Destination S3 bucket.
        s3_client: Optional injected boto3 S3 client.

    Returns:
        S3 URI of the uploaded object.

    Raises:
        ValueError: If the bucket name is blank.
    """
    if not bucket_name.strip():
        raise ValueError("S3 bucket name cannot be blank.")

    client = s3_client or boto3.client("s3")
    object_key = create_raw_s3_key(run_timestamp)
    body = _serialize_jsonl(records)

    client.put_object(
        Bucket=bucket_name,
        Key=object_key,
        Body=body,
        ContentType="application/x-ndjson",
        ServerSideEncryption="AES256",
    )

    return f"s3://{bucket_name}/{object_key}"


def write_standardized_quotes_to_s3(
    quotes: Iterable[StockQuote],
    run_timestamp: datetime,
    bucket_name: str,
    s3_client: Any | None = None,
) -> str:
    """Write standardized stock quotes to Amazon S3.

    Args:
        quotes: Validated and standardized stock quotes.
        run_timestamp: UTC timestamp used for partitioning.
        bucket_name: Destination S3 bucket.
        s3_client: Optional injected boto3 S3 client.

    Returns:
        S3 URI of the uploaded object.

    Raises:
        ValueError: If the bucket name is blank.
    """
    if not bucket_name.strip():
        raise ValueError("S3 bucket name cannot be blank.")

    client = s3_client or boto3.client("s3")
    object_key = create_standardized_s3_key(run_timestamp)

    records = (
        quote.to_dict()
        for quote in quotes
    )

    body = _serialize_jsonl(records)

    client.put_object(
        Bucket=bucket_name,
        Key=object_key,
        Body=body,
        ContentType="application/x-ndjson",
        ServerSideEncryption="AES256",
    )

    return f"s3://{bucket_name}/{object_key}"