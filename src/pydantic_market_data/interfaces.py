from datetime import date
from typing import Protocol

from .models import (
    History,
    HistoryPeriod,
    PriceInput,
    SecurityCriteria,
    Symbol,
    TickerInput,
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

    def history(self, ticker: TickerInput, period: HistoryPeriod = HistoryPeriod.MO1) -> History:
        """
        Fetch historical data for a ticker
        """
        ...

    def validate(self, ticker: TickerInput, target_date: date, target_price: PriceInput) -> bool:
        """
        Validates if the ticker traded near the target price on the target date.
        """
        ...
