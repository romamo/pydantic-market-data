from __future__ import annotations

from datetime import date
from typing import Protocol

from .models import (
    History,
    HistoryPeriod,
    Price,
    SecurityCriteria,
    Symbol,
    Ticker,
)


class DataSource(Protocol):
    """
    Interface for a financial data source.
    """

    def search(self, query: str) -> list[Symbol]:
        """
        Search for security by ISIN, symbol, or name
        """
        ...

    def resolve(self, criteria: SecurityCriteria) -> Symbol | None:
        """
        Resolve security based on provided criteria
        """
        ...

    def history(self, ticker: Ticker.Input, period: HistoryPeriod = HistoryPeriod.MO1) -> History:
        """
        Fetch historical data for a ticker
        """
        ...

    def get_price(self, ticker: Ticker.Input, date: date | None = None) -> Price | None:
        """Fetch the price for a ticker (current or historical)"""
        ...

    def validate(self, ticker: Ticker.Input, target_date: date, target_price: Price.Input) -> bool:
        """
        Validates if the ticker traded near the target price on the target date.
        """
        ...
