# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Changed (Breaking)
- `FlexibleDate` (and `parse_date`) now accepts only the strings `YYYY-MM-DD`, `YYYY/MM/DD` and `YYYYMMDD` (one separator, used twice), besides `date` and `datetime` objects; every other string raises `ValidationError` naming the accepted formats. Before, `pd.to_datetime` read ambiguous dates month-first (`01/02/2025` became 2025-01-02 silently, `15/01/2025` and `15.01.2025` parsed with a pandas warning on stderr) and accepted shapes such as `Jan 15 2025` and `2024-01-15T10:00:00`. Impossible dates such as `2024-02-30` are still rejected. This affects `PriceOnDate.date`, `SecurityQuery.price_on`, and `date` on `SecurityQueryArgs`, `HistoryQueryArgs`, `SearchArgs` and `HistoryArgs`; `PriceVerificationError(actual_date=...)` raises `ValueError` for the rejected strings. `FlexibleDatetime` is unchanged (#18)

## [0.6.1] - 2026-10-01

### Fixed
- The `--symbol SYMBOL` help test no longer fails when colour is forced (`FORCE_COLOR`) on Python 3.14, whose argparse colours `format_help()`: the test strips ANSI codes before matching, and a new test checks the help in a subprocess with `FORCE_COLOR=1` (#14)

## [0.6.0] - 2026-10-01

### Changed (Breaking)
- `SecurityQueryArgs` no longer has a `limit` field (`--limit`): it is a paging option, not a domain field, and clashed with the `--limit` that list-command frameworks register themselves. `limit` is now declared on `SearchArgs`, whose fields, JSON schema, and CLI help are unchanged; code that read `limit` from a `SecurityQueryArgs` subclass must declare it itself (#5)
- `SecurityQueryArgs.asset_class` is now `AssetClass | None` (was the `CLASS` str label) and accepts any letter case (`Equity`, `EQUITY`, `equity`); unknown values such as `stock` raise `ValidationError`. `date` on `SecurityQueryArgs` and `HistoryQueryArgs` is now `FlexibleDate | None` (`datetime.date`, was the `DATE` str label), accepting `2024-01-15`, `2024/01/15` and `20240115` and rejecting invalid dates. The JSON schema now carries the `AssetClass` enum and `"format": "date"`, so schema-driven CLIs can validate both. `SearchArgs` and `HistoryArgs` inherit the change; the `CLASS` and `DATE` classes stay exported. Compare `asset_class` as the enum (or `.value`, not `str(...)`) (#6)
- `PatchedCliSettingsSource` now defaults `cli_kebab_case=True`, `cli_implicit_flags="toggle"` and `cli_hide_none_type=True`, the settings the arg models declare. With `class Cli(SearchArgs, BaseSettings)`, pydantic's MRO config merge let BaseSettings' defaults override them. Such CLIs now get `--asset-class` (was `--asset_class`; dest stays `asset_class`), valueless `-v`/`-vv`/`--verbose`/`--debug` flags (was `-v bool`, which required a value), and `--symbol SYMBOL` in help (was `{SYMBOL,null}`). Pass any of the three to the source explicitly to keep the old behaviour (#10, #13)

### Fixed
- `FlexibleDate` now rejects empty, `nan`, and `NaT` strings with `ValidationError`; it raised a raw `TypeError` before (#6)
- README Python samples run against the current API: `SecurityQuery` replaces the removed `SecurityCriteria`, asset classes use lowercase `AssetClass` values (`"equity"`), and the CLI sample registers `search` as a subcommand that parses `-vv`. A new test executes every README Python block (#9)

## [0.5.0] - 2026-10-01

### Added
- `History.candles` JSON Schema now declares `"x-ordered": true` and the description "Candles in ascending date order", so schema-driven serializers keep candle order (#2)
- `SecurityQueryArgs` and `HistoryQueryArgs`: domain-only argument models with the fields of `SearchArgs` / `HistoryArgs` but none of the CLI-framework options (`-v`, `-vv`, `--format`, `--schema`), for frameworks that own those options themselves. `SearchArgs` and `HistoryArgs` now compose them with `GlobalArgs`; their fields, JSON schema, and CLI help are unchanged. Exported from the top-level package (#1)

### Changed (Breaking)
- `History` now rejects candles that are not in strictly ascending date order (descending, unsorted, or duplicate dates) and candles that mix timezone-aware and naive dates, raising `ValidationError` that names the offending index and both dates; candles are not sorted automatically (#2)

## [0.4.1] - 2026-05-09

### Changed
- `SecurityQuery.price_on` now accepts a single `PriceOnDate` (or a plain dict) in addition to a list; a single item is automatically wrapped in a list.

## [0.4.0] - 2026-05-09

### Added
- `AssetClass` enum with values: `equity`, `fixed_income`, `cash`, `commodity`, `real_estate`, `fx`, `crypto`, `derivative`, `alternative`, `index`. Exported from the top-level package.

### Changed (Breaking)
- `Security.asset_class` changed from `str | None` to `AssetClass | None`. Pass a valid `AssetClass` value (e.g. `"equity"`) instead of a free-form string.
- `SecurityQuery.asset_class` changed from `str | None` to `AssetClass | None`.
- `SecurityQuery.price_on` changed from `PriceOnDate | None` to `list[PriceOnDate] | None` to support multi-date price queries.

## [0.3.2] - 2026-05-08

### Added
- `price_tolerance: float = 0.10` parameter on `DataSource.validate()` — allows callers to control the accepted price deviation instead of relying on an implicit default.
- `security_type: str | None` field on `Security` for instrument-type classification (e.g. `"Common Stock"`, `"ETF"`).

## [0.3.1] - 2026-04-23

### Fixed
- **FIGI check digit algorithm**: The Luhn algorithm was incorrectly applied to the expanded individual-digit list instead of the character-value list. Letters were split into two digits (e.g. `S=28 → [2, 8]`) before Luhn processing, causing parity misalignment for FIGIs that mix digits and letters in certain positions. The fix applies Luhn directly to character values (0–35) and uses `val % 10 + val // 10` as the digit-sum contribution, matching the OMG FIGI standard. Real-world identifiers such as `BBG00KHY5S69` (Broadcom Inc) were incorrectly rejected before this fix.

### Chore
- Pinned `astral-sh/setup-uv` GitHub Action to `v8.1.0`.
- Updated GitHub Actions to Node.js 24-compatible versions.

## [0.3.0] - 2026-04-23

### Changed (Breaking)
- Renamed `SecurityCriteria` to `SecurityQuery`. No backward-compatibility alias.
- Removed `target_price: Price.Input | None` and `target_date: FlexibleDate | None` from `SecurityQuery`. Both fields are now expressed as a single `price_on: PriceOnDate | None` field.

### Added
- `PriceOnDate` model (`price: Price.Input`, `date: FlexibleDate`) — exported from the top-level package.
- `figi: FIGI.Input | None` field on `SecurityQuery` for resolving by Bloomberg Open FIGI.

## [0.2.1] - 2026-04-23

### Added
- `FIGI` Value Object with full format and Luhn check-digit validation, following the Namespace Pattern (`FIGI.Input`).
- `figi: FIGI.Input | None` field on `Security` for Bloomberg Open FIGI identifiers.

## [0.2.0] - 2026-04-14

### Changed (Breaking)
- **Symbol Migration**: Standardized naming to align with industrial standards.
    - Renamed `Ticker` (RootModel) to `Symbol`.
    - Renamed `Symbol` (BaseModel) to `Security`.
    - In `Security`: Renamed `ticker` field to `symbol`.
    - In `History`: Renamed `symbol` field to `security`.
    - In `SecurityCriteria`: Ensured `symbol` field uses `Symbol.Input`.
    - In `PriceVerificationError`: Renamed `ticker` field to `symbol`.
    - Updated `DataSource` protocol and CLI models to use `symbol` instead of `ticker`.

## [0.1.17] - 2026-04-04

### Fixed
- Added missing `asset_class` field to `SecurityCriteria` model (previously only available in `Symbol`).

## [0.1.16] - 2026-02-28

### Refactored
- Transition `PriceVerificationError` to use Value Objects (`Ticker`, `Price`) and improve string representation for better error reporting.

## [0.1.15] - 2026-02-25

### Changed
- Adopted the **Namespace Pattern** for strict-yet-flexible typing (e.g., `Ticker.Input` instead of `TickerInput`) across all models and interfaces to improve Developer Experience and Mypy compatibility.

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
