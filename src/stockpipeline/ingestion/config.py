"""Application configuration for the stock-market ingestion pipeline."""

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import boto3
from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Configuration values required by the ingestion application."""

    twelve_data_api_key: str
    twelve_data_api_url: str = "https://api.twelvedata.com/quote"
    s3_bucket_name: str | None = None


@lru_cache(maxsize=1)
def _get_secret_value(secret_arn: str) -> str:
    """Retrieve the Twelve Data API key from Secrets Manager.

    Args:
        secret_arn: ARN or name of the Secrets Manager secret.

    Returns:
        Plaintext API key stored in the secret.

    Raises:
        ValueError: If the secret does not contain a usable string.
    """
    secrets_client = boto3.client("secretsmanager")

    response: dict[str, Any] = secrets_client.get_secret_value(
        SecretId=secret_arn,
    )

    secret_value = response.get("SecretString")

    if not secret_value or not secret_value.strip():
        raise ValueError(
            "The Twelve Data secret does not contain a usable SecretString."
        )

    return secret_value.strip()


def get_settings() -> Settings:
    """Load and validate application settings.

    Local execution uses TWELVE_DATA_API_KEY from the .env file.
    Lambda retrieves the key from Secrets Manager when
    TWELVE_DATA_SECRET_ARN is configured.

    Returns:
        Validated application configuration.

    Raises:
        ValueError: If the API key cannot be located.
    """
    api_key = os.getenv("TWELVE_DATA_API_KEY")

    if not api_key:
        secret_arn = os.getenv("TWELVE_DATA_SECRET_ARN")

        if secret_arn:
            api_key = _get_secret_value(secret_arn)

    if not api_key:
        raise ValueError(
            "The Twelve Data API key is missing. Configure "
            "TWELVE_DATA_API_KEY locally or TWELVE_DATA_SECRET_ARN "
            "in AWS Lambda."
        )

    return Settings(
        twelve_data_api_key=api_key,
        s3_bucket_name=os.getenv("STOCK_DATA_BUCKET"),
    )