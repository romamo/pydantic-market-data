"""Regression tests for #2: History.candles must be in strictly ascending date order."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from pydantic_market_data import OHLCV, History, Security

SEC = Security(symbol="TEST", name="Test", country="US", currency="USD")


def _history(*dates: datetime | str) -> History:
    return History(
        security=SEC, candles=[OHLCV(date=d, close=float(i)) for i, d in enumerate(dates)]
    )


def test_candles_schema_declares_order():
    prop = History.model_json_schema()["properties"]["candles"]
    assert prop["x-ordered"] is True
    assert prop["description"] == "Candles in ascending date order"
    assert prop["type"] == "array"


def test_candles_ascending_accepted_and_last_is_latest():
    h = _history("2023-01-01", "2023-01-02", "2023-01-03")
    assert h.candles[-1].date == datetime(2023, 1, 3)


def test_candles_empty_and_single_valid():
    assert _history().candles == []
    assert len(_history("2023-01-01").candles) == 1


def test_candles_descending_rejected_naming_index_and_dates():
    with pytest.raises(ValidationError) as exc:
        _history("2023-01-01", "2023-01-03", "2023-01-02")
    msg = str(exc.value)
    assert "candle 2 date 2023-01-02T00:00:00" in msg
    assert "candle 1 date 2023-01-03T00:00:00" in msg


def test_candles_duplicate_date_rejected():
    with pytest.raises(ValidationError, match="strictly ascending"):
        _history("2023-01-01", "2023-01-01")


def test_candles_mixed_timezone_awareness_rejected():
    with pytest.raises(ValidationError, match="mix timezone-aware and naive"):
        _history(datetime(2023, 1, 1), datetime(2023, 1, 2, tzinfo=timezone.utc))


def test_candles_aware_compared_across_offsets():
    h = _history("2023-01-01T10:00:00+02:00", "2023-01-01T09:00:00+00:00")
    assert len(h.candles) == 2
    with pytest.raises(ValidationError, match="strictly ascending"):
        _history("2023-01-01T09:00:00+00:00", "2023-01-01T10:00:00+02:00")


def test_model_validate_rejects_reversed_dump():
    h = _history("2023-01-01", "2023-01-02")
    payload = h.model_dump()
    payload["candles"].reverse()
    with pytest.raises(ValidationError, match="strictly ascending"):
        History.model_validate(payload)
