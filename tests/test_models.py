from datetime import date, datetime

import pytest
from pydantic import ValidationError

from pydantic_market_data import OHLCV, History, SecurityCriteria, Symbol, Ticker
from pydantic_market_data.models import clean_isin, validate_isin


def test_symbol_valid():
    s = Symbol(ticker="AAPL", name="Apple", country="US", currency="USD")
    assert s.country == "US"
    assert s.currency == "USD"

    # Test country name lookup
    s2 = Symbol(ticker="AAPL", name="Apple", country="United States", currency="USD")
    assert s2.country == "US"

    s3 = Symbol(ticker="TSLA", name="Tesla", country="UNITED KINGDOM", currency="GBP")
    assert s3.country == "GB"


def test_symbol_invalid_country():
    # "United States" is valid according to some extra-types logic if lenient?
    # But usually CountryAlpha2 expects 2 chars.
    # Let's test what rejects. "XX" is unlikely to be valid if it checks list.
    with pytest.raises(ValidationError):
        Symbol(ticker="AAPL", name="Apple", country="ZZ", currency="USD")


def test_symbol_invalid_currency():
    with pytest.raises(ValidationError):
        Symbol(ticker="AAPL", name="Apple", country="US", currency="LOL")


def test_security_criteria_isin_valid():
    c = SecurityCriteria(isin="US0378331005")
    assert c.isin == "US0378331005"


def test_security_criteria_isin_invalid():
    # Length
    with pytest.raises(ValidationError):
        SecurityCriteria(isin="US037833100")  # Too short

    # Pattern
    with pytest.raises(ValidationError):
        SecurityCriteria(isin="U$0378331005")  # Bad char

    # Checksum failure (valid pattern but bad digit)
    with pytest.raises(ValidationError):
        SecurityCriteria(isin="US0378331006")


def test_history_to_pandas():
    candles = [
        OHLCV(date=datetime(2023, 1, 1), close=100.0, volume=1000),
        OHLCV(date=datetime(2023, 1, 2), close=102.0, volume=1200),
    ]
    h = History(
        symbol=Symbol(ticker="TEST", name="Test", country="US", currency="USD"), candles=candles
    )
    df = h.to_pandas()
    assert not df.empty
    assert len(df) == 2
    assert "Close" in df.columns
    assert "Volume" in df.columns
    assert df.index.name == "Date"
    assert df.iloc[0]["Close"] == 100.0


def test_flexible_date_parsing():
    # ISO Format
    c1 = SecurityCriteria(target_date="2023-01-01")
    assert c1.target_date == date(2023, 1, 1)

    # Compressed Format
    c2 = SecurityCriteria(target_date="20230101")
    assert c2.target_date == date(2023, 1, 1)

    # Slash Format
    c3 = SecurityCriteria(target_date="2023/01/01")
    assert c3.target_date == date(2023, 1, 1)

    # Original Date object
    c4 = SecurityCriteria(target_date=date(2023, 1, 1))
    assert c4.target_date == date(2023, 1, 1)


def test_flexible_datetime_parsing():
    # ISO string
    o1 = OHLCV(date="2023-01-01 12:00:00", close=100)
    assert o1.date == datetime(2023, 1, 1, 12, 0, 0)

    # Date only string (defaults to 00:00:00)
    o2 = OHLCV(date="2023-01-01", close=100)
    assert o2.date == datetime(2023, 1, 1, 0, 0, 0)

    # Pandas timestamp support (via string parsing or direct if pd passed)
    # We test string primarily as that's the "auto convert" goal
    o3 = OHLCV(date="2023/01/01 10:30", close=100)
    assert o3.date == datetime(2023, 1, 1, 10, 30)


def test_validate_country_unknown_name():
    """T1: validate_country should raise for unknown country names (fail-fast)."""
    with pytest.raises(ValidationError, match="Unknown country name"):
        Symbol(ticker="AAPL", name="Apple", country="Narnia", currency="USD")


def test_clean_isin_edge_cases():
    """T2: clean_isin should return None for None, '-', 'NONE', and empty strings."""

    assert clean_isin(None) is None
    assert clean_isin("-") is None
    assert clean_isin("NONE") is None
    assert clean_isin("  ") is None

    assert validate_isin(None) is None

    c1 = SecurityCriteria(isin=None)
    assert c1.isin is None


def test_history_to_pandas_empty():
    """T3: to_pandas() on an empty History should return an empty DataFrame."""
    h = History(
        symbol=Symbol(ticker="TEST", name="Test", country="US", currency="USD"),
        candles=[],
    )
    df = h.to_pandas()
    assert df.empty


def test_ticker_str():
    """T4: Ticker.__str__ should return the underlying string (RootModel)."""
    t = Ticker("AAPL")
    assert str(t) == "AAPL"
