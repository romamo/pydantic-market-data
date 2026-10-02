import copy
import pickle  # nosec B403
import warnings
from datetime import date, datetime

import pytest
from pydantic import ValidationError
from pydantic_extra_types.currency_code import Currency

from pydantic_market_data import (
    OHLCV,
    CurrencyCode,
    History,
    MajorCurrency,
    PriceOnDate,
    QuoteCurrency,
    Security,
    SecurityQuery,
    Symbol,
)
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


# --- Issue #18: FlexibleDate accepts only YYYY-MM-DD, YYYY/MM/DD and YYYYMMDD ----------------

ACCEPTED_DATES = ["2025-01-15", "2025/01/15", "20250115", date(2025, 1, 15)]
REJECTED_DATES = [
    "01/02/2025",  # ambiguous day/month: was read month-first as 2025-01-02
    "15/01/2025",
    "15.01.2025",
    "Jan 15 2025",
    "2024-01-15T10:00:00",
    "2025-01/15",  # mixed separators
    "2025.01.15",
    " 2025-01-15",
    "2025-1-15",
    "250115",
]
_FORMATS_MESSAGE = "expected YYYY-MM-DD, YYYY/MM/DD or YYYYMMDD"


@pytest.mark.parametrize("raw", ACCEPTED_DATES)
def test_price_on_date_accepts_documented_shapes(raw):
    assert PriceOnDate(price=1.0, date=raw).date == date(2025, 1, 15)


@pytest.mark.parametrize("raw", ACCEPTED_DATES)
def test_security_query_price_on_accepts_documented_shapes(raw):
    sq = SecurityQuery(price_on={"price": 1.0, "date": raw})
    assert sq.price_on is not None
    assert sq.price_on[0].date == date(2025, 1, 15)


@pytest.mark.parametrize("raw", REJECTED_DATES)
def test_price_on_date_rejects_other_shapes(raw):
    with pytest.raises(ValidationError, match=_FORMATS_MESSAGE):
        PriceOnDate(price=1.0, date=raw)


@pytest.mark.parametrize("raw", REJECTED_DATES)
def test_security_query_price_on_rejects_other_shapes(raw):
    with pytest.raises(ValidationError, match=_FORMATS_MESSAGE):
        SecurityQuery(price_on={"price": 1.0, "date": raw})


@pytest.mark.parametrize("raw", ["2024-02-30", "2024/02/30", "20240230", "2025-13-01"])
def test_price_on_date_rejects_impossible_dates(raw):
    with pytest.raises(ValidationError):
        PriceOnDate(price=1.0, date=raw)


def test_price_on_date_accepts_leap_day():
    assert PriceOnDate(price=1.0, date="2024-02-29").date == date(2024, 2, 29)


def test_price_on_date_rejection_emits_no_warning():
    # pd.to_datetime warned "Parsing dates in %d/%m/%Y format" on stderr for 15/01/2025
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with pytest.raises(ValidationError):
            PriceOnDate(price=1.0, date="15/01/2025")


def test_price_on_date_datetime_object_behaviour_unchanged():
    assert PriceOnDate(price=1.0, date=datetime(2025, 1, 15)).date == date(2025, 1, 15)
    with pytest.raises(ValidationError):
        PriceOnDate(price=1.0, date=datetime(2025, 1, 15, 10, 0))


# --- Issue #25: minor-unit quote currencies ---------------------------------------------

_MINOR_CASES = [
    # (input, canonical code, major code, factor)
    ("GBX", "GBX", "GBP", 100),
    ("gbx", "GBX", "GBP", 100),
    ("GBp", "GBX", "GBP", 100),
    ("ZAC", "ZAC", "ZAR", 100),
    ("zac", "ZAC", "ZAR", 100),
    ("ZAc", "ZAC", "ZAR", 100),
    ("ILA", "ILA", "ILS", 100),
    ("ila", "ILA", "ILS", 100),
    # Only the exact mixed-case GBp/ZAc mean the minor unit; other cases keep the ISO meaning
    ("GBP", "GBP", "GBP", 1),
    ("gbp", "GBP", "GBP", 1),
    ("Gbp", "GBP", "GBP", 1),
    ("gBp", "GBP", "GBP", 1),
    ("zar", "ZAR", "ZAR", 1),
    ("usd", "USD", "USD", 1),
]


@pytest.mark.parametrize(("raw", "code", "major", "factor"), _MINOR_CASES)
def test_security_currency_minor_units(raw, code, major, factor):
    currency = Security(symbol="VOD:LSE", name="v", currency=raw).currency
    assert currency is not None
    assert currency == CurrencyCode(code)
    assert str(currency) == code
    assert currency.value == code
    assert currency.to_major() == MajorCurrency(currency=major, factor=factor)
    assert str(currency.to_major().currency) == major
    assert currency.to_major().factor == factor


@pytest.mark.parametrize(("raw", "code"), [(c[0], c[1]) for c in _MINOR_CASES])
def test_security_query_currency_minor_units_on_assignment(raw, code):
    q = SecurityQuery(currency=raw)
    assert str(q.currency) == code
    q.currency = "USD"
    assert str(q.currency) == "USD"
    q.currency = raw
    assert str(q.currency) == code


@pytest.mark.parametrize("raw", ["XXXX", "ABC", "ZAX", "GB", "GBp ", "XAU", 840])
def test_currency_rejects_unknown_codes(raw):
    with pytest.raises(ValidationError):
        Security(symbol="V", name="v", currency=raw)
    q = SecurityQuery()
    with pytest.raises(ValidationError):
        q.currency = raw


def test_currency_code_json_schema_adds_only_minor_unit_codes():
    enum = Security.model_json_schema()["$defs"]["CurrencyCode"]["enum"]
    assert set(enum) - set(Currency.allowed_countries_list) == {"GBX", "ILA", "ZAC"}
    assert set(Currency.allowed_countries_list) <= set(enum)
    assert enum == sorted(enum)


def test_currency_code_value_is_a_str_quote_currency():
    code = CurrencyCode("GBp")
    assert isinstance(code.value, QuoteCurrency)
    assert isinstance(code.value, str)
    assert code.value == "GBX"
    assert code.model_dump() == "GBX"
    assert CurrencyCode.model_validate_json('"GBp"') == code
    assert MajorCurrency(currency="gbp", factor=100).currency == CurrencyCode("GBP")


@pytest.mark.parametrize("raw", ["GBX", "GBp", "ILA"])
def test_major_currency_rejects_minor_unit_codes(raw):
    with pytest.raises(ValidationError, match="minor-unit code"):
        MajorCurrency(currency=raw, factor=1)


@pytest.mark.parametrize(
    ("raw", "code"),
    [("gbp", "GBP"), ("GBp", "GBX"), ("gbx", "GBX"), ("ZAc", "ZAC"), ("ila", "ILA")],
)
def test_quote_currency_direct_construction_validates(raw, code):
    value = QuoteCurrency(raw)
    assert value == code
    assert type(value) is QuoteCurrency
    assert QuoteCurrency(value) == code
    assert CurrencyCode(value).value == code


@pytest.mark.parametrize("raw", ["junk", "ZAX", "XAU", "", "GBp "])
def test_quote_currency_direct_construction_rejects_unknown(raw):
    with pytest.raises(ValueError, match="Invalid currency code"):
        QuoteCurrency(raw)


def test_quote_currency_direct_construction_rejects_non_str():
    with pytest.raises(TypeError):
        QuoteCurrency(840)  # type: ignore[arg-type]


def test_quote_currency_pydantic_error_type():
    with pytest.raises(ValidationError) as exc:
        CurrencyCode("ZAX")
    assert exc.value.errors()[0]["type"] == "InvalidCurrency"


def test_quote_currency_survives_copy_and_pickle():
    s = Security(symbol="VOD:LSE", name="v", currency="GBp")
    assert copy.deepcopy(s) == s
    assert s.model_copy(deep=True).currency == CurrencyCode("GBX")
    assert pickle.loads(pickle.dumps(QuoteCurrency("GBp"))) == "GBX"  # nosec B301


def test_currency_error_names_the_code():
    with pytest.raises(ValidationError, match="Invalid currency code 'ZAX'"):
        CurrencyCode("ZAX")
