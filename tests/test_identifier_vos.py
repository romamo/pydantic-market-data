"""Issue #26: ISIN and FIGI validate their own root and are accepted by ``.Input`` fields."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from pydantic import ValidationError

import pydantic_market_data
from pydantic_market_data import Security, SecurityQuery, cli_models, models
from pydantic_market_data.models import FIGI, ISIN, clean_isin, validate_figi, validate_isin

_ISIN = "US0378331005"  # Apple
_FIGI = "BBG000B9XRY4"  # Apple

_BUILDERS: list[Callable[[Any], Any]] = [
    lambda v: ISIN(root=v),
    lambda v: ISIN(v),
    ISIN.model_validate,
]
_FIGI_BUILDERS: list[Callable[[Any], Any]] = [
    lambda v: FIGI(root=v),
    lambda v: FIGI(v),
    FIGI.model_validate,
]


# --- VO direct construction --------------------------------------------------------------


@pytest.mark.parametrize("build", _BUILDERS)
def test_isin_vo_valid_and_normalized(build: Callable[[Any], ISIN]) -> None:
    assert build(_ISIN).root == _ISIN
    assert build(" us0378331005 ").root == _ISIN


@pytest.mark.parametrize("build", _BUILDERS)
@pytest.mark.parametrize(
    ("value", "match"),
    [
        ("NOTANISIN123", "Invalid ISIN checksum"),
        ("US037833100", "Invalid ISIN format"),
        ("US0378331006", "Invalid ISIN checksum"),
        ("", "must not be empty"),
        ("  ", "must not be empty"),
        ("-", "must not be empty"),
        ("NONE", "must not be empty"),
        (None, "valid string"),
        (123, "valid string"),
    ],
)
def test_isin_vo_rejects_bad_root(build: Callable[[Any], ISIN], value: Any, match: str) -> None:
    with pytest.raises(ValidationError, match=match):
        build(value)


@pytest.mark.parametrize("build", _FIGI_BUILDERS)
def test_figi_vo_valid_and_normalized(build: Callable[[Any], FIGI]) -> None:
    assert build(_FIGI).root == _FIGI
    assert build(" bbg000b9xry4 ").root == _FIGI


@pytest.mark.parametrize("build", _FIGI_BUILDERS)
@pytest.mark.parametrize(
    ("value", "match"),
    [
        ("junk", "Invalid FIGI format"),
        ("BSG000B9XRY4", "Invalid FIGI prefix"),
        ("BBG000B9XRY3", "Invalid FIGI check digit"),
        ("", "must not be empty"),
        ("  ", "must not be empty"),
        ("-", "Invalid FIGI format"),
        (None, "valid string"),
        (123, "valid string"),
    ],
)
def test_figi_vo_rejects_bad_root(build: Callable[[Any], FIGI], value: Any, match: str) -> None:
    with pytest.raises(ValidationError, match=match):
        build(value)


# --- .Input fields on Security and SecurityQuery -----------------------------------------


def _security(**kwargs: Any) -> Security:
    return Security(symbol="AAPL", name="Apple", **kwargs)


_MODELS: list[Callable[..., Security | SecurityQuery]] = [_security, SecurityQuery]


@pytest.mark.parametrize("make", _MODELS)
@pytest.mark.parametrize("value", [_ISIN, " us0378331005 ", ISIN(_ISIN)])
def test_isin_field_accepts_str_and_vo(make: Callable[..., Any], value: Any) -> None:
    assert make(isin=value).isin == _ISIN


@pytest.mark.parametrize("make", _MODELS)
@pytest.mark.parametrize("value", [_FIGI, " bbg000b9xry4 ", FIGI(_FIGI)])
def test_figi_field_accepts_str_and_vo(make: Callable[..., Any], value: Any) -> None:
    assert make(figi=value).figi == _FIGI


@pytest.mark.parametrize("make", _MODELS)
@pytest.mark.parametrize("value", [None, "", "-", "NONE", "  "])
def test_isin_field_placeholder_becomes_none(make: Callable[..., Any], value: Any) -> None:
    assert make(isin=value).isin is None


@pytest.mark.parametrize("make", _MODELS)
@pytest.mark.parametrize("value", [None, "", "  "])
def test_figi_field_empty_becomes_none(make: Callable[..., Any], value: Any) -> None:
    assert make(figi=value).figi is None


@pytest.mark.parametrize("make", _MODELS)
@pytest.mark.parametrize("field", ["isin", "figi"])
@pytest.mark.parametrize("value", ["junk", 123])
def test_identifier_field_rejects_bad_value(
    make: Callable[..., Any], field: str, value: Any
) -> None:
    with pytest.raises(ValidationError):
        make(**{field: value})


def test_security_query_validate_assignment() -> None:
    q = SecurityQuery()
    q.isin = ISIN(_ISIN)
    q.figi = FIGI(_FIGI)
    assert (q.isin, q.figi) == (_ISIN, _FIGI)
    q.isin = "-"
    assert q.isin is None
    with pytest.raises(ValidationError):
        q.isin = "NOTANISIN123"
    with pytest.raises(ValidationError):
        q.figi = "junk"


def test_model_validate_and_dump_round_trip() -> None:
    s = Security.model_validate(
        {"symbol": "AAPL", "name": "Apple", "isin": ISIN(_ISIN), "figi": FIGI(_FIGI)}
    )
    assert s.model_dump(include={"isin", "figi"}) == {"isin": _ISIN, "figi": _FIGI}


# --- Module-level validators keep their str behaviour ------------------------------------


def test_str_validators_unchanged() -> None:
    assert validate_isin(" us0378331005 ") == _ISIN
    assert validate_isin("-") is None
    assert clean_isin("NONE") is None
    assert validate_figi("") is None
    assert validate_figi(_FIGI) == _FIGI


# --- Lax str coercion must not bypass the checks -----------------------------------------


@pytest.mark.parametrize("build", [*_BUILDERS, *_FIGI_BUILDERS])
@pytest.mark.parametrize("value", [b"junk", bytearray(b"junk")])
def test_vo_validates_bytes_after_coercion(build: Callable[[Any], Any], value: Any) -> None:
    with pytest.raises(ValidationError, match="Invalid"):
        build(value)


@pytest.mark.parametrize("build", [*_BUILDERS, *_FIGI_BUILDERS])
def test_vo_accepts_valid_bytes(build: Callable[[Any], Any]) -> None:
    value = _ISIN if build in _BUILDERS else _FIGI
    assert build(f" {value.lower()} ".encode()).root == value


@pytest.mark.parametrize("make", _MODELS)
@pytest.mark.parametrize("field", ["isin", "figi"])
@pytest.mark.parametrize("value", [b"junk", bytearray(b"junk")])
def test_identifier_field_rejects_bytes(make: Callable[..., Any], field: str, value: Any) -> None:
    with pytest.raises(ValidationError):
        make(**{field: value})


def test_top_level_identifiers_are_value_objects() -> None:
    """Issue #28: top-level ``ISIN`` is the value object, like ``FIGI``, not the CLI metavar."""
    assert pydantic_market_data.ISIN is models.ISIN
    assert pydantic_market_data.FIGI is models.FIGI
    assert pydantic_market_data.ISIN is not cli_models.ISIN
    assert pydantic_market_data.__all__.count("ISIN") == 1
    assert pydantic_market_data.ISIN(_ISIN).root == _ISIN
    with pytest.raises(ValidationError, match="Invalid ISIN checksum"):
        pydantic_market_data.ISIN("NOTANISIN123")
