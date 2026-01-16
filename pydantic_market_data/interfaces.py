from typing import List, Optional, Protocol

from .models import History, HistoryPeriod, SecurityCriteria, Symbol


class DataSource(Protocol):
    """
    Interface for a financial data source.
    """

    def search(self, query: str) -> List[Symbol]:
        """
        Search for a security by ISIN, symbol, or name.
        """
        ...

    def resolve(self, criteria: SecurityCriteria) -> Optional[Symbol]:
        """
        Resolve a security based on provided criteria.
        """
        ...

    def history(self, ticker: str, period: HistoryPeriod = HistoryPeriod.MO1) -> History:
        """
        Fetch historical data for a ticker.
        """
        ...
