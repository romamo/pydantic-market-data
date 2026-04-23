from datetime import date

from pydantic_market_data import (
    DataSource,
    HistoryInterval,
    HistoryPeriod,
    PriceOnDate,
    Security,
    SecurityQuery,
)


def test_imports():
    assert issubclass(Security, object)
    assert issubclass(SecurityQuery, object)
    assert issubclass(PriceOnDate, object)
    assert issubclass(HistoryPeriod, object)
    assert issubclass(HistoryInterval, object)
    # DataSource is a Protocol, not a class to subclass
    assert DataSource is not None
    print("Smoke test passed: pydantic-market-data imported successfully.")


def test_security_instantiation():
    s = Security(symbol="AAPL", name="Apple Inc", asset_class="Equity", isin="US0378331005")
    assert str(s.symbol) == "AAPL"
    assert s.name == "Apple Inc"
    assert s.asset_class == "Equity"
    assert str(s.isin) == "US0378331005"
    assert s.exchange is None
    assert s.currency is None


def test_security_query_asset_class():
    sq = SecurityQuery(asset_class="Fixed Income")
    assert sq.asset_class == "Fixed Income"


def test_price_on_date_coercion():
    p = PriceOnDate(price=100.0, date="2024-01-15")
    assert p.date == date(2024, 1, 15)


def test_history_period_enum():
    assert HistoryPeriod.Y1.value == "1y"
    assert HistoryPeriod.MAX.value == "max"


def test_history_interval_enum():
    assert HistoryInterval.D1.value == "1d"
    assert HistoryInterval.MO1.value == "1mo"


if __name__ == "__main__":
    test_imports()
    test_security_instantiation()
    test_security_query_asset_class()
    test_price_on_date_coercion()
    test_history_period_enum()
    test_history_interval_enum()
