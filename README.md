# pydantic-market-data

[![PyPI version](https://img.shields.io/pypi/v/pydantic-market-data.svg)](https://pypi.org/project/pydantic-market-data/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI Status](https://github.com/romamo/pydantic-market-data/actions/workflows/ci.yml/badge.svg)](https://github.com/romamo/pydantic-market-data/actions)

Shared Pydantic models and interfaces for financial data sources.
Defines a standard contract (`DataSource`) and data structures (`OHLCV`, `Security`, `History`) to ensure interoperability between finance packages.

## Installation

```bash
pip install pydantic-market-data
```

## Usage

### Models

Standardized data models for financial entities.

```python
from pydantic_market_data.models import Security, OHLCV, History, SecurityCriteria, Symbol

# Security Definition
s = Security(
    symbol="AAPL",
    name="Apple Inc.",
    exchange="NASDAQ",
    currency="USD",
    asset_class="Equity",
    isin="US0378331005"
)

# Historical Data Point
candle = OHLCV(
    date="2023-12-01", # Coerced to FlexibleDatetime
    open=150.0,
    high=155.0,
    low=149.0,
    close=154.0,
    volume=50000000
)

# Security Lookup Criteria
criteria = SecurityCriteria(
    symbol="AAPL",
    asset_class="Equity",
    target_date="2023-12-01" # Coerced to FlexibleDate
)
```

### Protocol

Implement the `DataSource` protocol to create compatible data providers.

```python
from typing import Optional, List
from pydantic_market_data.interfaces import DataSource
from pydantic_market_data.models import SecurityCriteria, Security, History, Symbol, HistoryPeriod

class MySource(DataSource):
    def resolve(self, criteria: SecurityCriteria) -> Optional[Security]:
        # Implementation...
        pass

    def history(self, symbol: Symbol | str, period: HistoryPeriod = HistoryPeriod.MO1) -> History:
        # Implementation...
        pass

    def search(self, query: str) -> List[Security]:
        # Implementation...
        pass
```

## CLI Support

The package provides optimized `pydantic-settings` models for building professional CLI tools.

```python
from pydantic_market_data.cli_models import SearchArgs, PatchedCliSettingsSource
from pydantic_settings import BaseSettings

class MyCliSettings(BaseSettings):
    search: SearchArgs

    @classmethod
    def settings_customise_sources(cls, settings_cls, **kwargs):
        return (PatchedCliSettingsSource(settings_cls),)

# Usage:
# my-tool search --symbol AAPL --vv --format json
```

Key CLI features:
- **Clean Help**: Automatically removes default values from help text for a cleaner look.
- **Improved Flags**: Normalizes double-dash flags like `--vv` to `-vv`.
- **JSON Schema**: Adds a `--schema` flag to output the interface definition.
- **Metavars**: Custom types (`SYMBOL`, `ISIN`, etc.) provide descriptive help labels.

## License

MIT
