"""Logging configuration for the stock-market pipeline."""

import logging
import os


def configure_logging() -> None:
    """Configure application-wide logging."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    logging.basicConfig(
        level=log_level,
        format=(
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        ),
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        force=True,
    )