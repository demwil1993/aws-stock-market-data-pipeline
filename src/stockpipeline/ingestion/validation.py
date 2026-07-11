"""Validation rules for standardized stock quote records."""

from stockpipeline.ingestion.exceptions import StockValidationError
from stockpipeline.ingestion.models import StockQuote


def validate_stock_quote(quote: StockQuote) -> None:
    """Validate a standardized stock quote.

    Args:
        quote: Stock quote to validate.

    Raises:
        StockValidationError: If one or more validation rules fail.
    """
    errors: list[str] = []

    if not quote.symbol.strip():
        errors.append("symbol cannot be blank")

    if quote.price <= 0:
        errors.append("price must be greater than zero")

    if quote.open_price <= 0:
        errors.append("open_price must be greater than zero")

    if quote.high_price <= 0:
        errors.append("high_price must be greater than zero")

    if quote.low_price <= 0:
        errors.append("low_price must be greater than zero")

    if quote.previous_close <= 0:
        errors.append("previous_close must be greater than zero")

    if quote.volume < 0:
        errors.append("volume cannot be negative")

    if quote.high_price < quote.low_price:
        errors.append("high_price cannot be lower than low_price")

    if not quote.low_price <= quote.open_price <= quote.high_price:
        errors.append(
            "open_price must be between low_price and high_price"
        )

    if not quote.low_price <= quote.price <= quote.high_price:
        errors.append(
            "price must be between low_price and high_price"
        )

    if not quote.market_timestamp.strip():
        errors.append("market_timestamp cannot be blank")

    if not quote.ingestion_timestamp.strip():
        errors.append("ingestion_timestamp cannot be blank")

    if errors:
        error_message = "; ".join(errors)

        raise StockValidationError(
            f"Validation failed for {quote.symbol or 'UNKNOWN'}: "
            f"{error_message}"
        )