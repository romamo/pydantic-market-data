from datetime import date

from pydantic_market_data import (
    DataSource,
    HistoryInterval,
    HistoryPeriod,
    Security,
    SecurityCriteria,
)


def test_imports():
    assert issubclass(Security, object)
    assert issubclass(SecurityCriteria, object)
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


def test_security_criteria_asset_class():
    sc = SecurityCriteria(asset_class="Fixed Income")
    assert sc.asset_class == "Fixed Income"


def test_security_criteria_date_coercion():
    sc = SecurityCriteria(target_date="2024-01-15")
    assert sc.target_date == date(2024, 1, 15)


def test_history_period_enum():
    assert HistoryPeriod.Y1.value == "1y"
    assert HistoryPeriod.MAX.value == "max"


def test_history_interval_enum():
    assert HistoryInterval.D1.value == "1d"
    assert HistoryInterval.MO1.value == "1mo"


if __name__ == "__main__":
    test_imports()
    test_security_instantiation()
    test_security_criteria_asset_class()
    test_security_criteria_date_coercion()
    test_history_period_enum()
    test_history_interval_enum()
