"""Tests for the AWS Lambda ingestion handler."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from stockpipeline.ingestion.lambda_function import (
    _build_response,
    _get_symbols,
    lambda_handler,
)
from stockpipeline.ingestion.pipeline import IngestionResult
from stockpipeline.ingestion.watchlist import WATCHLIST


class TestLambdaContext:
    """Minimal Lambda context used by unit tests."""

    aws_request_id = "test-request-id"


def test_get_symbols_uses_default_watchlist() -> None:
    """Use the configured watchlist when no symbols are supplied."""
    assert _get_symbols({}) == WATCHLIST


def test_get_symbols_normalizes_supplied_symbols() -> None:
    """Normalize symbols supplied through the event."""
    event = {
        "symbols": [
            " aapl ",
            "amzn",
            "JPM",
        ]
    }

    assert _get_symbols(event) == (
        "AAPL",
        "AMZN",
        "JPM",
    )


def test_get_symbols_rejects_non_list_value() -> None:
    """Reject an invalid symbols event value."""
    with pytest.raises(
        ValueError,
        match="must be a list",
    ):
        _get_symbols({"symbols": "AAPL"})


def test_get_symbols_rejects_empty_list() -> None:
    """Reject a symbol list that contains no usable values."""
    with pytest.raises(
        ValueError,
        match="at least one symbol",
    ):
        _get_symbols({"symbols": ["", "   "]})


def test_build_response_is_json_serializable() -> None:
    """Convert Path values and tuples into JSON-compatible values."""
    result = IngestionResult(
        requested_count=2,
        successful_count=1,
        failed_count=1,
        failed_symbols=("AMZN",),
        raw_storage_location=Path("data/raw/test.jsonl"),
        curated_storage_location=Path("data/curated/test.jsonl"),
    )

    response = _build_response(result)

    assert response == {
        "status": "completed",
        "requested_count": 2,
        "successful_count": 1,
        "failed_count": 1,
        "failed_symbols": ["AMZN"],
        "raw_storage_location": str(
            Path("data/raw/test.jsonl")
        ),
        "curated_storage_location": str(
            Path("data/curated/test.jsonl")
        ),
    }


@patch(
    "stockpipeline.ingestion.lambda_function.run_ingestion"
)
@patch(
    "stockpipeline.ingestion.lambda_function.TwelveDataClient"
)
@patch(
    "stockpipeline.ingestion.lambda_function.get_settings"
)
def test_lambda_handler_runs_ingestion(
    mock_get_settings: Mock,
    mock_client_class: Mock,
    mock_run_ingestion: Mock,
) -> None:
    """Create the client and run ingestion using event symbols."""
    mock_settings = Mock()
    mock_client = Mock()

    mock_get_settings.return_value = mock_settings
    mock_client_class.return_value = mock_client

    mock_run_ingestion.return_value = IngestionResult(
        requested_count=2,
        successful_count=2,
        failed_count=0,
        failed_symbols=(),
        raw_storage_location="s3://example/raw/test.jsonl",
        curated_storage_location="s3://example/curated/test.jsonl",
    )

    event = {
        "symbols": [
            "AAPL",
            "AMZN",
        ]
    }

    response = lambda_handler(
        event=event,
        context=TestLambdaContext(),
    )

    mock_get_settings.assert_called_once_with()
    mock_client_class.assert_called_once_with(mock_settings)

    mock_run_ingestion.assert_called_once_with(
        client=mock_client,
        symbols=("AAPL", "AMZN"),
    )

    assert response["status"] == "completed"
    assert response["requested_count"] == 2
    assert response["successful_count"] == 2
    assert response["failed_count"] == 0