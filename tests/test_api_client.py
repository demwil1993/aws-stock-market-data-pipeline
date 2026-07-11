"""Tests for the Twelve Data API client."""

from unittest.mock import Mock, patch

import pytest
import requests

from stockpipeline.ingestion.api_client import TwelveDataClient
from stockpipeline.ingestion.config import Settings
from stockpipeline.ingestion.exceptions import (
    InvalidStockResponseError,
    StockAPIConnectionError,
    StockAPIError,
)


@pytest.fixture
def client() -> TwelveDataClient:
    """Create an API client with test configuration."""
    settings = Settings(
        twelve_data_api_key="test-api-key",
    )

    return TwelveDataClient(settings)


@patch("stockpipeline.ingestion.api_client.requests.get")
def test_get_quote_returns_valid_response(
    mock_get: Mock,
    client: TwelveDataClient,
) -> None:
    """Return quote data when the API response is valid."""
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "symbol": "AAPL",
        "close": "210.50",
        "datetime": "2026-07-10",
    }
    mock_get.return_value = mock_response

    result = client.get_quote("aapl")

    assert result["symbol"] == "AAPL"
    assert result["close"] == "210.50"

    mock_get.assert_called_once_with(
        "https://api.twelvedata.com/quote",
        params={
            "symbol": "AAPL",
            "apikey": "test-api-key",
        },
        timeout=15,
    )


@patch("stockpipeline.ingestion.api_client.requests.get")
def test_get_quote_rejects_api_error(
    mock_get: Mock,
    client: TwelveDataClient,
) -> None:
    """Raise an error when Twelve Data reports an API failure."""
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "status": "error",
        "message": "API limit reached",
    }
    mock_get.return_value = mock_response

    with pytest.raises(
        StockAPIError,
        match="API limit reached",
    ):
        client.get_quote("AAPL")


@patch("stockpipeline.ingestion.api_client.requests.get")
def test_get_quote_rejects_connection_failure(
    mock_get: Mock,
    client: TwelveDataClient,
) -> None:
    """Raise an error when the HTTP request fails."""
    mock_get.side_effect = requests.Timeout()

    with pytest.raises(StockAPIConnectionError):
        client.get_quote("AAPL")


@patch("stockpipeline.ingestion.api_client.requests.get")
def test_get_quote_rejects_missing_fields(
    mock_get: Mock,
    client: TwelveDataClient,
) -> None:
    """Raise an error when required fields are missing."""
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "symbol": "AAPL",
    }
    mock_get.return_value = mock_response

    with pytest.raises(
        InvalidStockResponseError,
        match="missing fields",
    ):
        client.get_quote("AAPL")


def test_get_quote_rejects_blank_symbol(
    client: TwelveDataClient,
) -> None:
    """Reject an empty stock symbol before making an API request."""
    with pytest.raises(
        ValueError,
        match="Stock symbol cannot be empty",
    ):
        client.get_quote("   ")