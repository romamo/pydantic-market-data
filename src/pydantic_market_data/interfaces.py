from __future__ import annotations

from datetime import date
from typing import Protocol

from .models import (
    History,
    HistoryPeriod,
    Price,
    Security,
    SecurityQuery,
    Symbol,
)


class DataSource(Protocol):
    """
    Interface for a financial data source.
    """

    def search(self, query: str) -> list[Security]:
        """
        Search for security by ISIN, symbol, or name
        """
        ...

    def resolve(self, criteria: SecurityQuery) -> Security | None:
        """
        Resolve security based on provided criteria
        """
        ...

    def history(self, symbol: Symbol.Input, period: HistoryPeriod = HistoryPeriod.MO1) -> History:
        """
        Fetch historical data for a symbol
        """
        ...

    def get_price(self, symbol: Symbol.Input, date: date | None = None) -> Price | None:
        """Fetch the price for a symbol (current or historical)"""
        ...

    def validate(self, symbol: Symbol.Input, target_date: date, target_price: Price.Input) -> bool:
        """
        Validates if the symbol traded near the target price on the target date.
        """
        ...
