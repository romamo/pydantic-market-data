import re
from datetime import date, datetime
from enum import Enum
from typing import TYPE_CHECKING, Annotated, Any, TypeAlias

import pandas as pd
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    RootModel,
)
from pydantic_extra_types.country import CountryAlpha2
from pydantic_extra_types.currency_code import Currency

# Re-exported for downstream consumers


def parse_date(v: date | str) -> date:
    if isinstance(v, str):
        return pd.to_datetime(v).date()
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


FlexibleDate: TypeAlias = Annotated[date, BeforeValidator(parse_date)]
FlexibleDatetime: TypeAlias = Annotated[datetime, BeforeValidator(parse_datetime)]


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

    @property
    def value(self) -> float:
        return self.root

    def __str__(self) -> str:
        return str(self.root)


class StrictDate(RootModel[date]):
    """
    Strict Value Object for dates.
    """

    @property
    def value(self) -> date:
        return self.root

    def __str__(self) -> str:
        return str(self.root)


class ISIN(RootModel[str]):
    """
    Strict Value Object for ISIN identifiers.
    """

    @property
    def value(self) -> str:
        return self.root

    def __str__(self) -> str:
        return self.root


class Ticker(RootModel[str]):
    """
    Strict Value Object for ticker symbols to avoid primitive obsession.
    """

    @property
    def value(self) -> str:
        return self.root

    def __str__(self) -> str:
        return self.root


class PriceVerificationError(Exception):
    """
    Exception raised when price verification fails.
    Carries the actual market data for reporting.
    """

    def __init__(
        self,
        message: str,
        ticker: str,
        actual_date: date,
        expected_price: float,
        actual_low: float | None = None,
        actual_high: float | None = None,
        actual_close: float | None = None,
    ):
        super().__init__(message)
        self.ticker = ticker
        self.actual_date = actual_date
        self.expected_price = expected_price
        self.actual_low = actual_low
        self.actual_high = actual_high
        self.actual_close = actual_close

    def __str__(self) -> str:
        details = []
        if self.actual_low is not None and self.actual_high is not None:
            details.append(f"Range: {self.actual_low:.2f} - {self.actual_high:.2f}")
        if self.actual_close is not None:
            details.append(f"Close: {self.actual_close:.2f}")

        msg = super().__str__()
        if details:
            msg += f" (Actual {', '.join(details)})"
        return msg


def validate_country_code(v: Any) -> Any:
    if isinstance(v, str) and len(v) != 2:
        import pycountry  # noqa: PLC0415

        try:
            found = pycountry.countries.lookup(v)
            return found.alpha_2
        except LookupError:
            raise ValueError(f"Unknown country name: {v!r}") from None
    return v


if TYPE_CHECKING:
    TickerInput = Ticker | str
    CountryInput = CountryAlpha2 | str
    CurrencyInput = Currency | str
    PriceInput = Price | float
    DateInput = StrictDate | date
    ISINInput = ISIN | str | None
    ISINField = ISIN | str | None
else:
    TickerInput = Ticker
    CountryInput = Annotated[CountryAlpha2, BeforeValidator(validate_country_code)]
    CurrencyInput = Currency
    PriceInput = Price
    DateInput = StrictDate
    ISINInput = Annotated[ISIN | str | None, BeforeValidator(validate_isin)]
    ISINField = Annotated[ISIN | str | None, BeforeValidator(validate_isin)]


class Symbol(BaseModel):
    """
    Represents a resolved security symbol.
    """

    ticker: TickerInput  # e.g., "AAPL:NSQ"
    name: str  # e.g., "Apple Inc"
    exchange: str | None = None
    country: CountryInput | None = None
    currency: CurrencyInput | None = None
    asset_class: str | None = None
    isin: ISINField | None = None


class OHLCV(BaseModel):
    """
    Represents a single price candle.
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

    symbol: Symbol
    candles: list[OHLCV]

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


class SearchResult(Symbol):
    pass


class SecurityCriteria(BaseModel):
    """
    Criteria for resolving security
    """

    isin: ISINField | None = None
    symbol: TickerInput | None = None
    description: str | None = None
    target_price: PriceInput | None = None
    target_date: FlexibleDate | None = None
    currency: CurrencyInput | None = None
    exchange: str | None = None

    model_config = ConfigDict(validate_assignment=True)
