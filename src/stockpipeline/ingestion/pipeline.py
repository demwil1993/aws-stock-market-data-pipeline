"""Orchestration logic for stock quote ingestion."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from stockpipeline.ingestion.api_client import TwelveDataClient
from stockpipeline.ingestion.exceptions import StockPipelineError
from stockpipeline.ingestion.models import StockQuote
from stockpipeline.ingestion.validation import validate_stock_quote
from stockpipeline.storage.local_storage import (
    write_curated_quotes,
    write_raw_quotes,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestionResult:
    """Summary of a completed ingestion run."""

    requested_count: int
    successful_count: int
    failed_count: int
    failed_symbols: tuple[str, ...]
    raw_file_path: Path | None
    curated_file_path: Path | None


def run_ingestion(
    client: TwelveDataClient,
    symbols: tuple[str, ...],
    run_timestamp: datetime | None = None,
) -> IngestionResult:
    """Retrieve, validate, and store quotes for multiple symbols.

    Args:
        client: Configured Twelve Data API client.
        symbols: Stock symbols to retrieve.
        run_timestamp: Optional UTC timestamp for the ingestion run.

    Returns:
        Summary information for the completed ingestion run.
    """
    timestamp = run_timestamp or datetime.now(UTC)

    raw_quotes: list[dict[str, Any]] = []
    successful_quotes: list[StockQuote] = []
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

            successful_quotes.append(stock_quote)

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

    raw_file_path = None
    curated_file_path = None

    if raw_quotes:
        raw_file_path = write_raw_quotes(
            raw_quotes,
            run_timestamp=timestamp,
        )

        logger.info(
            "Raw quotes written: path=%s records=%s",
            raw_file_path,
            len(raw_quotes),
        )

    if successful_quotes:
        curated_file_path = write_curated_quotes(
            successful_quotes,
            run_timestamp=timestamp,
        )

        logger.info(
            "Curated quotes written: path=%s records=%s",
            curated_file_path,
            len(successful_quotes),
        )

    result = IngestionResult(
        requested_count=len(symbols),
        successful_count=len(successful_quotes),
        failed_count=len(failed_symbols),
        failed_symbols=tuple(failed_symbols),
        raw_file_path=raw_file_path,
        curated_file_path=curated_file_path,
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