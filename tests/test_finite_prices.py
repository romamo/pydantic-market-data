"""Issue #33: prices and candle values must be finite (no NaN, no infinity)."""

from datetime import datetime

import numpy as np
import pytest
from pydantic import BaseModel, ValidationError
from pydantic_settings import BaseSettings

from pydantic_market_data import (
    OHLCV,
    HistoryArgs,
    PatchedCliSettingsSource,
    Price,
    PriceOnDate,
    PriceVerificationError,
    SearchArgs,
    SecurityQueryArgs,
)
from pydantic_market_data.cli_models import HistoryQueryArgs

NON_FINITE = [
    float("nan"),
    float("inf"),
    float("-inf"),
    np.float64("nan"),
    np.float64("inf"),
    "nan",
    "NaN",
    "inf",
    "-inf",
    "Infinity",
    "-Infinity",
]
FINITE = [0, 0.0, -0.0, -1.5, 42, 123.45, 1e308, -1e308, "12.5", np.float64(3.25)]
OHLCV_FIELDS = ["open", "high", "low", "close", "volume"]
CLI_MODELS: list[type[BaseModel]] = [SearchArgs, SecurityQueryArgs, HistoryArgs, HistoryQueryArgs]
DAY = datetime(2026, 10, 2)


@pytest.mark.parametrize("raw", NON_FINITE)
def test_price_rejects_non_finite(raw):
    with pytest.raises(ValidationError, match="finite number"):
        Price(raw)
    with pytest.raises(ValidationError, match="finite number"):
        Price(root=raw)
    with pytest.raises(ValidationError, match="finite number"):
        Price.model_validate(raw)


@pytest.mark.parametrize("raw", ["NaN", "Infinity", "-Infinity"])
def test_price_rejects_non_finite_json(raw):
    with pytest.raises(ValidationError, match="finite number"):
        Price.model_validate_json(raw)


@pytest.mark.parametrize("raw", FINITE)
def test_price_accepts_finite(raw):
    assert Price(raw).value == float(raw)
    assert type(Price(raw).value) is float


def test_price_int_coerces():
    assert Price(5).model_dump_json() == "5.0"


@pytest.mark.parametrize("raw", NON_FINITE)
def test_price_input_field_rejects_non_finite(raw):
    with pytest.raises(ValidationError, match="finite number"):
        PriceOnDate(price=raw, date="2026-10-02")


def test_price_input_field_accepts_finite():
    assert PriceOnDate(price=1e308, date="2026-10-02").price == Price(1e308)
    assert PriceOnDate(price=Price(0), date="2026-10-02").price.value == 0.0


@pytest.mark.parametrize("arg", ["expected_price", "actual_low", "actual_high", "actual_close"])
def test_price_verification_error_rejects_non_finite(arg):
    kwargs: dict = {"expected_price": 1.0, arg: float("nan")}
    with pytest.raises(ValidationError, match="finite number"):
        PriceVerificationError("m", symbol="AAPL", actual_date="2026-10-02", **kwargs)


@pytest.mark.parametrize("field", OHLCV_FIELDS)
@pytest.mark.parametrize("raw", NON_FINITE)
def test_ohlcv_rejects_non_finite(field, raw):
    with pytest.raises(ValidationError, match="finite number"):
        OHLCV(date=DAY, **{field: raw})


@pytest.mark.parametrize("field", OHLCV_FIELDS)
@pytest.mark.parametrize("raw", [float("nan"), np.float64("inf"), "-inf"])
def test_ohlcv_rejects_non_finite_on_assignment(field, raw):
    candle = OHLCV(date=DAY, **{field: 1.0})
    with pytest.raises(ValidationError, match="finite number"):
        setattr(candle, field, raw)
    assert getattr(candle, field) == 1.0


@pytest.mark.parametrize("field", OHLCV_FIELDS)
@pytest.mark.parametrize("raw", FINITE)
def test_ohlcv_accepts_finite_and_none(field, raw):
    candle = OHLCV(date=DAY, **{field: raw})
    assert getattr(candle, field) == float(raw)
    setattr(candle, field, None)
    assert getattr(candle, field) is None


@pytest.mark.parametrize("model", CLI_MODELS)
@pytest.mark.parametrize("raw", ["nan", "inf", "-Infinity", float("nan")])
def test_cli_price_rejects_non_finite(model, raw):
    with pytest.raises(ValidationError, match="finite number"):
        model(price=raw)


@pytest.mark.parametrize("model", CLI_MODELS)
def test_cli_price_accepts_finite(model):
    assert model(price="1e308").price == 1e308
    assert model(price=0).price == 0.0


@pytest.mark.parametrize("model", [SearchArgs, SecurityQueryArgs])
@pytest.mark.parametrize("raw", ["nan", "inf", "-inf"])
def test_cli_parse_price_rejects_non_finite(model, raw):
    class Cli(model, BaseSettings):  # type: ignore[misc, valid-type]
        pass

    source = PatchedCliSettingsSource(Cli, cli_parse_args=[f"--price={raw}"])
    with pytest.raises(ValidationError, match="finite number"):
        Cli.model_validate(source())


@pytest.mark.parametrize("model", [SearchArgs, SecurityQueryArgs])
def test_cli_parse_price_accepts_finite(model):
    class Cli(model, BaseSettings):  # type: ignore[misc, valid-type]
        pass

    source = PatchedCliSettingsSource(Cli, cli_parse_args=["--price=-2.5"])
    assert Cli.model_validate(source()).price == -2.5
