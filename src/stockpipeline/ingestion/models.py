"""Data models for stock-market ingestion."""

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from stockpipeline.ingestion.exceptions import InvalidStockResponseError


@dataclass(frozen=True)
class StockQuote:
    """Standardized stock quote used throughout the pipeline."""

    symbol: str
    company_name: str
    exchange: str
    currency: str
    price: float
    open_price: float
    high_price: float
    low_price: float
    previous_close: float
    change: float
    change_percent: float
    volume: int
    market_timestamp: str
    ingestion_timestamp: str
    source: str = "twelve_data"

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "StockQuote":
        """Create a standardized quote from a Twelve Data response.

        Args:
            data: Raw JSON response from Twelve Data.

        Returns:
            A validated and typed StockQuote instance.

        Raises:
            InvalidStockResponseError: If required values are missing or invalid.
        """
        try:
            return cls(
                symbol=str(data["symbol"]).strip().upper(),
                company_name=str(data.get("name", "")).strip(),
                exchange=str(data.get("exchange", "")).strip(),
                currency=str(data.get("currency", "USD")).strip(),
                price=float(data["close"]),
                open_price=float(data["open"]),
                high_price=float(data["high"]),
                low_price=float(data["low"]),
                previous_close=float(data["previous_close"]),
                change=float(data["change"]),
                change_percent=float(data["percent_change"]),
                volume=int(float(data["volume"])),
                market_timestamp=str(data["datetime"]),
                ingestion_timestamp=datetime.now(UTC).isoformat(),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidStockResponseError(
                "Unable to convert the API response into a StockQuote."
            ) from exc

    def to_dict(self) -> dict[str, Any]:
        """Return the quote as a dictionary."""
        return asdict(self)