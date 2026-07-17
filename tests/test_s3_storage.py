"""Tests for Amazon S3 stock-market storage."""

import json
from datetime import UTC, datetime
from unittest.mock import Mock

from stockpipeline.ingestion.models import StockQuote
from stockpipeline.storage.s3_storage import (
    create_raw_s3_key,
    create_standardized_s3_key,
    write_raw_quotes_to_s3,
    write_standardized_quotes_to_s3,
)


TEST_TIMESTAMP = datetime(
    2026,
    7,
    11,
    15,
    30,
    45,
    tzinfo=UTC,
)


def create_test_quote() -> StockQuote:
    """Create a valid stock quote for S3 storage tests."""
    return StockQuote(
        symbol="AAPL",
        company_name="Apple Inc",
        exchange="NASDAQ",
        currency="USD",
        price=210.50,
        open_price=208.75,
        high_price=212.10,
        low_price=207.90,
        previous_close=209.25,
        change=1.25,
        change_percent=0.5974,
        volume=48_500_000,
        market_timestamp="2026-07-11",
        ingestion_timestamp="2026-07-11T15:30:45+00:00",
    )


def test_create_raw_s3_key() -> None:
    """Create the expected partitioned raw S3 key."""
    result = create_raw_s3_key(TEST_TIMESTAMP)

    assert result == (
        "raw/quotes/"
        "year=2026/"
        "month=07/"
        "day=11/"
        "hour=15/"
        "quotes_20260711T153045Z.jsonl"
    )


def test_create_standardized_s3_key() -> None:
    """Create the expected partitioned standardized S3 key."""
    result = create_standardized_s3_key(TEST_TIMESTAMP)

    assert result == (
        "standardized/quotes/"
        "year=2026/"
        "month=07/"
        "day=11/"
        "quotes_20260711T153045Z.jsonl"
    )


def test_write_raw_quotes_to_s3() -> None:
    """Upload raw records as newline-delimited JSON."""
    s3_client = Mock()

    records = [
        {
            "symbol": "AAPL",
            "close": "210.50",
        },
        {
            "symbol": "AMZN",
            "close": "225.75",
        },
    ]

    result = write_raw_quotes_to_s3(
        records=records,
        run_timestamp=TEST_TIMESTAMP,
        bucket_name="test-stock-bucket",
        s3_client=s3_client,
    )

    assert result == (
        "s3://test-stock-bucket/"
        "raw/quotes/year=2026/month=07/day=11/hour=15/"
        "quotes_20260711T153045Z.jsonl"
    )

    s3_client.put_object.assert_called_once()

    call_arguments = s3_client.put_object.call_args.kwargs

    assert call_arguments["Bucket"] == "test-stock-bucket"
    assert call_arguments["ContentType"] == "application/x-ndjson"
    assert call_arguments["ServerSideEncryption"] == "AES256"

    body = call_arguments["Body"].decode("utf-8")
    lines = body.splitlines()

    assert len(lines) == 2
    assert json.loads(lines[0]) == records[0]
    assert json.loads(lines[1]) == records[1]


def test_write_standardized_quotes_to_s3() -> None:
    """Upload standardized records as newline-delimited JSON."""
    s3_client = Mock()
    quote = create_test_quote()

    result = write_standardized_quotes_to_s3(
        quotes=[quote],
        run_timestamp=TEST_TIMESTAMP,
        bucket_name="test-stock-bucket",
        s3_client=s3_client,
    )

    assert result == (
        "s3://test-stock-bucket/"
        "standardized/quotes/year=2026/month=07/day=11/"
        "quotes_20260711T153045Z.jsonl"
    )

    call_arguments = s3_client.put_object.call_args.kwargs
    body = call_arguments["Body"].decode("utf-8")
    lines = body.splitlines()

    assert len(lines) == 1

    stored_record = json.loads(lines[0])

    assert stored_record["symbol"] == "AAPL"
    assert stored_record["price"] == 210.50
    assert stored_record["volume"] == 48_500_000
    assert stored_record["source"] == "twelve_data"