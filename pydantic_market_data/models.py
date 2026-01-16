from datetime import date, datetime
from enum import Enum
from typing import TYPE_CHECKING, Annotated, Any, List, Optional, TypeAlias, Union

import pandas as pd
from pydantic import BaseModel, BeforeValidator, StringConstraints
from pydantic_extra_types.country import CountryAlpha2
from pydantic_extra_types.currency_code import Currency

# ...


def parse_date(v: Any) -> Any:
    if isinstance(v, str):
        try:
            return pd.to_datetime(v).date()
        except (ValueError, TypeError):
            pass
    return v


def parse_datetime(v: Any) -> Any:
    if isinstance(v, str):
        try:
            return pd.to_datetime(v).to_pydatetime()
        except (ValueError, TypeError):
            pass
    return v


if TYPE_CHECKING:
    FlexibleDate: TypeAlias = Union[date, str]
    FlexibleDatetime: TypeAlias = Union[datetime, str]
else:
    FlexibleDate = Annotated[date, BeforeValidator(parse_date)]
    FlexibleDatetime = Annotated[datetime, BeforeValidator(parse_datetime)]



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


ISIN = Annotated[
    str,
    StringConstraints(
        pattern=r"^[A-Z]{2}[A-Z0-9]{9}\d$",
        min_length=12,
        max_length=12,
        to_upper=True,  # Bonus: auto-uppercase
    ),
]


# ISIN is now defined above using Annotated for better str compatibility



class Symbol(BaseModel):
    """
    Represents a resolved security symbol.
    """

    ticker: str  # e.g., "AAPL:NSQ"
    name: str  # e.g., "Apple Inc"
    exchange: Optional[str] = None
    country: Optional[CountryAlpha2] = None
    currency: Optional[Currency] = None  # inferred

    def __init__(self, **data):
        # Allow lenient initialization for country (convert full names if possible or ignore)
        # But here we assume strictly cleaner data.
        # Ideally, we should add a `BeforeValidator` to map "United States" -> "US"
        super().__init__(**data)


class OHLCV(BaseModel):
    """
    Represents a single price candle.
    """

    date: FlexibleDatetime
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[float] = None


class History(BaseModel):
    """
    Represents a collection of historical price data.
    """

    symbol: Symbol
    candles: List[OHLCV]

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
    Criteria for resolving a security.
    """

    isin: Optional[ISIN] = None
    symbol: Optional[str] = None
    description: Optional[str] = None
    preferred_exchanges: Optional[List[str]] = None
    target_price: Optional[float] = None
    target_date: Optional[FlexibleDate] = None  # Flexible date parsing
