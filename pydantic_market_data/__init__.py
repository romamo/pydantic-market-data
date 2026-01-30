import importlib.metadata

try:
    __version__ = importlib.metadata.version("pydantic-market-data")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0"

from .interfaces import DataSource
from .models import (
    OHLCV,
    FlexibleDate,
    FlexibleDatetime,
    History,
    HistoryInterval,
    HistoryPeriod,
    SearchResult,
    SecurityCriteria,
    Symbol,
)

__all__ = [
    "Symbol",
    "OHLCV",
    "History",
    "HistoryInterval",
    "HistoryPeriod",
    "SearchResult",
    "SecurityCriteria",
    "DataSource",
    "FlexibleDate",
    "FlexibleDatetime",
]
