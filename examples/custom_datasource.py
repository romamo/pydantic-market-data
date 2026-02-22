from datetime import date, datetime, timedelta

from pydantic_market_data import (
    OHLCV,
    DataSource,
    History,
    HistoryPeriod,
    PriceInput,
    SecurityCriteria,
    Symbol,
    TickerInput,
)


class MockDataSource(DataSource):
    """
    Example implementation of the DataSource protocol.
    """

    def resolve(self, criteria: SecurityCriteria) -> Symbol | None:
        print(f"Resolving with criteria: {criteria}")

        # Simulate lookup logic
        if criteria.symbol == "AAPL" or criteria.isin == "US0378331005":
            return Symbol(
                ticker="AAPL",
                name="Apple Inc.",
                exchange="NASDAQ",
                country="US",
                currency="USD",
            )
        return None

    def history(self, ticker: TickerInput, period: HistoryPeriod = HistoryPeriod.MO1) -> History:
        print(f"Fetching history for {ticker}, period={period}")

        return History(
            symbol=Symbol(
                ticker=ticker,
                name="Mock Ticker",
                country="US",
                currency="USD",
            ),
            candles=[
                OHLCV(date=datetime.now() - timedelta(days=1), close=100.0, volume=500),
                OHLCV(date=datetime.now(), close=101.5, volume=600),
            ],
        )

    def search(self, query: str) -> list[Symbol]:
        # Minimal implementation
        return []

    def validate(self, ticker: TickerInput, target_date: date, target_price: PriceInput) -> bool:
        # Minimal implementation: always returns True
        print(f"Validating {ticker} on {target_date} at {target_price}")
        return True


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
