"""Tests for stock quote validation rules."""

from dataclasses import replace

import pytest

from stockpipeline.ingestion.exceptions import StockValidationError
from stockpipeline.ingestion.models import StockQuote
from stockpipeline.ingestion.validation import validate_stock_quote


def create_valid_quote() -> StockQuote:
    """Create a valid stock quote for test cases."""
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
        market_timestamp="2026-07-10",
        ingestion_timestamp="2026-07-10T15:30:00+00:00",
    )


def test_valid_stock_quote_passes_validation() -> None:
    """Accept a quote that satisfies every validation rule."""
    quote = create_valid_quote()

    validate_stock_quote(quote)


def test_negative_price_fails_validation() -> None:
    """Reject a quote with a negative closing price."""
    quote = replace(create_valid_quote(), price=-1.0)

    with pytest.raises(
        StockValidationError,
        match="price must be greater than zero",
    ):
        validate_stock_quote(quote)


def test_negative_volume_fails_validation() -> None:
    """Reject a quote with negative volume."""
    quote = replace(create_valid_quote(), volume=-1)

    with pytest.raises(
        StockValidationError,
        match="volume cannot be negative",
    ):
        validate_stock_quote(quote)


def test_high_price_below_low_price_fails_validation() -> None:
    """Reject a quote when the daily high is below the daily low."""
    quote = replace(
        create_valid_quote(),
        high_price=205.00,
        low_price=207.90,
    )

    with pytest.raises(
        StockValidationError,
        match="high_price cannot be lower than low_price",
    ):
        validate_stock_quote(quote)


def test_price_outside_daily_range_fails_validation() -> None:
    """Reject a closing price outside the day's high-low range."""
    quote = replace(create_valid_quote(), price=215.00)

    with pytest.raises(
        StockValidationError,
        match="price must be between low_price and high_price",
    ):
        validate_stock_quote(quote)