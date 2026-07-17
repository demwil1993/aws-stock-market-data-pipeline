"""Tests for the stock quote ingestion pipeline."""

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

from stockpipeline.ingestion.exceptions import StockAPIError
from stockpipeline.ingestion.pipeline import run_ingestion


TEST_TIMESTAMP = datetime(
    2026,
    7,
    11,
    15,
    30,
    45,
    tzinfo=UTC,
)


def create_api_response(
    symbol: str,
    close: str,
) -> dict[str, str]:
    """Create a valid Twelve Data response for pipeline tests."""
    return {
        "symbol": symbol,
        "name": f"{symbol} Company",
        "exchange": "NASDAQ",
        "currency": "USD",
        "close": close,
        "open": "100.00",
        "high": "110.00",
        "low": "90.00",
        "previous_close": "99.00",
        "change": "1.00",
        "percent_change": "1.0101",
        "volume": "1000000",
        "datetime": "2026-07-11",
    }


def test_run_ingestion_processes_all_symbols(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Process and store every symbol when all API calls succeed."""
    client = Mock()

    client.get_quote.side_effect = [
        create_api_response("AAPL", "101.00"),
        create_api_response("AMZN", "102.00"),
    ]

    monkeypatch.setattr(
        "stockpipeline.ingestion.pipeline.write_raw_quotes",
        lambda records, run_timestamp: _write_test_records(
            records=records,
            run_timestamp=run_timestamp,
            data_root=tmp_path,
            zone="raw",
        ),
    )

    monkeypatch.setattr(
        "stockpipeline.ingestion.pipeline.write_standardized_quotes",
        lambda quotes, run_timestamp: _write_test_quotes(
            quotes=quotes,
            run_timestamp=run_timestamp,
            data_root=tmp_path,
        ),
    )

    result = run_ingestion(
        client=client,
        symbols=("AAPL", "AMZN"),
        run_timestamp=TEST_TIMESTAMP,
    )

    assert result.requested_count == 2
    assert result.successful_count == 2
    assert result.failed_count == 0
    assert result.failed_symbols == ()

    assert result.raw_storage_location is not None
    assert result.standardized_storage_location is not None

    assert isinstance(result.raw_storage_location, Path)
    assert isinstance(result.standardized_storage_location, Path)

    assert result.raw_storage_location.exists()
    assert result.standardized_storage_location.exists()

    client.get_quote.assert_any_call("AAPL")
    client.get_quote.assert_any_call("AMZN")
    assert client.get_quote.call_count == 2


def test_run_ingestion_continues_after_symbol_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Continue processing after one stock symbol fails."""
    client = Mock()

    client.get_quote.side_effect = [
        create_api_response("AAPL", "101.00"),
        StockAPIError("API limit reached"),
        create_api_response("JPM", "103.00"),
    ]

    monkeypatch.setattr(
        "stockpipeline.ingestion.pipeline.write_raw_quotes",
        lambda records, run_timestamp: _write_test_records(
            records=records,
            run_timestamp=run_timestamp,
            data_root=tmp_path,
            zone="raw",
        ),
    )

    monkeypatch.setattr(
        "stockpipeline.ingestion.pipeline.write_standardized_quotes",
        lambda quotes, run_timestamp: _write_test_quotes(
            quotes=quotes,
            run_timestamp=run_timestamp,
            data_root=tmp_path,
        ),
    )

    result = run_ingestion(
        client=client,
        symbols=("AAPL", "AMZN", "JPM"),
        run_timestamp=TEST_TIMESTAMP,
    )

    assert result.requested_count == 3
    assert result.successful_count == 2
    assert result.failed_count == 1
    assert result.failed_symbols == ("AMZN",)

    assert result.raw_storage_location is not None
    assert result.standardized_storage_location is not None

    assert isinstance(result.raw_storage_location, Path)
    assert isinstance(result.standardized_storage_location, Path)

    raw_lines = (
        result.raw_storage_location
        .read_text(encoding="utf-8")
        .splitlines()
    )

    standardized_lines = (
        result.standardized_storage_location
        .read_text(encoding="utf-8")
        .splitlines()
    )

    assert len(raw_lines) == 2
    assert len(standardized_lines) == 2

    raw_records = [json.loads(line) for line in raw_lines]
    standardized_records = [
        json.loads(line) for line in standardized_lines
    ]

    assert [record["symbol"] for record in raw_records] == [
        "AAPL",
        "JPM",
    ]

    assert [record["symbol"] for record in standardized_records] == [
        "AAPL",
        "JPM",
    ]

    client.get_quote.assert_any_call("AAPL")
    client.get_quote.assert_any_call("AMZN")
    client.get_quote.assert_any_call("JPM")
    assert client.get_quote.call_count == 3


def _write_test_records(
    records,
    run_timestamp: datetime,
    data_root: Path,
    zone: str,
) -> Path:
    """Write raw test records into a temporary directory."""
    file_path = (
        data_root
        / zone
        / f"quotes_{run_timestamp:%Y%m%dT%H%M%SZ}.jsonl"
    )

    file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record))
            file.write("\n")

    return file_path


def _write_test_quotes(
    quotes,
    run_timestamp: datetime,
    data_root: Path,
) -> Path:
    """Write standardized test records into a temporary directory."""
    file_path = (
        data_root
        / "standardized"
        / f"quotes_{run_timestamp:%Y%m%dT%H%M%SZ}.jsonl"
    )

    file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open("w", encoding="utf-8") as file:
        for quote in quotes:
            file.write(json.dumps(quote.to_dict()))
            file.write("\n")

    return file_path