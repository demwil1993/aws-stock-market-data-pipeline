"""Client for retrieving stock quote data from the Twelve Data API."""

from typing import Any

import requests

from stockpipeline.ingestion.config import Settings
from stockpipeline.ingestion.exceptions import (
    InvalidStockResponseError,
    StockAPIConnectionError,
    StockAPIError,
)


class TwelveDataClient:
    """Client for interacting with the Twelve Data quote endpoint."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the API client.

        Args:
            settings: Validated application settings.
        """
        self.api_key = settings.twelve_data_api_key
        self.api_url = settings.twelve_data_api_url

    def get_quote(self, symbol: str) -> dict[str, Any]:
        """Retrieve the latest quote for a stock symbol.

        Args:
            symbol: Stock ticker symbol, such as AAPL.

        Returns:
            Raw quote data returned by Twelve Data.

        Raises:
            StockAPIConnectionError: If the HTTP request fails.
            StockAPIError: If Twelve Data returns an API error.
            InvalidStockResponseError: If required fields are missing.
        """
        normalized_symbol = symbol.strip().upper()

        if not normalized_symbol:
            raise ValueError("Stock symbol cannot be empty.")

        params = {
            "symbol": normalized_symbol,
            "apikey": self.api_key,
        }

        try:
            response = requests.get(
                self.api_url,
                params=params,
                timeout=15,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise StockAPIConnectionError(
                f"Unable to retrieve quote for {normalized_symbol}."
            ) from exc

        try:
            data: dict[str, Any] = response.json()
        except requests.JSONDecodeError as exc:
            raise InvalidStockResponseError(
                f"Twelve Data returned invalid JSON for {normalized_symbol}."
            ) from exc

        if data.get("status") == "error":
            message = data.get("message", "Unknown Twelve Data API error.")
            raise StockAPIError(
                f"Twelve Data error for {normalized_symbol}: {message}"
            )

        required_fields = {"symbol", "close", "datetime"}

        missing_fields = required_fields.difference(data)

        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise InvalidStockResponseError(
                f"Quote for {normalized_symbol} is missing fields: {missing}"
            )

        return data