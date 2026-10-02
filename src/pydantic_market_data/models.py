from __future__ import annotations

import re
from datetime import date, datetime
from enum import Enum
from typing import TYPE_CHECKING, Annotated, Any, ClassVar, TypeAlias

import pandas as pd
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    GetCoreSchemaHandler,
    GetJsonSchemaHandler,
    PositiveInt,
    RootModel,
    field_validator,
)
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import PydanticCustomError, core_schema
from pydantic_extra_types.country import CountryAlpha2
from pydantic_extra_types.currency_code import Currency

# Re-exported for downstream consumers


_DATE_PATTERN = re.compile(r"([0-9]{4})([-/]?)([0-9]{2})\2([0-9]{2})")


def parse_date(v: date | str) -> date:
    """Parse ``YYYY-MM-DD``, ``YYYY/MM/DD`` or ``YYYYMMDD``; date objects pass through."""
    if isinstance(v, str):
        match = _DATE_PATTERN.fullmatch(v)
        if match is None:
            raise ValueError(f"Invalid date: {v!r}; expected YYYY-MM-DD, YYYY/MM/DD or YYYYMMDD")
        year, _, month, day = match.groups()
        return date(int(year), int(month), int(day))
    return v


def parse_datetime(v: datetime | str) -> datetime:
    if isinstance(v, str):
        return pd.to_datetime(v).to_pydatetime()
    return v


def clean_isin(v: str | None) -> str | None:
    """Cleans ISIN field, handles common junk like '-' from Yahoo."""
    if v is None:
        return None
    v = v.strip().upper()
    if not v or v == "-" or v == "NONE":
        return None
    return v


def validate_isin(v: str | None) -> str | None:
    v = clean_isin(v)
    if v is None:
        return None
    if not re.match(r"^[A-Z]{2}[A-Z0-9]{9}\d$", v):
        raise ValueError(f"Invalid ISIN format: {v}")

    # Luhn checksum validation
    def luhn_checksum(isin: str) -> bool:
        # Convert ISIN to digits
        # Letters A-Z map to 10-35
        digits = []
        for char in isin:
            if char.isdigit():
                digits.append(int(char))
            else:
                val = ord(char) - ord("A") + 10
                digits.extend(divmod(val, 10)) if val >= 10 else digits.append(val)

        # Apply Luhn from right to left
        checksum = 0
        reverse_digits = digits[::-1]
        for i, digit in enumerate(reverse_digits):
            if i % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            checksum += digit
        return checksum % 10 == 0

    if not luhn_checksum(v):
        raise ValueError(f"Invalid ISIN checksum: {v}")

    return v


_FIGI_RESERVED = {"BS", "BM", "GG", "GB", "GH", "KY", "VG"}
_FIGI_PATTERN = re.compile(r"^[A-Z]{2}G[B-DF-HJ-NP-TV-Z0-9]{8}\d$")


def validate_figi(v: str | None) -> str | None:
    if v is None:
        return None
    v = v.strip().upper()
    if not v:
        return None
    if not _FIGI_PATTERN.match(v):
        raise ValueError(f"Invalid FIGI format: {v}")
    if v[:2] in _FIGI_RESERVED:
        raise ValueError(f"Invalid FIGI prefix: {v[:2]}")
    total = 0
    for i, ch in enumerate(reversed(v[:11])):
        val = int(ch) if ch.isdigit() else ord(ch) - ord("A") + 10
        if i % 2 == 1:
            val *= 2
        total += val % 10 + val // 10
    if (10 - (total % 10)) % 10 != int(v[11]):
        raise ValueError(f"Invalid FIGI check digit: {v}")
    return v


FlexibleDate: TypeAlias = Annotated[date, BeforeValidator(parse_date)]
FlexibleDatetime: TypeAlias = Annotated[datetime, BeforeValidator(parse_datetime)]


class AssetClass(str, Enum):
    EQUITY = "equity"
    FIXED_INCOME = "fixed_income"
    CASH = "cash"
    COMMODITY = "commodity"
    REAL_ESTATE = "real_estate"
    FX = "fx"
    CRYPTO = "crypto"
    DERIVATIVE = "derivative"
    ALTERNATIVE = "alternative"
    INDEX = "index"


class HistoryInterval(str, Enum):
    IM1 = "1m"
    IM2 = "2m"
    IM5 = "5m"
    IM15 = "15m"
    IM30 = "30m"
    IM60 = "60m"
    IM90 = "90m"
    H1 = "1h"
    D1 = "1d"
    D5 = "5d"
    W1 = "1wk"
    MO1 = "1mo"
    MO3 = "3mo"


class HistoryPeriod(str, Enum):
    D1 = "1d"
    D5 = "5d"
    MO1 = "1mo"
    MO3 = "3mo"
    MO6 = "6mo"
    Y1 = "1y"
    Y2 = "2y"
    Y5 = "5y"
    Y10 = "10y"
    YTD = "ytd"
    MAX = "max"


class Price(RootModel[float]):
    """
    Strict Value Object for prices to avoid primitive obsession everywhere.
    """

    if TYPE_CHECKING:
        Input: TypeAlias = "Price" | float  # type: ignore[misc]
    else:
        Input: ClassVar[Any] = Annotated["Price", BeforeValidator(lambda v: v)]

    @property
    def value(self) -> float:
        return self.root

    def __str__(self) -> str:
        return str(self.root)


class StrictDate(RootModel[date]):
    """
    Strict Value Object for dates.
    """

    if TYPE_CHECKING:
        Input: TypeAlias = "StrictDate" | date  # type: ignore[misc]
    else:
        Input: ClassVar[Any] = Annotated["StrictDate", BeforeValidator(lambda v: v)]

    @property
    def value(self) -> date:
        return self.root

    def __str__(self) -> str:
        return str(self.root)


def _isin_root(v: str) -> str:
    """Validate and normalize an ``ISIN`` root; placeholders cannot become a VO.

    Runs after pydantic's ``str`` coercion, so lax inputs such as ``bytes`` are checked too.
    """
    isin = validate_isin(v)
    if isin is None:
        raise ValueError(f"ISIN must not be empty or a placeholder: {v!r}")
    return isin


def _isin_field(v: Any) -> Any:
    """``ISIN.Input`` coercion: unwrap an ``ISIN``, validate a str, map placeholders to None."""
    if isinstance(v, ISIN):
        return v.root
    if isinstance(v, str):
        return validate_isin(v)
    if v is None:
        return None
    raise ValueError(f"ISIN must be a str or ISIN, got {type(v).__name__}")


class ISIN(RootModel[str]):
    """
    Strict Value Object for ISIN identifiers.
    """

    if TYPE_CHECKING:
        Input: TypeAlias = "ISIN" | str | None  # type: ignore[misc]
    else:
        Input: ClassVar[Any] = Annotated["ISIN | str | None", BeforeValidator(_isin_field)]

    # The root is stripped, upper-cased and checked for format and Luhn checksum.
    _validate_root = field_validator("root", mode="after")(_isin_root)

    @property
    def value(self) -> str:
        return self.root

    def __str__(self) -> str:
        return self.root


def _figi_root(v: str) -> str:
    """Validate and normalize a ``FIGI`` root; an empty value cannot become a VO.

    Runs after pydantic's ``str`` coercion, so lax inputs such as ``bytes`` are checked too.
    """
    figi = validate_figi(v)
    if figi is None:
        raise ValueError(f"FIGI must not be empty: {v!r}")
    return figi


def _figi_field(v: Any) -> Any:
    """``FIGI.Input`` coercion: unwrap a ``FIGI``, validate a str, map empty to None."""
    if isinstance(v, FIGI):
        return v.root
    if isinstance(v, str):
        return validate_figi(v)
    if v is None:
        return None
    raise ValueError(f"FIGI must be a str or FIGI, got {type(v).__name__}")


class FIGI(RootModel[str]):
    """
    Strict Value Object for FIGI (Financial Instrument Global Identifier).
    """

    if TYPE_CHECKING:
        Input: TypeAlias = "FIGI" | str | None  # type: ignore[misc]
    else:
        Input: ClassVar[Any] = Annotated["FIGI | str | None", BeforeValidator(_figi_field)]

    # The root is stripped, upper-cased and checked for format, prefix and check digit.
    _validate_root = field_validator("root", mode="after")(_figi_root)

    @property
    def value(self) -> str:
        return self.root

    def __str__(self) -> str:
        return self.root


class Symbol(RootModel[str]):
    """
    Strict Value Object for security symbols (e.g. AAPL) to avoid primitive obsession.
    """

    if TYPE_CHECKING:
        Input: TypeAlias = "Symbol" | str  # type: ignore[misc]
    else:
        Input: ClassVar[Any] = Annotated["Symbol", BeforeValidator(lambda v: v)]

    @property
    def value(self) -> str:
        return self.root

    def __str__(self) -> str:
        return self.root


def validate_country_code(v: Any) -> Any:
    if isinstance(v, str) and len(v) != 2:
        import pycountry  # noqa: PLC0415

        try:
            found = pycountry.countries.lookup(v)
            return found.alpha_2
        except LookupError:
            raise ValueError(f"Unknown country name: {v!r}") from None
    return v


class Country(RootModel[CountryAlpha2]):
    """
    Strict Value Object for country codes.
    """

    if TYPE_CHECKING:
        Input: TypeAlias = "Country" | CountryAlpha2 | str  # type: ignore[misc]
    else:
        Input: ClassVar[Any] = Annotated["Country", BeforeValidator(validate_country_code)]

    @property
    def value(self) -> CountryAlpha2:
        return self.root

    def __str__(self) -> str:
        return str(self.root)


# Minor-unit quote codes (not ISO 4217) -> (major ISO 4217 code, minor units per major unit)
_MINOR_UNIT_CODES: dict[str, tuple[str, int]] = {
    "GBX": ("GBP", 100),  # pence sterling, LSE quotes
    "ZAC": ("ZAR", 100),  # South African cents, JSE quotes
    "ILA": ("ILS", 100),  # Israeli agorot, TASE quotes
}
# Exact mixed-case spellings that mean the minor unit; any other case of "GBP"/"ZAC" does not
_MIXED_CASE_MINOR_ALIASES: dict[str, str] = {"GBp": "GBX", "ZAc": "ZAC"}


class QuoteCurrency(str):
    """A currency code a price can be quoted in.

    An ISO 4217 currency code (bond, metal and testing codes excluded, as in
    ``pydantic_extra_types.currency_code.Currency``) or a minor-unit quote code: ``GBX``
    (pence), ``ZAC`` (South African cents), ``ILA`` (agorot). Input is case-insensitive and
    stored uppercase, except the exact mixed-case ``GBp`` and ``ZAc``, which mean ``GBX`` and
    ``ZAC`` (``gbp`` and ``Gbp`` still mean ``GBP``). Direct construction validates too:
    ``QuoteCurrency("GBp") == "GBX"``; an unknown code raises ``ValueError``.
    """

    allowed_codes: ClassVar[list[str]] = sorted(
        [*Currency.allowed_countries_list, *_MINOR_UNIT_CODES]
    )
    _allowed: ClassVar[frozenset[str]] = frozenset(allowed_codes)

    def __new__(cls, value: str) -> QuoteCurrency:
        if not isinstance(value, str):
            raise TypeError(f"Currency code must be a str, got {type(value).__name__}")
        code = _MIXED_CASE_MINOR_ALIASES.get(value, value.upper())
        if code not in cls._allowed:
            # PydanticCustomError is a ValueError, so direct construction raises ValueError
            # and the pydantic path reports error type "InvalidCurrency"
            raise PydanticCustomError(
                "InvalidCurrency",
                "Invalid currency code '{code}': expected an ISO 4217 currency code"
                " (https://en.wikipedia.org/wiki/ISO_4217; bond, testing and precious metal"
                " codes are not allowed) or a minor-unit code GBX/GBp, ZAC/ZAc, ILA",
                {"code": value},
            )
        return super().__new__(cls, code)

    @classmethod
    def _validate(cls, v: str) -> QuoteCurrency:
        return cls(v)

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source: Any, _handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls._validate, core_schema.str_schema(min_length=3, max_length=3)
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        json_schema = handler(schema)
        json_schema["enum"] = list(cls.allowed_codes)
        return json_schema


# The docstring is the JSON schema description: accepted codes are documented on QuoteCurrency
class CurrencyCode(RootModel[QuoteCurrency]):
    """
    Strict Value Object for currency codes.
    """

    if TYPE_CHECKING:
        Input: TypeAlias = "CurrencyCode" | QuoteCurrency | str  # type: ignore[misc]
    else:
        Input: ClassVar[Any] = Annotated["CurrencyCode", BeforeValidator(lambda v: v)]

    @property
    def value(self) -> QuoteCurrency:
        return self.root

    def to_major(self) -> MajorCurrency:
        """The major currency and factor: ``GBX`` -> ``GBP``/100; an ISO code -> itself/1."""
        major, factor = _MINOR_UNIT_CODES.get(self.root, (self.root, 1))
        return MajorCurrency(currency=CurrencyCode(QuoteCurrency(major)), factor=factor)

    def __str__(self) -> str:
        return str(self.root)


class MajorCurrency(BaseModel):
    """The major currency of a quote code and how many quote units make one major unit.

    Divide a price quoted in the code by ``factor`` to get the price in ``currency``.
    """

    model_config = ConfigDict(frozen=True)

    currency: CurrencyCode.Input
    factor: PositiveInt

    @field_validator("currency")
    @classmethod
    def _check_major(cls, v: CurrencyCode) -> CurrencyCode:
        if v.root in _MINOR_UNIT_CODES:
            raise ValueError(f"{v.root} is a minor-unit code, not a major currency")
        return v


class PriceVerificationError(Exception):
    """
    Exception raised when price verification fails.
    Carries the actual market data for reporting.
    """

    def __init__(
        self,
        message: str,
        symbol: Symbol.Input,
        actual_date: date | str,
        expected_price: Price.Input,
        actual_low: Price.Input | None = None,
        actual_high: Price.Input | None = None,
        actual_close: Price.Input | None = None,
        source: str | None = None,
    ):
        super().__init__(message)
        self.symbol = symbol if isinstance(symbol, Symbol) else Symbol(symbol)
        self.actual_date = parse_date(actual_date)
        self.expected_price = (
            expected_price if isinstance(expected_price, Price) else Price(expected_price)
        )
        self.actual_low = (
            actual_low if isinstance(actual_low, Price) or actual_low is None else Price(actual_low)
        )
        self.actual_high = (
            actual_high
            if isinstance(actual_high, Price) or actual_high is None
            else Price(actual_high)
        )
        self.actual_close = (
            actual_close
            if isinstance(actual_close, Price) or actual_close is None
            else Price(actual_close)
        )
        self.source = source

    def __str__(self) -> str:
        details = []
        if self.actual_low is not None and self.actual_high is not None:
            details.append(f"Range: {self.actual_low.value:.2f} - {self.actual_high.value:.2f}")
        if self.actual_close is not None:
            details.append(f"Close: {self.actual_close.value:.2f}")

        parts = []
        if self.source:
            parts.append(f"{self.source}:")

        # The message itself should explain the 'why' (e.g. "Price is outside daily range")
        parts.append(super().__str__())

        if details:
            parts.append(f"({', '.join(details)})")

        return f"[{self.symbol.value}] {' '.join(parts)}"


# Boundary types now handled via Namespace Pattern in VOs


class Security(BaseModel):
    """
    Represents a resolved security.
    """

    symbol: Symbol.Input  # e.g., "AAPL:NSQ"
    name: str  # e.g., "Apple Inc"
    exchange: str | None = None
    country: Country.Input | None = None
    currency: CurrencyCode.Input | None = None
    asset_class: AssetClass | None = None
    security_type: str | None = None
    isin: ISIN.Input | None = None
    figi: FIGI.Input | None = None


class OHLCV(BaseModel):
    """
    Represents a single price range.
    """

    date: FlexibleDatetime
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: float | None = None

    model_config = ConfigDict(validate_assignment=True)


class History(BaseModel):
    """
    Represents a collection of historical price data.
    """

    security: Security
    candles: list[OHLCV] = Field(
        description="Candles in ascending date order",
        json_schema_extra={"x-ordered": True},
    )

    @field_validator("candles")
    @classmethod
    def _check_ascending_dates(cls, v: list[OHLCV]) -> list[OHLCV]:
        """Reject candles that are not in strictly ascending date order."""
        for i in range(1, len(v)):
            prev, curr = v[i - 1].date, v[i].date
            prev_aware = prev.utcoffset() is not None
            curr_aware = curr.utcoffset() is not None
            if prev_aware != curr_aware:
                raise ValueError(
                    f"candles mix timezone-aware and naive dates: candle {i - 1} date "
                    f"{prev.isoformat()} ({'aware' if prev_aware else 'naive'}), candle {i} "
                    f"date {curr.isoformat()} ({'aware' if curr_aware else 'naive'})"
                )
            if curr <= prev:
                raise ValueError(
                    f"candles must be in strictly ascending date order: candle {i} date "
                    f"{curr.isoformat()} is not after candle {i - 1} date {prev.isoformat()}"
                )
        return v

    def to_pandas(self) -> pd.DataFrame:
        """
        Converts the history to a Pandas DataFrame indexed by Date.
        """
        data = [c.model_dump() for c in self.candles]
        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)
            df.index.name = "Date"

        # Standardize columns to Title Case for compatibility
        df.rename(
            columns={
                "open": "Open",
                "high": "High",
                "low": "Low",
                "close": "Close",
                "volume": "Volume",
            },
            inplace=True,
        )

        return df


class SearchResult(Security):
    pass


class PriceOnDate(BaseModel):
    price: Price.Input
    date: FlexibleDate


def _coerce_price_on_list(v: Any) -> Any:
    return [v] if not isinstance(v, list) else v


class SecurityQuery(BaseModel):
    """
    Criteria for resolving a security.
    """

    isin: ISIN.Input | None = None
    figi: FIGI.Input | None = None
    symbol: Symbol.Input | None = None
    description: str | None = None
    price_on: Annotated[list[PriceOnDate], BeforeValidator(_coerce_price_on_list)] | None = None
    currency: CurrencyCode.Input | None = None
    exchange: str | None = None
    asset_class: AssetClass | None = None

    model_config = ConfigDict(validate_assignment=True)
