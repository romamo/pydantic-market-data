from datetime import date, datetime, timedelta

from pydantic_market_data import (
    OHLCV,
    DataSource,
    History,
    HistoryPeriod,
    Price,
    Security,
    SecurityCriteria,
    Symbol,
)


class MockDataSource(DataSource):
    """
    Example implementation of the DataSource protocol.
    """

    def resolve(self, criteria: SecurityCriteria) -> Security | None:
        print(f"Resolving with criteria: {criteria}")

        # Simulate lookup logic
        if criteria.symbol == "AAPL" or criteria.isin == "US0378331005":
            return Security(
                symbol="AAPL",
                name="Apple Inc.",
                exchange="NASDAQ",
                country="US",
                currency="USD",
            )
        return None

    def history(self, symbol: Symbol.Input, period: HistoryPeriod = HistoryPeriod.MO1) -> History:
        print(f"Fetching history for {symbol}, period={period}")

        return History(
            security=Security(
                symbol=symbol,
                name="Mock Security",
                country="US",
                currency="USD",
            ),
            candles=[
                OHLCV(date=datetime.now() - timedelta(days=1), close=100.0, volume=500),
                OHLCV(date=datetime.now(), close=101.5, volume=600),
            ],
        )

    def search(self, query: str) -> list[Security]:
        # Minimal implementation
        return []

    def validate(self, symbol: Symbol.Input, target_date: date, target_price: Price.Input) -> bool:
        # Minimal implementation: always returns True
        print(f"Validating {symbol} on {target_date} at {target_price}")
        return True


def main():
    source = MockDataSource()

    # 1. Resolve
    criteria = SecurityCriteria(symbol="AAPL")
    security = source.resolve(criteria)

    if security:
        print(f"Resolved: {security.symbol} ({security.name})")

        # 2. History
        hist = source.history(security.symbol)
        print(f"Got {len(hist.candles)} candles.")
    else:
        print("Not found.")


if __name__ == "__main__":
    main()
