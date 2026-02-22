import importlib.metadata

try:
    __version__ = importlib.metadata.version("pydantic-market-data")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.1.14"

from .interfaces import DataSource
from .models import (
    ISIN,
    OHLCV,
    CountryAlpha2,
    CountryInput,
    Currency,
    CurrencyInput,
    DateInput,
    FlexibleDate,
    FlexibleDatetime,
    History,
    HistoryInterval,
    HistoryPeriod,
    ISINInput,
    Price,
    PriceInput,
    PriceVerificationError,
    SearchResult,
    SecurityCriteria,
    StrictDate,
    Symbol,
    Ticker,
    TickerInput,
)

__all__ = [
    "CountryAlpha2",
    "CountryInput",
    "Currency",
    "CurrencyInput",
    "DataSource",
    "DateInput",
    "FlexibleDate",
    "FlexibleDatetime",
    "History",
    "HistoryInterval",
    "HistoryPeriod",
    "ISIN",
    "ISINInput",
    "OHLCV",
    "Price",
    "PriceInput",
    "PriceVerificationError",
    "SearchResult",
    "SecurityCriteria",
    "StrictDate",
    "Symbol",
    "Ticker",
    "TickerInput",
]
