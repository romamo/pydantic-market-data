from datetime import date

from pydantic_market_data import Price, PriceVerificationError, Ticker


def test_price_verification_error_primitives():
    err = PriceVerificationError(
        message="Price missing",
        ticker="AAPL",
        actual_date="2023-01-01",
        expected_price=150.0,
        actual_low=140.0,
        actual_high=160.0,
        actual_close=155.0,
        source="Yahoo",
    )

    # Assert fields are coerced to VOs
    assert isinstance(err.ticker, Ticker)
    assert err.ticker.value == "AAPL"
    assert err.actual_date == date(2023, 1, 1)
    assert isinstance(err.expected_price, Price)
    assert err.expected_price.value == 150.0

    # Check bounds
    assert isinstance(err.actual_low, Price)
    assert err.actual_low.value == 140.0
    assert isinstance(err.actual_high, Price)
    assert err.actual_high.value == 160.0
    assert isinstance(err.actual_close, Price)
    assert err.actual_close.value == 155.0
    assert err.source == "Yahoo"

    assert str(err) == "[AAPL] Yahoo: Price missing (Range: 140.00 - 160.00, Close: 155.00)"


def test_price_verification_error_vos():
    err = PriceVerificationError(
        message="Price is outside daily range",
        ticker=Ticker("MSFT"),
        actual_date=date(2023, 2, 1),
        expected_price=Price(250.0),
        actual_close=Price(240.0),
    )

    assert err.ticker.value == "MSFT"
    assert err.actual_date == date(2023, 2, 1)
    assert err.expected_price.value == 250.0
    assert err.actual_close.value == 240.0
    assert err.source is None

    assert str(err) == "[MSFT] Price is outside daily range (Close: 240.00)"


def test_price_verification_error_no_details():
    err = PriceVerificationError(
        message="No data found",
        ticker="TSLA",
        actual_date="2023-01-01",
        expected_price=100.0,
    )

    assert str(err) == "[TSLA] No data found"
