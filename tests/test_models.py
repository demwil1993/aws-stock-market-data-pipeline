"""Tests for stock quote data models."""

import pytest

from stockpipeline.ingestion.exceptions import InvalidStockResponseError
from stockpipeline.ingestion.models import StockQuote


def test_stock_quote_from_api_response() -> None:
    """Convert a valid API response into a typed StockQuote."""
    api_response = {
        "symbol": "aapl",
        "name": "Apple Inc",
        "exchange": "NASDAQ",
        "currency": "USD",
        "close": "210.50",
        "open": "208.75",
        "high": "212.10",
        "low": "207.90",
        "previous_close": "209.25",
        "change": "1.25",
        "percent_change": "0.5974",
        "volume": "48500000",
        "datetime": "2026-07-10",
    }

    quote = StockQuote.from_api_response(api_response)

    assert quote.symbol == "AAPL"
    assert quote.company_name == "Apple Inc"
    assert quote.price == 210.50
    assert quote.open_price == 208.75
    assert quote.high_price == 212.10
    assert quote.low_price == 207.90
    assert quote.previous_close == 209.25
    assert quote.change == 1.25
    assert quote.change_percent == 0.5974
    assert quote.volume == 48_500_000
    assert quote.market_timestamp == "2026-07-10"
    assert quote.source == "twelve_data"
    assert quote.ingestion_timestamp


def test_stock_quote_rejects_missing_required_value() -> None:
    """Raise an error when a required value is missing."""
    api_response = {
        "symbol": "AAPL",
        "name": "Apple Inc",
        "exchange": "NASDAQ",
        "currency": "USD",
        "open": "208.75",
        "high": "212.10",
        "low": "207.90",
        "previous_close": "209.25",
        "change": "1.25",
        "percent_change": "0.5974",
        "volume": "48500000",
        "datetime": "2026-07-10",
    }

    with pytest.raises(InvalidStockResponseError):
        StockQuote.from_api_response(api_response)