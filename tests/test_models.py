from datetime import date, datetime

import pytest
from pydantic import ValidationError

from pydantic_market_data import OHLCV, History, PriceOnDate, Security, SecurityQuery, Symbol
from pydantic_market_data.models import clean_isin, validate_figi, validate_isin


def test_security_valid():
    s = Security(symbol="AAPL", name="Apple", country="US", currency="USD")
    assert str(s.country) == "US"
    assert str(s.currency) == "USD"

    # Test country name lookup
    s2 = Security(symbol="AAPL", name="Apple", country="United States", currency="USD")
    assert str(s2.country) == "US"

    s3 = Security(symbol="TSLA", name="Tesla", country="UNITED KINGDOM", currency="GBP")
    assert str(s3.country) == "GB"


def test_security_invalid_country():
    # "United States" is valid according to some extra-types logic if lenient?
    # But usually CountryAlpha2 expects 2 chars.
    # Let's test what rejects. "XX" is unlikely to be valid if it checks list.
    with pytest.raises(ValidationError):
        Security(symbol="AAPL", name="Apple", country="ZZ", currency="USD")


def test_security_invalid_currency():
    with pytest.raises(ValidationError):
        Security(symbol="AAPL", name="Apple", country="US", currency="LOL")


def test_security_query_isin_valid():
    c = SecurityQuery(isin="US0378331005")
    assert str(c.isin) == "US0378331005"


def test_security_query_isin_invalid():
    # Length
    with pytest.raises(ValidationError):
        SecurityQuery(isin="US037833100")  # Too short

    # Pattern
    with pytest.raises(ValidationError):
        SecurityQuery(isin="U$0378331005")  # Bad char

    # Checksum failure (valid pattern but bad digit)
    with pytest.raises(ValidationError):
        SecurityQuery(isin="US0378331006")


def test_history_to_pandas():
    candles = [
        OHLCV(date=datetime(2023, 1, 1), close=100.0, volume=1000),
        OHLCV(date=datetime(2023, 1, 2), close=102.0, volume=1200),
    ]
    h = History(
        security=Security(symbol="TEST", name="Test", country="US", currency="USD"), candles=candles
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
    p1 = PriceOnDate(price=100.0, date="2023-01-01")
    assert p1.date == date(2023, 1, 1)

    # Compressed Format
    p2 = PriceOnDate(price=100.0, date="20230101")
    assert p2.date == date(2023, 1, 1)

    # Slash Format
    p3 = PriceOnDate(price=100.0, date="2023/01/01")
    assert p3.date == date(2023, 1, 1)

    # Original Date object
    p4 = PriceOnDate(price=100.0, date=date(2023, 1, 1))
    assert p4.date == date(2023, 1, 1)


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
        Security(symbol="AAPL", name="Apple", country="Narnia", currency="USD")


def test_clean_isin_edge_cases():
    """T2: clean_isin should return None for None, '-', 'NONE', and empty strings."""

    assert clean_isin(None) is None
    assert clean_isin("-") is None
    assert clean_isin("NONE") is None
    assert clean_isin("  ") is None

    assert validate_isin(None) is None

    c1 = SecurityQuery(isin=None)
    assert c1.isin is None


def test_history_to_pandas_empty():
    """T3: to_pandas() on an empty History should return an empty DataFrame."""
    h = History(
        security=Security(symbol="TEST", name="Test", country="US", currency="USD"),
        candles=[],
    )
    df = h.to_pandas()
    assert df.empty


def test_symbol_str():
    """T4: Symbol.__str__ should return the underlying string (RootModel)."""
    s = Symbol("AAPL")
    assert str(s) == "AAPL"


# BBG000B9XRY4 is Apple Inc's real FIGI
_VALID_FIGI = "BBG000B9XRY4"
# BBG00KHY5S69 is Broadcom Inc (AVGO) real FIGI
_VALID_FIGI_BROADCOM = "BBG00KHY5S69"


def test_figi_valid():
    assert validate_figi(_VALID_FIGI) == _VALID_FIGI


def test_figi_valid_broadcom():
    assert validate_figi(_VALID_FIGI_BROADCOM) == _VALID_FIGI_BROADCOM


def test_figi_none():
    assert validate_figi(None) is None


def test_figi_empty():
    assert validate_figi("") is None


def test_figi_wrong_length():
    with pytest.raises(ValueError, match="Invalid FIGI format"):
        validate_figi("BBG000B9XRY")  # 11 chars


def test_figi_bad_position_3():
    with pytest.raises(ValueError, match="Invalid FIGI format"):
        validate_figi("BBX000B9XRY4")  # position 3 must be G


def test_figi_reserved_prefix():
    with pytest.raises(ValueError, match="Invalid FIGI prefix"):
        validate_figi("BSG000B9XRY4")  # BS is a reserved prefix


def test_figi_bad_check_digit():
    with pytest.raises(ValueError, match="Invalid FIGI check digit"):
        validate_figi("BBG000B9XRY3")  # check digit should be 4, not 3


def test_security_figi_none():
    s = Security(symbol="AAPL", name="Apple", figi=None)
    assert s.figi is None


def test_security_figi_valid():
    s = Security(symbol="AAPL", name="Apple", figi=_VALID_FIGI)
    assert str(s.figi) == _VALID_FIGI


def test_security_figi_invalid():
    with pytest.raises(ValidationError):
        Security(symbol="AAPL", name="Apple", figi="NOTAFIGI")
