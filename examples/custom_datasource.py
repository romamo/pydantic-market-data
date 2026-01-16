from datetime import timedelta
from typing import Optional

from pydantic_market_data import OHLCV, DataSource, History, SecurityCriteria, Symbol


class MockDataSource(DataSource):
    """
    Example implementation of the DataSource protocol.
    """

    def resolve(self, criteria: SecurityCriteria) -> Optional[Symbol]:
        print(f"Resolving with criteria: {criteria}")

        # Simulate lookup logic
        if criteria.symbol == "AAPL" or criteria.isin == "US0378331005":
            return Symbol(
                ticker="AAPL", name="Apple Inc.", exchange="NASDAQ", country="US", currency="USD"
            )
        return None

    def history(self, ticker: str, period: str = "1mo") -> History:
        print(f"Fetching history for {ticker}, period={period}")

        # Return dummy data
        from datetime import datetime

        return History(
            symbol=Symbol(ticker=ticker, name="Mock Ticker", country="US", currency="USD"),
            candles=[
                OHLCV(date=datetime.now() - timedelta(days=1), close=100.0, volume=500),
                OHLCV(date=datetime.now(), close=101.5, volume=600),
            ],
        )

    def search(self, query: str) -> list[Symbol]:
        # Minimal implementation
        return []


def main():
    source = MockDataSource()

    # 1. Resolve
    criteria = SecurityCriteria(symbol="AAPL")
    symbol = source.resolve(criteria)

    if symbol:
        print(f"Resolved: {symbol.ticker} ({symbol.name})")

        # 2. History
        hist = source.history(symbol.ticker)
        print(f"Got {len(hist.candles)} candles.")
    else:
        print("Not found.")


if __name__ == "__main__":
    main()
