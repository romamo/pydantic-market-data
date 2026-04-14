# Migration Guide: v0.1.x to v0.2.0

Version 0.2.0 introduces a significant rename of core models to align with financial industry standards (e.g., FIX, Yahoo Finance, Interactive Brokers). This is a **breaking change**.

## Summary of Renames

| Old Name (v0.1.x) | New Name (v0.2.0) | Description |
| :--- | :--- | :--- |
| `Ticker` | `Symbol` | The string identifier (e.g., "AAPL"). |
| `Symbol` | `Security` | The full data object with name, exchange, etc. |
| `Symbol.ticker` | `Security.symbol` | The field within the security object. |
| `History.symbol` | `History.security` | The field within the history object. |
| `PriceVerificationError.ticker` | `PriceVerificationError.symbol` | The field within the error object. |
| `--ticker` (CLI) | `--symbol` (CLI) | CLI argument in `SearchArgs` and `HistoryArgs`. |

## Action Items

### 1. Update Imports
If you were importing `Ticker` or `Symbol`, you need to update your imports.

**Before:**
```python
from pydantic_market_data import Symbol, Ticker
```

**After:**
```python
from pydantic_market_data import Security, Symbol
```

### 2. Update Model Initialization
Update field names when creating `Security` (formerly `Symbol`) objects.

**Before:**
```python
s = Symbol(ticker="AAPL", name="Apple Inc.")
```

**After:**
```python
s = Security(symbol="AAPL", name="Apple Inc.")
```

### 3. Update Interface Implementations
If you implemented the `DataSource` protocol, update the method signatures and return types.

**Before:**
```python
def history(self, ticker: Ticker.Input, ...) -> History:
    ...
```

**After:**
```python
def history(self, symbol: Symbol.Input, ...) -> History:
    ...
```

### 4. Update CLI Tooling
If you use `SearchArgs` or `HistoryArgs` with `pydantic-settings`, the command-line flag has changed.

**Before:**
```bash
my-tool search --ticker AAPL
```

**After:**
```bash
my-tool search --symbol AAPL
```

## Why this change?
"Ticker" is often used interchangeably with "Symbol", but in most industrial APIs, **Symbol** is the standard term for the identifier, and **Security** or **Instrument** represents the asset. This change resolves the ambiguity where the `Symbol` class actually represented a "Security" and its `ticker` field was the "Symbol".
