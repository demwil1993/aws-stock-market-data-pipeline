"""AWS Lambda entry point for scheduled stock quote ingestion."""

import logging
from functools import partial
from typing import Any

import boto3

from stockpipeline.ingestion.api_client import TwelveDataClient
from stockpipeline.ingestion.config import get_settings
from stockpipeline.ingestion.pipeline import IngestionResult, run_ingestion
from stockpipeline.ingestion.watchlist import WATCHLIST
from stockpipeline.logging_config import configure_logging
from stockpipeline.storage.s3_storage import (
    write_curated_quotes_to_s3,
    write_raw_quotes_to_s3,
)


logger = logging.getLogger(__name__)


def _get_symbols(event: dict[str, Any]) -> tuple[str, ...]:
    """Extract an optional stock-symbol list from a Lambda event."""
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
    """Convert an ingestion result into a JSON-compatible response."""
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
    """Run stock ingestion and store results in Amazon S3."""
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
    settings = get_settings()

    if not settings.s3_bucket_name:
        raise ValueError(
            "STOCK_DATA_BUCKET is missing from the Lambda configuration."
        )

    client = TwelveDataClient(settings)
    s3_client = boto3.client("s3")

    raw_writer = partial(
        write_raw_quotes_to_s3,
        bucket_name=settings.s3_bucket_name,
        s3_client=s3_client,
    )

    curated_writer = partial(
        write_curated_quotes_to_s3,
        bucket_name=settings.s3_bucket_name,
        s3_client=s3_client,
    )

    result = run_ingestion(
        client=client,
        symbols=symbols,
        raw_writer=raw_writer,
        curated_writer=curated_writer,
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