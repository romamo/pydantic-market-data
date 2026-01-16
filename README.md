# pydantic-market-data

Shared Pydantic models and interfaces for financial data sources.
Defines a standard contract (`DataSource`) and data structures (`OHLCV`, `Symbol`, `History`) to interoperability between finance packages.

## Installation

```bash
pip install pydantic-market-data
```

## Usage

### Models

Standardized data models for financial entities.

```python
from pydantic_market_data.models import Symbol, OHLCV, History, SecurityCriteria

# Symbol Definition
s = Symbol(
    ticker="AAPL",
    name="Apple Inc.",
    exchange="NASDAQ",
    currency="USD"
)

# Historical Data Point
candle = OHLCV(
    date="2023-12-01",
    open=150.0,
    high=155.0,
    low=149.0,
    close=154.0,
    volume=50000000
)

# Security Lookup Criteria
criteria = SecurityCriteria(
    symbol="AAPL",
    preferred_exchanges=["NASDAQ"],
    target_date="2023-12-01"
)
```

### Protocol

Implement the `DataSource` protocol to create compatible data providers.

```python
from typing import Optional, List
from pydantic_market_data.interfaces import DataSource
from pydantic_market_data.models import SecurityCriteria, Symbol, History

class MySource(DataSource):
    def resolve(self, criteria: SecurityCriteria) -> Optional[Symbol]:
        # Implementation...
        pass

    def history(self, ticker: str, period: str = "1mo") -> History:
        # Implementation...
        pass
```

## License

MIT
