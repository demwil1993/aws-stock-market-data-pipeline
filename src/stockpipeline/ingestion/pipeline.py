"""Orchestration logic for stock quote ingestion."""

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from stockpipeline.ingestion.api_client import TwelveDataClient
from stockpipeline.ingestion.exceptions import StockPipelineError
from stockpipeline.ingestion.models import StockQuote
from stockpipeline.ingestion.validation import validate_stock_quote
from stockpipeline.storage.local_storage import (
    write_raw_quotes,
    write_standardized_quotes,
)


logger = logging.getLogger(__name__)


RawWriter = Callable[
    [Iterable[dict[str, Any]], datetime],
    Path | str,
]

StandardizedWriter = Callable[
    [Iterable[StockQuote], datetime],
    Path | str,
]


@dataclass(frozen=True)
class IngestionResult:
    """Summary of a completed ingestion run."""

    requested_count: int
    successful_count: int
    failed_count: int
    failed_symbols: tuple[str, ...]
    raw_storage_location: Path | str | None
    standardized_storage_location: Path | str | None


def _default_raw_writer(
    records: Iterable[dict[str, Any]],
    run_timestamp: datetime,
) -> Path:
    """Write raw records using the local storage implementation."""
    return write_raw_quotes(
        records=records,
        run_timestamp=run_timestamp,
    )


def _default_standardized_writer(
    quotes: Iterable[StockQuote],
    run_timestamp: datetime,
) -> Path:
    """Write standardized records using the local storage implementation."""
    return write_standardized_quotes(
        quotes=quotes,
        run_timestamp=run_timestamp,
    )


def run_ingestion(
    client: TwelveDataClient,
    symbols: tuple[str, ...],
    run_timestamp: datetime | None = None,
    raw_writer: RawWriter = _default_raw_writer,
    standardized_writer: StandardizedWriter = _default_standardized_writer,
) -> IngestionResult:
    """Retrieve, validate, and store quotes for multiple symbols.

    Args:
        client: Configured Twelve Data API client.
        symbols: Stock symbols to retrieve.
        run_timestamp: Optional UTC timestamp for the ingestion run.
        raw_writer: Function used to store raw API responses.
        standardized_writer: Function used to store standardized quotes.

    Returns:
        Summary information for the completed ingestion run.
    """
    timestamp = run_timestamp or datetime.now(UTC)

    raw_quotes: list[dict[str, Any]] = []
    standardized_quotes: list[StockQuote] = []
    failed_symbols: list[str] = []

    logger.info(
        "Starting stock quote ingestion: run_timestamp=%s symbols=%s",
        timestamp.isoformat(),
        len(symbols),
    )

    for symbol in symbols:
        try:
            logger.info("Requesting quote for symbol=%s", symbol)

            raw_quote = client.get_quote(symbol)
            raw_quotes.append(raw_quote)

            stock_quote = StockQuote.from_api_response(raw_quote)
            validate_stock_quote(stock_quote)

            standardized_quotes.append(stock_quote)

            logger.info(
                (
                    "Quote retrieved and validated successfully: "
                    "symbol=%s price=%s volume=%s"
                ),
                stock_quote.symbol,
                stock_quote.price,
                stock_quote.volume,
            )

        except (StockPipelineError, ValueError) as exc:
            failed_symbols.append(symbol)

            logger.error(
                "Quote processing failed: symbol=%s error=%s",
                symbol,
                exc,
            )

    raw_storage_location: Path | str | None = None
    standardized_storage_location: Path | str | None = None

    if raw_quotes:
        raw_storage_location = raw_writer(
            raw_quotes,
            timestamp,
        )

        logger.info(
            "Raw quotes written: location=%s records=%s",
            raw_storage_location,
            len(raw_quotes),
        )

    if standardized_quotes:
        standardized_storage_location = standardized_writer(
            standardized_quotes,
            timestamp,
        )

        logger.info(
            "Standardized quotes written: location=%s records=%s",
            standardized_storage_location,
            len(standardized_quotes),
        )

    result = IngestionResult(
        requested_count=len(symbols),
        successful_count=len(standardized_quotes),
        failed_count=len(failed_symbols),
        failed_symbols=tuple(failed_symbols),
        raw_storage_location=raw_storage_location,
        standardized_storage_location=standardized_storage_location,
    )

    logger.info(
        (
            "Ingestion completed: requested=%s "
            "successful=%s failed=%s"
        ),
        result.requested_count,
        result.successful_count,
        result.failed_count,
    )

    if result.failed_symbols:
        logger.warning(
            "Failed symbols: %s",
            ", ".join(result.failed_symbols),
        )

    return result