"""AWS Lambda entry point for scheduled stock quote ingestion."""

import logging
from typing import Any

from stockpipeline.ingestion.api_client import TwelveDataClient
from stockpipeline.ingestion.config import get_settings
from stockpipeline.ingestion.pipeline import IngestionResult, run_ingestion
from stockpipeline.ingestion.watchlist import WATCHLIST
from stockpipeline.logging_config import configure_logging


logger = logging.getLogger(__name__)


def _get_symbols(event: dict[str, Any]) -> tuple[str, ...]:
    """Extract an optional stock-symbol list from a Lambda event.

    Args:
        event: EventBridge Scheduler or manually supplied Lambda event.

    Returns:
        Normalized stock symbols from the event, or the default watchlist.

    Raises:
        ValueError: If the supplied symbols value is invalid.
    """
    supplied_symbols = event.get("symbols")

    if supplied_symbols is None:
        return WATCHLIST

    if not isinstance(supplied_symbols, list):
        raise ValueError("Event field 'symbols' must be a list.")

    normalized_symbols = tuple(
        str(symbol).strip().upper()
        for symbol in supplied_symbols
        if str(symbol).strip()
    )

    if not normalized_symbols:
        raise ValueError(
            "Event field 'symbols' must contain at least one symbol."
        )

    return normalized_symbols


def _build_response(result: IngestionResult) -> dict[str, Any]:
    """Convert an ingestion result into a JSON-serializable response."""
    return {
        "status": "completed",
        "requested_count": result.requested_count,
        "successful_count": result.successful_count,
        "failed_count": result.failed_count,
        "failed_symbols": list(result.failed_symbols),
        "raw_storage_location": (
            str(result.raw_storage_location)
            if result.raw_storage_location is not None
            else None
        ),
        "curated_storage_location": (
            str(result.curated_storage_location)
            if result.curated_storage_location is not None
            else None
        ),
    }


def lambda_handler(
    event: dict[str, Any],
    context: Any,
) -> dict[str, Any]:
    """Run stock ingestion in response to a Lambda invocation.

    Args:
        event: JSON-compatible invocation payload.
        context: Lambda runtime context object.

    Returns:
        JSON-serializable ingestion summary.
    """
    configure_logging()

    request_id = getattr(
        context,
        "aws_request_id",
        "local-test",
    )

    logger.info(
        "Lambda invocation started: request_id=%s",
        request_id,
    )

    symbols = _get_symbols(event)

    logger.info(
        "Symbols selected for ingestion: symbols=%s",
        ",".join(symbols),
    )

    settings = get_settings()
    client = TwelveDataClient(settings)

    result = run_ingestion(
        client=client,
        symbols=symbols,
    )

    response = _build_response(result)

    logger.info(
        (
            "Lambda invocation completed: request_id=%s "
            "successful=%s failed=%s"
        ),
        request_id,
        result.successful_count,
        result.failed_count,
    )

    return response