"""Local entry point for the stock-market ingestion pipeline."""

import logging

from stockpipeline.ingestion.api_client import TwelveDataClient
from stockpipeline.ingestion.config import get_settings
from stockpipeline.ingestion.pipeline import run_ingestion
from stockpipeline.ingestion.watchlist import WATCHLIST
from stockpipeline.logging_config import configure_logging


logger = logging.getLogger(__name__)


def main() -> None:
    """Run the stock ingestion pipeline locally."""
    configure_logging()

    settings = get_settings()
    client = TwelveDataClient(settings)

    result = run_ingestion(
        client=client,
        symbols=WATCHLIST,
    )

    if result.failed_count:
        logger.warning(
            "Local run completed with failures: failed=%s",
            result.failed_count,
        )

    logger.info(
        "Local storage locations: raw=%s curated=%s",
        result.raw_storage_location,
        result.curated_storage_location,
    )


if __name__ == "__main__":
    main()