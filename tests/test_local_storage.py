"""Tests for local raw and curated storage."""

import json
from datetime import UTC, datetime
from pathlib import Path

from stockpipeline.ingestion.models import StockQuote
from stockpipeline.storage.local_storage import (
    create_curated_partition_path,
    create_raw_partition_path,
    write_curated_quotes,
    write_raw_quotes,
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
    """Create a valid stock quote for storage tests."""
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


def test_create_raw_partition_path(tmp_path: Path) -> None:
    """Create the expected raw partition directory."""
    result = create_raw_partition_path(
        run_timestamp=TEST_TIMESTAMP,
        data_root=tmp_path,
    )

    expected = (
        tmp_path
        / "raw"
        / "quotes"
        / "year=2026"
        / "month=07"
        / "day=11"
        / "hour=15"
    )

    assert result == expected
    assert result.exists()
    assert result.is_dir()


def test_create_curated_partition_path(tmp_path: Path) -> None:
    """Create the expected curated partition directory."""
    result = create_curated_partition_path(
        run_timestamp=TEST_TIMESTAMP,
        data_root=tmp_path,
    )

    expected = (
        tmp_path
        / "curated"
        / "quotes"
        / "year=2026"
        / "month=07"
        / "day=11"
    )

    assert result == expected
    assert result.exists()
    assert result.is_dir()


def test_write_raw_quotes(tmp_path: Path) -> None:
    """Write raw API responses as newline-delimited JSON."""
    records = [
        {
            "symbol": "AAPL",
            "close": "210.50",
            "datetime": "2026-07-11",
        },
        {
            "symbol": "AMZN",
            "close": "225.75",
            "datetime": "2026-07-11",
        },
    ]

    file_path = write_raw_quotes(
        records=records,
        run_timestamp=TEST_TIMESTAMP,
        data_root=tmp_path,
    )

    expected_name = "quotes_20260711T153045Z.jsonl"

    assert file_path.name == expected_name
    assert file_path.exists()

    lines = file_path.read_text(encoding="utf-8").splitlines()

    assert len(lines) == 2
    assert json.loads(lines[0]) == records[0]
    assert json.loads(lines[1]) == records[1]


def test_write_curated_quotes(tmp_path: Path) -> None:
    """Write standardized stock quotes as newline-delimited JSON."""
    quotes = [create_test_quote()]

    file_path = write_curated_quotes(
        quotes=quotes,
        run_timestamp=TEST_TIMESTAMP,
        data_root=tmp_path,
    )

    expected_name = "quotes_20260711T153045Z.jsonl"

    assert file_path.name == expected_name
    assert file_path.exists()

    lines = file_path.read_text(encoding="utf-8").splitlines()

    assert len(lines) == 1

    stored_record = json.loads(lines[0])

    assert stored_record["symbol"] == "AAPL"
    assert stored_record["price"] == 210.50
    assert stored_record["volume"] == 48_500_000
    assert stored_record["source"] == "twelve_data"