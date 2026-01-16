from pydantic_market_data import (
    DataSource,
    HistoryInterval,
    HistoryPeriod,
    SecurityCriteria,
    Symbol,
)


def test_imports():
    assert Symbol
    assert SecurityCriteria
    assert DataSource
    assert HistoryPeriod
    assert HistoryInterval
    print("Smoke test passed: pydantic-market-data imported successfully.")


if __name__ == "__main__":
    test_imports()
