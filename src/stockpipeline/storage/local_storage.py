"""Local storage utilities for raw and curated stock-market records."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from stockpipeline.ingestion.models import StockQuote


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_ROOT = PROJECT_ROOT / "data"


def create_raw_partition_path(
    run_timestamp: datetime,
    data_root: Path = DEFAULT_DATA_ROOT,
) -> Path:
    """Create the partitioned directory for raw quote records.

    Args:
        run_timestamp: UTC timestamp for the ingestion run.
        data_root: Root directory where pipeline data is stored.

    Returns:
        Path to the raw partition directory.
    """
    partition_path = (
        data_root
        / "raw"
        / "quotes"
        / f"year={run_timestamp:%Y}"
        / f"month={run_timestamp:%m}"
        / f"day={run_timestamp:%d}"
        / f"hour={run_timestamp:%H}"
    )

    partition_path.mkdir(parents=True, exist_ok=True)

    return partition_path


def create_curated_partition_path(
    run_timestamp: datetime,
    data_root: Path = DEFAULT_DATA_ROOT,
) -> Path:
    """Create the partitioned directory for curated quote records.

    Args:
        run_timestamp: UTC timestamp for the ingestion run.
        data_root: Root directory where pipeline data is stored.

    Returns:
        Path to the curated partition directory.
    """
    partition_path = (
        data_root
        / "curated"
        / "quotes"
        / f"year={run_timestamp:%Y}"
        / f"month={run_timestamp:%m}"
        / f"day={run_timestamp:%d}"
    )

    partition_path.mkdir(parents=True, exist_ok=True)

    return partition_path


def write_raw_quotes(
    records: Iterable[dict[str, Any]],
    run_timestamp: datetime | None = None,
    data_root: Path = DEFAULT_DATA_ROOT,
) -> Path:
    """Write raw API responses to a partitioned JSONL file.

    Args:
        records: Original records returned by the API.
        run_timestamp: UTC timestamp used for partitioning and file naming.
        data_root: Root directory where pipeline data is stored.

    Returns:
        Path to the raw JSONL file.
    """
    timestamp = run_timestamp or datetime.now(UTC)
    partition_path = create_raw_partition_path(
        timestamp,
        data_root,
    )

    file_path = (
        partition_path
        / f"quotes_{timestamp:%Y%m%dT%H%M%SZ}.jsonl"
    )

    with file_path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False))
            file.write("\n")

    return file_path


def write_curated_quotes(
    quotes: Iterable[StockQuote],
    run_timestamp: datetime | None = None,
    data_root: Path = DEFAULT_DATA_ROOT,
) -> Path:
    """Write standardized quotes to a partitioned JSONL file.

    Args:
        quotes: Validated and standardized stock quotes.
        run_timestamp: UTC timestamp used for partitioning and file naming.
        data_root: Root directory where pipeline data is stored.

    Returns:
        Path to the curated JSONL file.
    """
    timestamp = run_timestamp or datetime.now(UTC)
    partition_path = create_curated_partition_path(
        timestamp,
        data_root,
    )

    file_path = (
        partition_path
        / f"quotes_{timestamp:%Y%m%dT%H%M%SZ}.jsonl"
    )

    with file_path.open("w", encoding="utf-8") as file:
        for quote in quotes:
            file.write(
                json.dumps(
                    quote.to_dict(),
                    ensure_ascii=False,
                )
            )
            file.write("\n")

    return file_path