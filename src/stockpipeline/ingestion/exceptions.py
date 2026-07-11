"""Custom exceptions for stock-market data ingestion."""


class StockPipelineError(Exception):
    """Base exception for the stock-market pipeline."""


class StockAPIError(StockPipelineError):
    """Raised when the stock API returns an error response."""


class StockAPIConnectionError(StockPipelineError):
    """Raised when the application cannot connect to the stock API."""


class InvalidStockResponseError(StockPipelineError):
    """Raised when the stock API response is missing required data."""


class StockValidationError(StockPipelineError):
    """Raised when a standardized stock quote fails validation."""