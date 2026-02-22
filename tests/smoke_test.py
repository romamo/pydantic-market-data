from datetime import date

from pydantic_market_data import (
    DataSource,
    HistoryInterval,
    HistoryPeriod,
    SecurityCriteria,
    Symbol,
)


def test_imports():
    assert issubclass(Symbol, object)
    assert issubclass(SecurityCriteria, object)
    assert issubclass(HistoryPeriod, object)
    assert issubclass(HistoryInterval, object)
    # DataSource is a Protocol, not a class to subclass
    assert DataSource is not None
    print("Smoke test passed: pydantic-market-data imported successfully.")


def test_symbol_instantiation():
    s = Symbol(ticker="AAPL", name="Apple Inc")
    assert str(s.ticker) == "AAPL"
    assert s.name == "Apple Inc"
    assert s.exchange is None
    assert s.currency is None


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
    test_symbol_instantiation()
    test_security_criteria_date_coercion()
    test_history_period_enum()
    test_history_interval_enum()
