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
from pydantic_market_data.models import Security, OHLCV, SecurityQuery

# Security Definition
s = Security(
    symbol="AAPL",
    name="Apple Inc.",
    exchange="NASDAQ",
    currency="USD",
    asset_class="equity",  # AssetClass value
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

# Security Lookup Query
query = SecurityQuery(
    symbol="AAPL",
    asset_class="equity",
    price_on={"price": 190.0, "date": "2023-12-01"}  # Known price, coerced to list[PriceOnDate]
)
```

### Protocol

Implement the `DataSource` protocol to create compatible data providers.

```python
from pydantic_market_data.interfaces import DataSource
from pydantic_market_data.models import SecurityQuery, Security, History, Symbol, HistoryPeriod

class MySource(DataSource):
    def resolve(self, criteria: SecurityQuery) -> Security | None:
        # Implementation...
        pass

    def history(self, symbol: Symbol.Input, period: HistoryPeriod = HistoryPeriod.MO1) -> History:
        # Implementation...
        pass

    def search(self, query: str) -> list[Security]:
        # Implementation...
        pass

    # ...plus get_price() and validate()
```

## CLI Support

The package provides optimized `pydantic-settings` models for building professional CLI tools.

```python
from pydantic_market_data.cli_models import SearchArgs, PatchedCliSettingsSource
from pydantic_settings import BaseSettings, CliSubCommand

class MyCliSettings(BaseSettings):
    search: CliSubCommand[SearchArgs]

    @classmethod
    def settings_customise_sources(cls, settings_cls, **kwargs):
        return (PatchedCliSettingsSource(settings_cls, cli_parse_args=True),)

# Usage:
# my-tool search --symbol AAPL -vv --format json
```

Key CLI features:
- **Clean Help**: Automatically removes default values from help text for a cleaner look.
- **Improved Flags**: Normalizes double-dash flags like `--vv` to `-vv`.
- **JSON Schema**: Adds a `--schema` flag to output the interface definition.
- **Consistent Defaults**: Whatever order your `BaseSettings` subclass lists its bases in, multi-word fields become `--asset-class`, `-v`/`-vv` are valueless flags, and optional values show as `--symbol SYMBOL` (not `{SYMBOL,null}`). Pass `cli_kebab_case`, `cli_implicit_flags` or `cli_hide_none_type` to the source to override.
- **Metavars**: Custom types (`SYMBOL`, `ISIN`, etc.) provide descriptive help labels.

`SearchArgs` and `HistoryArgs` are `SecurityQueryArgs` and `HistoryQueryArgs` plus `GlobalArgs` (`-v`, `-vv`, `--format`, `--schema`). `SearchArgs` also adds `--limit`, a paging option that list-command frameworks are expected to own. If your CLI framework already owns those options, use the domain-only `*QueryArgs` models instead:

```python
from pydantic_market_data import SecurityQueryArgs

class SearchCommand(SecurityQueryArgs):
    pass  # --symbol, --isin, ... without -v/--format/--schema/--limit
```

## License

MIT
