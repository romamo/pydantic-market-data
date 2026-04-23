# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install / sync dependencies
uv sync

# Run all tests
uv run pytest

# Run a single test
uv run pytest tests/test_models.py::test_symbol_str

# Lint
uv run ruff check .

# Type check
uv run mypy src

# Security audit
uv run bandit -r src/

# Build the package
uv build
```

## Architecture

This is a small, single-package library (`src/pydantic_market_data/`) with three modules and no internal dependencies between them except `cli_models` importing from `models`.

### `models.py` — domain model layer

All financial entities live here. The central pattern is the **Namespace Pattern for Value Objects**: every VO (e.g. `Symbol`, `Price`, `ISIN`, `Country`, `CurrencyCode`) is a Pydantic `RootModel` that exposes an `Input` class attribute. Under `TYPE_CHECKING` this is a `TypeAlias` (`"Symbol" | str`) so mypy sees the wide union; at runtime it's an `Annotated` type with a `BeforeValidator` so Pydantic performs coercion. Fields on models use `VO.Input` (e.g. `symbol: Symbol.Input`) to accept primitives at the boundary while keeping internal values strongly typed.

`FlexibleDate` / `FlexibleDatetime` are type aliases (not VOs) that use `BeforeValidator(parse_date/parse_datetime)` backed by `pd.to_datetime` — they handle ISO, slash, and compressed date strings.

`PriceVerificationError` is a rich exception that carries the original market data for structured error reporting downstream.

### `interfaces.py` — DataSource protocol

Defines the `DataSource` `Protocol` with four methods: `search`, `resolve`, `history`, `get_price`, and `validate`. All downstream data-provider packages implement this protocol. New methods added here must be added to every implementation.

### `cli_models.py` — CLI adapter layer

Built on top of `pydantic-settings` `CliSettingsSource`. Contains:

- **Metavar classes** (`SYMBOL`, `ISIN`, `DATE`, `PRICE`, …): bare `str`/`float`/`int` subclasses whose `__qualname__` becomes the argparse metavar in help output. They implement `__get_pydantic_core_schema__` so Pydantic still treats them as the primitive type.
- **`GlobalArgs`**: base model with `-v` / `-vv` / `--format` / `--schema` shared across all commands.
- **`SearchArgs` / `HistoryArgs`**: concrete command models that compose `GlobalArgs`.
- **`PatchedCliSettingsSource`**: subclasses `CliSettingsSource` to (1) strip `(default: …)` noise from help text, (2) remap `--v`/`--vv` to `-v`/`-vv` short flags, and (3) wire `--schema` to a `PrintSchemaAction` that exits after printing the JSON schema, bypassing required-argument validation.

### Public API (`__init__.py`)

Everything meant for downstream consumers is re-exported from the top-level package. When adding a new public symbol, add it to both `__init__.py` imports and `__all__`.

## Key conventions

- Value Objects use the Namespace Pattern (`VO.Input`) — never widen field types with raw `str` when a VO exists.
- `FlexibleDate`/`FlexibleDatetime` are the only coercing date types; use them at model boundaries, not inside internal logic.
- `PatchedCliSettingsSource` must be used (not the bare `CliSettingsSource`) in any CLI built on this package to preserve consistent flag behavior.
- Ruff line length is 100; target is Python 3.10 (`from __future__ import annotations` is used throughout).
