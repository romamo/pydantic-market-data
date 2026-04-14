# pydantic-market-data

Shared Pydantic models and interfaces for financial data sources. This project defines a standard contract (`DataSource`) and data structures (`OHLCV`, `Security`, `History`) to ensure interoperability between finance packages.

## Project Overview

- **Purpose**: Provide standardized data models and protocols for financial data retrieval and validation.
- **Core Technologies**:
    - [Pydantic v2](https://docs.pydantic.dev/latest/): Data validation and settings management.
    - [pydantic-settings](https://docs.pydantic.dev/latest/usage/pydantic_settings/): CLI argument parsing and configuration.
    - [Pandas](https://pandas.pydata.org/): For high-performance data structures in financial models.
    - [Hatchling](https://hatch.pypa.io/latest/): Build backend.
    - [uv](https://github.com/astral-sh/uv): Fast Python package management.
- **Key Components**:
    - `models.py`: Core financial entities (`Symbol`, `Security`, `OHLCV`, `History`, `Currency`, `ISIN`).
    - `interfaces.py`: `DataSource` Protocol defining `resolve`, `history`, and `search` methods.
    - `cli_models.py`: Specialized models for building professional CLIs with `pydantic-settings`, featuring cleaned-up help text, custom metavars, and verbosity flags (`-v`, `-vv`).

## Development Workflow

### Environment Setup
The project uses `uv` for dependency management.
```bash
# Install dependencies
uv sync
```

### Building and Running
```bash
# Build the package
uv build

# Install in editable mode
uv pip install -e .
```

### Testing and Quality
```bash
# Run tests
uv run pytest

# Run linting
uv run ruff check .

# Run type checking
uv run mypy src

# Run security audit
uv run bandit -r src/
```

## Coding Conventions

- **Type Safety**: Strictly typed with `mypy`. Use the custom types in `cli_models.py` (e.g., `SYMBOL`, `ISIN`, `DATE`) for CLI models to ensure proper help documentation.
- **Pydantic v2**: Always use Pydantic v2 features. Models should leverage `Annotated` and `BeforeValidator` where complex coercion is needed (see `FlexibleDate` in `models.py`).
- **Interfaces**: When implementing a new data provider, always adhere to the `DataSource` protocol in `interfaces.py`.
- **CLI Design**: Use `PatchedCliSettingsSource` from `cli_models.py` to ensure consistent flag behavior and clean help output.

## Key Files
- `src/pydantic_market_data/models.py`: The "source of truth" for financial data structures.
- `src/pydantic_market_data/interfaces.py`: Defines the interoperability contract.
- `src/pydantic_market_data/cli_models.py`: Infrastructure for building consistent CLI tools.
- `pyproject.toml`: Project metadata, dependencies, and tool configurations.
