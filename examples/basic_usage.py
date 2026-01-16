from datetime import date, datetime

from pydantic import ValidationError

from pydantic_market_data.models import OHLCV, History, SecurityCriteria, Symbol


def main():
    print("--- Symbol Creation ---")
    try:
        # Valid Symbol
        s = Symbol(
            ticker="AAPL",
            name="Apple Inc.",
            exchange="NASDAQ",
            country="US",  # Must be ISO 3166-1 alpha-2
            currency="USD",  # Must be ISO 4217
        )
        print(f"Created Symbol: {s}")
    except ValidationError as e:
        print(f"Validation Error: {e}")

    print("\n--- Strict Validation Example ---")
    try:
        # Invalid Country
        Symbol(
            ticker="INVALID",
            name="Invalid Country",
            country="United States",  # Will fail, requires "US"
            currency="USD",
        )
    except ValidationError as e:
        print(f"Caught expected validation error for country: {e.errors()[0]['msg']}")

    print("\n--- Security Criteria ---")
    try:
        # Valid ISIN & Date
        c = SecurityCriteria(
            isin="US0378331005", target_date=date(2023, 11, 15), preferred_exchanges=["NASDAQ"]
        )
        print(f"Criteria: ISIN={c.isin}, Date={c.target_date}")
    except ValidationError as e:
        print(e)

    print("\n--- History & Pandas ---")
    # Creating history manually
    candles = [
        OHLCV(date=datetime(2023, 11, 15), close=150.0, volume=1000),
        OHLCV(date=datetime(2023, 11, 16), close=152.0, volume=1200),
    ]
    h = History(symbol=s, candles=candles)

    # Convert to DataFrame
    df = h.to_pandas()
    print("Pandas DataFrame:")
    print(df)


if __name__ == "__main__":
    main()
