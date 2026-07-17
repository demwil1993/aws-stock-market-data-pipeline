"""Run the stock-market ingestion pipeline locally."""

import logging
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"

if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))


from stockpipeline.ingestion.api_client import TwelveDataClient
from stockpipeline.ingestion.config import get_settings
from stockpipeline.ingestion.pipeline import run_ingestion
from stockpipeline.ingestion.watchlist import WATCHLIST
from stockpipeline.logging_config import configure_logging


logger = logging.getLogger(__name__)


def main() -> None:
    """Run the stock ingestion pipeline using local storage."""
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
        "Local storage locations: raw=%s standardized=%s",
        result.raw_storage_location,
        result.standardized_storage_location,
    )


if __name__ == "__main__":
    main()