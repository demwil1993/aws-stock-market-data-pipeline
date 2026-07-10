"""Local entry point for the stock-market ingestion pipeline."""

from pprint import pprint

from stockpipeline.ingestion.api_client import TwelveDataClient
from stockpipeline.ingestion.config import get_settings
from stockpipeline.ingestion.exceptions import StockPipelineError
from stockpipeline.ingestion.models import StockQuote


def main() -> None:
    """Retrieve, standardize, and display a stock quote."""
    try:
        settings = get_settings()
        client = TwelveDataClient(settings)

        raw_quote = client.get_quote("AAPL")
        stock_quote = StockQuote.from_api_response(raw_quote)

        print("Quote retrieved and standardized successfully.")
        pprint(stock_quote.to_dict())

    except (StockPipelineError, ValueError) as exc:
        print(f"Pipeline error: {exc}")


if __name__ == "__main__":
    main()