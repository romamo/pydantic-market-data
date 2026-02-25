import importlib.metadata

try:
    __version__ = importlib.metadata.version("pydantic-market-data")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.1.15"

from .interfaces import DataSource
from .models import (
    ISIN,
    OHLCV,
    Country,
    CountryAlpha2,
    Currency,
    CurrencyCode,
    FlexibleDate,
    FlexibleDatetime,
    History,
    HistoryInterval,
    HistoryPeriod,
    Price,
    PriceVerificationError,
    SearchResult,
    SecurityCriteria,
    StrictDate,
    Symbol,
    Ticker,
)

__all__ = [
    "Country",
    "CountryAlpha2",
    "Currency",
    "CurrencyCode",
    "DataSource",
    "FlexibleDate",
    "FlexibleDatetime",
    "History",
    "HistoryInterval",
    "HistoryPeriod",
    "ISIN",
    "OHLCV",
    "Price",
    "PriceVerificationError",
    "SearchResult",
    "SecurityCriteria",
    "StrictDate",
    "Symbol",
    "Ticker",
]
