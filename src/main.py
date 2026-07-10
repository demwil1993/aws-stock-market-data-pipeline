"""Local entry point for the stock-market ingestion pipeline."""

from pprint import pprint

from stockpipeline.ingestion.api_client import TwelveDataClient
from stockpipeline.ingestion.config import get_settings
from stockpipeline.ingestion.exceptions import StockPipelineError
from stockpipeline.ingestion.models import StockQuote
from stockpipeline.ingestion.watchlist import WATCHLIST


def main() -> None:
    """Retrieve and standardize quotes for all monitored stocks."""
    settings = get_settings()
    client = TwelveDataClient(settings)

    successful_quotes: list[StockQuote] = []
    failed_symbols: list[str] = []

    for symbol in WATCHLIST:
        try:
            raw_quote = client.get_quote(symbol)
            stock_quote = StockQuote.from_api_response(raw_quote)

            successful_quotes.append(stock_quote)

            print(f"\nQuote retrieved successfully for {symbol}.")
            pprint(stock_quote.to_dict())

        except StockPipelineError as exc:
            failed_symbols.append(symbol)
            print(f"\nFailed to retrieve {symbol}: {exc}")

    print("\n" + "=" * 60)
    print("Ingestion summary")
    print("=" * 60)
    print(f"Symbols requested: {len(WATCHLIST)}")
    print(f"Quotes retrieved: {len(successful_quotes)}")
    print(f"Quotes failed: {len(failed_symbols)}")

    if failed_symbols:
        print(f"Failed symbols: {', '.join(failed_symbols)}")


if __name__ == "__main__":
    main()