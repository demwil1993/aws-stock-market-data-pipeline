"""Application configuration for the stock market ingestion pipeline."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Configuration values required by the ingestion application."""

    twelve_data_api_key: str
    twelve_data_api_url: str = "https://api.twelvedata.com/quote"


def get_settings() -> Settings:
    """Load and validate application settings.

    Returns:
        Settings: Validated application configuration.

    Raises:
        ValueError: If a required environment variable is missing.
    """
    api_key = os.getenv("TWELVE_DATA_API_KEY")

    if not api_key:
        raise ValueError(
            "TWELVE_DATA_API_KEY is missing. "
            "Add it to the .env file in the project root."
        )

    return Settings(twelve_data_api_key=api_key)