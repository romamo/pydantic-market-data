# Changelog

All notable changes to this project will be documented in this file.

## [0.1.14] - 2026-02-22

### Fixed
- Recovery release following PyPI name reuse error on v0.1.13. No functional changes from v0.1.13.

## [0.1.13] - 2026-02-22

### Added
- Dedicated `cli_models.py` with support for short flags (`-v`, `-vv`) and JSON schema printing.
- `Ticker`, `ISIN`, `Price`, and `CountryAlpha2` strict Value Objects.
- `PriceVerificationError` for detailed validation failures.
- Automatic country resolution from names to Alpha-2 codes during initialization.
- Strict-yet-flexible typing allowing primitives (strings/floats) in models during creation.

### Changed
- Refactored `Symbol` and `SecurityCriteria` to use new Value Objects and Input types.
- Updated `DataSource` protocol to use `TickerInput` and `PriceInput` for better DX.
- Enabled validation on assignment for `OHLCV` and `SecurityCriteria`.


## [0.1.11] - 2026-02-19

### Added
- `isin` field to `Symbol` model.

## [0.1.10] - 2026-02-19

### Added
- `exchange` field to `SecurityCriteria` for more precise resolution.

### Changed
- Updated internal dependencies.
- Improved docstrings in `interfaces.py`.

## [0.1.9] - 2026-02-14

### Changed
- Updated `requires-python` constraint to `>=3.10`.

## [0.1.8] - 2026-02-14

### Fixed
- Retired unnecessary files and cleaned up repository structure.

## [0.1.7] - 2026-02-09

### Changed
- Minor internal cleanups and formatting.
## [0.1.6] - 2026-02-09

### Added
- OSS release workflow configuration.
- Completed project structure with `src` layout.

### Changed
- Improved metadata in `pyproject.toml`.
