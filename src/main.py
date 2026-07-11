"""Local entry point for the stock-market ingestion pipeline."""

import logging
from datetime import UTC, datetime
from typing import Any

from stockpipeline.ingestion.api_client import TwelveDataClient
from stockpipeline.ingestion.config import get_settings
from stockpipeline.ingestion.exceptions import StockPipelineError
from stockpipeline.ingestion.models import StockQuote
from stockpipeline.ingestion.validation import validate_stock_quote
from stockpipeline.ingestion.watchlist import WATCHLIST
from stockpipeline.logging_config import configure_logging
from stockpipeline.storage.local_storage import (
    write_curated_quotes,
    write_raw_quotes,
)


logger = logging.getLogger(__name__)


def main() -> None:
    """Retrieve, validate, and store all monitored stock quotes."""
    configure_logging()

    run_timestamp = datetime.now(UTC)

    logger.info(
        "Starting stock quote ingestion: run_timestamp=%s",
        run_timestamp.isoformat(),
    )

    settings = get_settings()
    client = TwelveDataClient(settings)

    raw_quotes: list[dict[str, Any]] = []
    successful_quotes: list[StockQuote] = []
    failed_symbols: list[str] = []

    for symbol in WATCHLIST:
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

    if raw_quotes:
        raw_file_path = write_raw_quotes(
            raw_quotes,
            run_timestamp=run_timestamp,
        )

        logger.info(
            "Raw quotes written: path=%s records=%s",
            raw_file_path,
            len(raw_quotes),
        )

    if successful_quotes:
        curated_file_path = write_curated_quotes(
            successful_quotes,
            run_timestamp=run_timestamp,
        )

        logger.info(
            "Curated quotes written: path=%s records=%s",
            curated_file_path,
            len(successful_quotes),
        )

    logger.info(
        (
            "Ingestion completed: requested=%s "
            "successful=%s failed=%s"
        ),
        len(WATCHLIST),
        len(successful_quotes),
        len(failed_symbols),
    )

    if failed_symbols:
        logger.warning(
            "Failed symbols: %s",
            ", ".join(failed_symbols),
        )


if __name__ == "__main__":
    main()