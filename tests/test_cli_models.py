import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date
from enum import IntEnum
from pathlib import Path
from typing import Literal
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError
from pydantic_settings import BaseSettings

import pydantic_market_data as pmd
from pydantic_market_data.cli_models import (
    CC,
    CLASS,
    CURR,
    DATE,
    EXCHANGE,
    FORMAT,
    ISIN,
    LIMIT,
    NAME,
    PATH,
    PATHS,
    PERIOD,
    PRICE,
    SYMBOL,
    GlobalArgs,
    HistoryArgs,
    HistoryQueryArgs,
    PatchedCliSettingsSource,
    SearchArgs,
    SecurityQueryArgs,
)
from pydantic_market_data.models import AssetClass, HistoryInterval, HistoryPeriod


def test_custom_types_schema():
    """Verify that custom types return the correct core schema."""
    assert TypeAdapter(SYMBOL).json_schema() == {"type": "string"}
    assert TypeAdapter(ISIN).json_schema() == {"type": "string"}
    assert TypeAdapter(NAME).json_schema() == {"type": "string"}
    assert TypeAdapter(EXCHANGE).json_schema() == {"type": "string"}
    assert TypeAdapter(CC).json_schema() == {"type": "string"}
    assert TypeAdapter(CLASS).json_schema() == {"type": "string"}
    assert TypeAdapter(DATE).json_schema() == {"type": "string"}
    assert TypeAdapter(PERIOD).json_schema() == {"type": "string"}
    assert TypeAdapter(FORMAT).json_schema() == {"type": "string"}
    assert TypeAdapter(PATH).json_schema() == {"type": "string"}
    assert TypeAdapter(PATHS).json_schema() == {"type": "string"}
    assert TypeAdapter(PRICE).json_schema() == {"type": "number"}
    assert TypeAdapter(LIMIT).json_schema() == {"type": "integer"}

    # CURR should return the Currency enum schema
    curr_schema = TypeAdapter(CURR).json_schema()
    assert "enum" in curr_schema or "$ref" in curr_schema


def test_global_args_defaults():
    args = GlobalArgs()
    assert args.v is False
    assert args.vv is False
    assert args.format == "text"
    assert args.print_schema is False


def test_search_args_defaults():
    args = SearchArgs()
    assert args.limit == 1
    assert args.symbol is None


def test_history_args_defaults():
    args = HistoryArgs()
    assert args.period == HistoryPeriod.MO1


def test_patched_cli_settings_source_help_format():
    source = PatchedCliSettingsSource(GlobalArgs)
    field_info = MagicMock()
    # Mock the return value of super()._help_format to return a string
    with patch(
        "pydantic_settings.CliSettingsSource._help_format",
        return_value="Standard help (default: 'text')",
    ):
        formatted = source._help_format("format", field_info, "text", False)
        assert "(default: 'text')" not in formatted
        assert "Standard help" in formatted


@patch("argparse.ArgumentParser.add_argument")
def test_patched_cli_settings_source_connect_root_parser(mock_add_argument):
    source = PatchedCliSettingsSource(GlobalArgs)
    root_parser = MagicMock()
    root_parser.prefix_chars = "-"

    source._connect_root_parser(root_parser, None, add_argument_method=mock_add_argument)

    # Verify that --vv was patched to also include -vv and --debug
    mock_add_argument.assert_any_call(
        root_parser,
        "-vv",
        "--debug",
        dest="vv",
        default="==SUPPRESS==",
        help="Debug output (DEBUG level)",
        required=False,
        action="store_true",
    )
    # Verify that -v was patched to also include --verbose
    mock_add_argument.assert_any_call(
        root_parser,
        "-v",
        "--verbose",
        dest="v",
        default="==SUPPRESS==",
        help="Verbose output (INFO level)",
        required=False,
        action="store_true",
    )


def test_currency_coercion():
    """Test that CURR correctly handles Currency enum."""
    adapter = TypeAdapter(CURR)
    val = adapter.validate_python("USD")
    assert val == "USD"


def test_print_schema_action(capsys):
    """Verify that PrintSchemaAction outputs JSON and exits."""
    source = PatchedCliSettingsSource(GlobalArgs)

    mock_add = MagicMock()
    root_parser = MagicMock()
    root_parser.prefix_chars = "-"

    with patch("pydantic_settings.CliSettingsSource._connect_root_parser") as mock_super:
        # Call the method we want to test
        source._connect_root_parser(root_parser, None, add_argument_method=mock_add)

        # Capture the 'patched_add_argument' that was passed to super
        _, kwargs = mock_super.call_args
        patched_add_argument = kwargs.get("add_argument_method")
        assert patched_add_argument is not None, "patched_add_argument not passed to super"

        # Execute it with --schema. This should trigger the logic that sets
        # kwargs['action'] = PrintSchemaAction and then calls mock_add.
        patched_add_argument(root_parser, "--schema")

        # Verify mock_add was called and capture the action class
        assert mock_add.called, "mock_add was not called by patched_add_argument"
        call_args = mock_add.call_args
        captured_action_class = call_args.kwargs.get("action")

    assert captured_action_class is not None, f"PrintSchemaAction not found in {call_args.kwargs}"

    # Instantiate and call the action
    action = captured_action_class(option_strings=["--schema"], dest="print_schema")
    parser = MagicMock()

    action(parser, MagicMock(), None)

    captured = capsys.readouterr()
    schema_output = json.loads(captured.out)
    assert schema_output["title"] == "GlobalArgs"
    parser.exit.assert_called_once()


# --- Issue #1: domain-only query models -------------------------------------------------

_FIXTURE = Path(__file__).parent / "fixtures" / "cli_args_v0_6_0.json"
_CLI_ONLY_KEYS = {"v", "vv", "format", "schema", "print_schema"}


def _frozen() -> dict:
    return json.loads(_FIXTURE.read_text())


def _cli_parser_structure(model: type) -> list[dict]:
    """The argparse actions a PatchedCliSettingsSource CLI over `model` registers, in order.

    Compared structurally because rendered --help differs across Python versions
    ("-v, --verbose bool" on 3.13+, "-v bool, --verbose bool" on 3.10) and terminal widths.
    """

    class Cli(model, BaseSettings):  # type: ignore[misc, valid-type]
        pass

    parser = PatchedCliSettingsSource(Cli, cli_prog_name="tool").root_parser
    return [
        {
            "option_strings": list(action.option_strings),
            "dest": action.dest,
            "metavar": action.metavar,
            "help": action.help,
            "action": type(action).__name__,
            "nargs": action.nargs,
            "default_suppressed": action.default == argparse.SUPPRESS,
        }
        for action in parser._actions
    ]


@pytest.mark.parametrize("model", [SearchArgs, HistoryArgs])
def test_cli_args_schema_unchanged_since_v0_6_0(model):
    frozen = _frozen()[model.__name__]
    # json.dumps keeps key order, so property order, title, description, alias all count
    assert json.dumps(model.model_json_schema()) == json.dumps(frozen["schema"])
    assert list(model.model_fields) == frozen["fields"]
    assert list(model.model_fields)[:4] == ["v", "vv", "format", "print_schema"]


@pytest.mark.parametrize("model", [SearchArgs, HistoryArgs])
def test_cli_args_parser_unchanged_since_v0_6_0(model):
    structure = _cli_parser_structure(model)
    assert structure == _frozen()["parser"][model.__name__]
    option_strings = [action["option_strings"] for action in structure]
    for flags in (["-v", "--verbose"], ["-vv", "--debug"], ["--format"], ["--schema"]):
        assert flags in option_strings
    schema_action = next(a for a in structure if a["option_strings"] == ["--schema"])
    assert schema_action["action"] == "PrintSchemaAction"


@pytest.mark.parametrize(
    ("query_model", "cli_model", "cli_extra"),
    [(SecurityQueryArgs, SearchArgs, ["limit"]), (HistoryQueryArgs, HistoryArgs, [])],
)
def test_query_args_are_domain_only(query_model, cli_model, cli_extra):
    schema = query_model.model_json_schema()
    assert _CLI_ONLY_KEYS.isdisjoint(schema["properties"])
    assert _CLI_ONLY_KEYS.isdisjoint(query_model.model_fields)
    # Same domain fields, in the same order, as the CLI model minus the GlobalArgs fields
    # and the CLI model's own trailing options
    assert list(query_model.model_fields) + cli_extra == list(cli_model.model_fields)[4:]
    assert issubclass(cli_model, query_model)
    assert issubclass(cli_model, GlobalArgs)
    assert not issubclass(query_model, GlobalArgs)
    assert query_model.model_config == cli_model.model_config


@pytest.mark.parametrize("model", [SecurityQueryArgs, HistoryQueryArgs])
def test_query_args_cli_has_no_framework_flags(model):
    flags = {f for action in _cli_parser_structure(model) for f in action["option_strings"]}
    assert "--symbol" in flags
    assert flags.isdisjoint({"-v", "--verbose", "-vv", "--debug", "--format", "--schema"})


def test_security_query_args_has_no_limit():
    # --limit is a paging option owned by list-command frameworks (#5)
    assert "limit" not in SecurityQueryArgs.model_fields
    assert "limit" not in SecurityQueryArgs.model_json_schema()["properties"]
    flags = {f for a in _cli_parser_structure(SecurityQueryArgs) for f in a["option_strings"]}
    assert "--limit" not in flags


def test_search_args_keeps_limit_last():
    assert list(SearchArgs.model_fields)[-1] == "limit"
    assert SearchArgs.model_fields["limit"].default == 1
    flags = [a["option_strings"] for a in _cli_parser_structure(SearchArgs)]
    assert flags[-1] == ["--limit"]
    assert SearchArgs.model_validate({"limit": 5}).limit == 5


def test_query_args_exported_from_package():
    assert pmd.SecurityQueryArgs is SecurityQueryArgs
    assert pmd.HistoryQueryArgs is HistoryQueryArgs
    assert {"SecurityQueryArgs", "HistoryQueryArgs"} <= set(pmd.__all__)


# --- Issue #6: typed asset_class and date ------------------------------------------------

_QUERY_MODELS = [SecurityQueryArgs, HistoryQueryArgs, SearchArgs, HistoryArgs]


@pytest.mark.parametrize("model", [SecurityQueryArgs, SearchArgs])
def test_asset_class_schema_is_asset_class_enum(model):
    schema = model.model_json_schema()
    assert schema["properties"]["asset_class"]["anyOf"] == [
        {"$ref": "#/$defs/AssetClass"},
        {"type": "null"},
    ]
    assert schema["$defs"]["AssetClass"]["enum"] == [c.value for c in AssetClass]


@pytest.mark.parametrize("model", _QUERY_MODELS)
def test_date_schema_has_date_format(model):
    assert model.model_json_schema()["properties"]["date"]["anyOf"] == [
        {"format": "date", "type": "string"},
        {"type": "null"},
    ]


@pytest.mark.parametrize("raw", ["equity", "Equity", "EQUITY", AssetClass.EQUITY])
def test_asset_class_is_case_insensitive(raw):
    assert SecurityQueryArgs(asset_class=raw).asset_class is AssetClass.EQUITY


@pytest.mark.parametrize("model", [SecurityQueryArgs, SearchArgs])
def test_asset_class_contract_schema_lowercase_python_any_case(model):
    # Issue #19: the schema advertises lowercase values only (schema-driven CLIs reject
    # "Equity"), while model_validate still folds case for Python callers
    enum = model.model_json_schema()["$defs"]["AssetClass"]["enum"]
    assert enum == [c.value for c in AssetClass]
    assert all(value == value.lower() for value in enum)
    for raw in ("equity", "Equity", "EQUITY"):
        assert model.model_validate({"asset_class": raw}).asset_class is AssetClass.EQUITY


@pytest.mark.parametrize("raw", ["stock", "", 1])
def test_asset_class_rejects_unknown(raw):
    with pytest.raises(ValidationError):
        SecurityQueryArgs(asset_class=raw)


@pytest.mark.parametrize("model", _QUERY_MODELS)
@pytest.mark.parametrize("raw", ["2024-01-15", "2024/01/15", "20240115", date(2024, 1, 15)])
def test_date_accepts_flexible_formats(model, raw):
    assert model(date=raw).date == date(2024, 1, 15)


@pytest.mark.parametrize("model", _QUERY_MODELS)
def test_date_rejects_invalid(model):
    with pytest.raises(ValidationError, match="month must be in 1..12"):
        model(date="2024-13-01")


@pytest.mark.parametrize("model", [SearchArgs, SecurityQueryArgs])
def test_cli_parses_typed_asset_class_and_date(model):
    class Cli(model, BaseSettings):  # type: ignore[misc, valid-type]
        pass

    argv = ["--asset-class", "Equity", "--date", "2024/01/15"]
    args = Cli.model_validate(PatchedCliSettingsSource(Cli, cli_parse_args=argv)())
    assert args.asset_class is AssetClass.EQUITY
    assert args.date == date(2024, 1, 15)


_ASSET_CLASS_CHOICES = "{" + ",".join(c.value for c in AssetClass) + "}"


@pytest.mark.parametrize("model", [SearchArgs, SecurityQueryArgs])
@pytest.mark.parametrize("raw", ["Equity", "equity", "EQUITY"])
def test_cli_parses_any_case_asset_class_despite_lowercase_help(model, raw):
    # Issue #19: --help lists lowercase values, but argparse has no `choices` to reject
    # mixed case, so the value reaches pydantic's case-folding validator
    class Cli(model, BaseSettings):  # type: ignore[misc, valid-type]
        pass

    source = PatchedCliSettingsSource(Cli, cli_parse_args=["--asset-class", raw])
    assert _action_by_dest(source, "asset_class").choices is None
    assert Cli.model_validate(source()).asset_class is AssetClass.EQUITY


@pytest.mark.parametrize("model", [SearchArgs, SecurityQueryArgs])
def test_cli_help_shows_lowercase_asset_class_choices(model):
    # Issue #19: help shows the lowercase values the JSON schema advertises, not member names
    class Cli(model, BaseSettings):  # type: ignore[misc, valid-type]
        pass

    source = PatchedCliSettingsSource(Cli, cli_prog_name="tool")
    assert _ASSET_CLASS_CHOICES == (
        "{equity,fixed_income,cash,commodity,real_estate,fx,crypto,derivative,alternative,index}"
    )
    assert _action_by_dest(source, "asset_class").metavar == _ASSET_CLASS_CHOICES
    help_text = re.sub(r"\s+", "", _strip_ansi(source.root_parser.format_help()))
    assert f"--asset-class{_ASSET_CLASS_CHOICES}" in help_text
    assert "EQUITY" not in help_text


# --- Issue #22: enum metavars show values, not member names ------------------------------

_PERIOD_CHOICES = "{1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max}"


@pytest.mark.parametrize("model", [HistoryArgs, HistoryQueryArgs])
def test_cli_help_shows_period_values(model):
    class Cli(model, BaseSettings):  # type: ignore[misc, valid-type]
        pass

    source = PatchedCliSettingsSource(Cli, cli_prog_name="tool")
    assert "{" + ",".join(p.value for p in HistoryPeriod) + "}" == _PERIOD_CHOICES
    assert _action_by_dest(source, "period").metavar == _PERIOD_CHOICES
    help_text = re.sub(r"\s+", "", _strip_ansi(source.root_parser.format_help()))
    assert f"--period{_PERIOD_CHOICES}" in help_text
    assert "MO1" not in help_text


@pytest.mark.parametrize("model", [HistoryArgs, HistoryQueryArgs])
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1d", HistoryPeriod.D1),
        ("D1", HistoryPeriod.D1),
        ("1mo", HistoryPeriod.MO1),
        ("MO1", HistoryPeriod.MO1),
        ("ytd", HistoryPeriod.YTD),
        ("YTD", HistoryPeriod.YTD),
    ],
)
def test_cli_parses_period_by_value_and_member_name(model, raw, expected):
    # Help change only: member names that parsed before #22 still parse
    class Cli(model, BaseSettings):  # type: ignore[misc, valid-type]
        pass

    source = PatchedCliSettingsSource(Cli, cli_parse_args=["--period", raw])
    assert _action_by_dest(source, "period").choices is None
    assert Cli.model_validate(source()).period is expected


def test_cli_rejects_unknown_period():
    class Cli(HistoryArgs, BaseSettings):
        pass

    with pytest.raises(ValidationError, match="1d"):
        Cli.model_validate(PatchedCliSettingsSource(Cli, cli_parse_args=["--period", "d1"])())


class _Level(IntEnum):
    LOW = 1
    HIGH = 2


class _EnumShapes(BaseModel):
    interval: HistoryInterval | None = None
    level: _Level = _Level.LOW
    mode: Literal["fast", "slow"] = "fast"


@pytest.mark.parametrize(
    ("hide_none", "interval"),
    [
        (True, "{1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo,3mo}"),
        (False, "{{1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo,3mo},null}"),
    ],
)
def test_any_enum_metavar_shows_values(hide_none, interval):
    # Optional enums, non-str enum values, and untouched Literal choices
    class Cli(_EnumShapes, BaseSettings):
        pass

    source = PatchedCliSettingsSource(Cli, cli_prog_name="tool", cli_hide_none_type=hide_none)
    assert _action_by_dest(source, "interval").metavar == interval
    assert _action_by_dest(source, "level").metavar == "{1,2}"
    assert _action_by_dest(source, "mode").metavar == "{fast,slow}"


def _action_by_dest(source: PatchedCliSettingsSource, dest: str) -> argparse.Action:
    return next(a for a in source.root_parser._actions if a.dest == dest)


@pytest.mark.parametrize("model", _QUERY_MODELS)
@pytest.mark.parametrize("raw", ["", "nan", "NaT"])
def test_date_rejects_empty_and_nat_with_validation_error(model, raw):
    # pd.to_datetime returns NaT for these; NaT.date() raised a raw TypeError
    with pytest.raises(ValidationError, match="Invalid date"):
        model(date=raw)


@pytest.mark.parametrize("model", _QUERY_MODELS)
@pytest.mark.parametrize(
    "raw",
    [
        "01/02/2025",  # ambiguous day/month: was read month-first as 2025-01-02
        "15/01/2025",
        "15.01.2025",
        "Jan 15 2025",
        "2024-01-15T10:00:00",
        "2025-01/15",
        " 2025-01-15",
    ],
)
def test_date_rejects_other_shapes(model, raw):
    # Issue #18: only YYYY-MM-DD, YYYY/MM/DD and YYYYMMDD strings are accepted
    with pytest.raises(ValidationError, match="expected YYYY-MM-DD, YYYY/MM/DD or YYYYMMDD"):
        model(date=raw)


@pytest.mark.parametrize("model", _QUERY_MODELS)
@pytest.mark.parametrize("raw", ["2024-02-30", "2024/02/30", "20240230"])
def test_date_rejects_impossible_day(model, raw):
    with pytest.raises(ValidationError, match="day"):  # wording differs by Python version
        model(date=raw)


@pytest.mark.parametrize("model", [SearchArgs, SecurityQueryArgs, HistoryQueryArgs])
def test_cli_rejects_ambiguous_date(model):
    class Cli(model, BaseSettings):  # type: ignore[misc, valid-type]
        pass

    argv = ["--date", "01/02/2025"]
    with pytest.raises(ValidationError, match="expected YYYY-MM-DD"):
        Cli.model_validate(PatchedCliSettingsSource(Cli, cli_parse_args=argv)())


# --- Issue #10: kebab-case flags by default -----------------------------------------------


def _cli_class(model: type, settings_first: bool) -> type[BaseSettings]:
    if settings_first:

        class CliSettingsFirst(BaseSettings, model):  # type: ignore[misc, valid-type]
            pass

        return CliSettingsFirst

    class CliModelFirst(model, BaseSettings):  # type: ignore[misc, valid-type]
        pass

    return CliModelFirst


def _option_strings(source: PatchedCliSettingsSource) -> list[str]:
    return [flag for action in source.root_parser._actions for flag in action.option_strings]


@pytest.mark.parametrize("model", [SearchArgs, HistoryArgs, SecurityQueryArgs, HistoryQueryArgs])
@pytest.mark.parametrize("settings_first", [False, True])
def test_patched_source_defaults_to_kebab_case(model, settings_first):
    cli = _cli_class(model, settings_first)
    source = PatchedCliSettingsSource(cli, cli_prog_name="tool")
    assert source.cli_kebab_case is True
    flags = _option_strings(source)
    assert "--symbol" in flags
    assert not [flag for flag in flags if "_" in flag]
    if "asset_class" in model.model_fields:
        assert "--asset-class" in flags


def test_model_first_cli_config_is_not_kebab():
    # Root cause of #10: BaseSettings' explicit cli_kebab_case=False wins the MRO config merge
    assert _cli_class(SearchArgs, settings_first=False).model_config["cli_kebab_case"] is False


@pytest.mark.parametrize("settings_first", [False, True])
def test_explicit_kebab_case_false_wins(settings_first):
    cli = _cli_class(SearchArgs, settings_first)
    source = PatchedCliSettingsSource(cli, cli_prog_name="tool", cli_kebab_case=False)
    assert source.cli_kebab_case is False
    flags = _option_strings(source)
    assert "--asset_class" in flags
    assert "--asset-class" not in flags


@pytest.mark.parametrize("settings_first", [False, True])
def test_cli_parses_kebab_asset_class_end_to_end(settings_first):
    cli = _cli_class(SearchArgs, settings_first)
    argv = ["--asset-class", "equity"]
    args = cli.model_validate(PatchedCliSettingsSource(cli, cli_parse_args=argv)())
    assert args.asset_class is AssetClass.EQUITY


@pytest.mark.parametrize("settings_first", [False, True])
def test_schema_flag_prints_and_exits(capsys, settings_first):
    cli = _cli_class(SearchArgs, settings_first)
    with pytest.raises(SystemExit) as exc:
        PatchedCliSettingsSource(cli, cli_parse_args=["--schema"])
    assert exc.value.code == 0
    assert "asset_class" in json.loads(capsys.readouterr().out)["properties"]


# --- Issue #13: toggle bool flags and hidden None type by default -------------------------


def _action(source: PatchedCliSettingsSource, flag: str) -> argparse.Action:
    return next(a for a in source.root_parser._actions if flag in a.option_strings)


_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    """Drop the colour codes argparse adds to help on Python 3.14+ when colour is forced."""
    return _ANSI_ESCAPE.sub("", text)


@pytest.mark.parametrize("model", [SearchArgs, HistoryArgs])
@pytest.mark.parametrize("settings_first", [False, True])
def test_patched_source_defaults_toggle_flags_and_hidden_none(model, settings_first):
    cli = _cli_class(model, settings_first)
    source = PatchedCliSettingsSource(cli, cli_prog_name="tool")
    assert source.cli_implicit_flags == "toggle"
    assert source.cli_hide_none_type is True
    assert _action(source, "--symbol").metavar == "SYMBOL"
    assert "--symbol SYMBOL" in _strip_ansi(source.root_parser.format_help())
    assert not [f for f in _option_strings(source) if f.startswith("--no-")]
    for flag, long_flag in (("-v", "--verbose"), ("-vv", "--debug")):
        action = _action(source, flag)
        assert action.option_strings == [flag, long_flag]
        assert action.nargs == 0


_FORCED_COLOUR_HELP = """
from pydantic_settings import BaseSettings
from pydantic_market_data.cli_models import PatchedCliSettingsSource, SearchArgs

class Cli(SearchArgs, BaseSettings):
    pass

print(PatchedCliSettingsSource(Cli, cli_prog_name="tool").root_parser.format_help())
"""


def test_help_metavar_survives_forced_colour():
    """Issue #14: forced colour on Python 3.14+ must not hide `--symbol SYMBOL` in help."""
    env = {k: v for k, v in os.environ.items() if k not in ("NO_COLOR", "PYTHON_COLORS")}
    result = subprocess.run(
        [sys.executable, "-c", _FORCED_COLOUR_HELP],
        env={**env, "FORCE_COLOR": "1"},
        capture_output=True,
        text=True,
        check=True,
    )
    if sys.version_info >= (3, 14):
        assert "\x1b[" in result.stdout
    assert "--symbol SYMBOL" in _strip_ansi(result.stdout)


@pytest.mark.parametrize("model", [SearchArgs, HistoryArgs])
@pytest.mark.parametrize("settings_first", [False, True])
@pytest.mark.parametrize("argv", [["-v", "-vv"], ["--verbose", "--debug"]])
def test_verbosity_flags_parse_without_value(model, settings_first, argv):
    cli = _cli_class(model, settings_first)
    args = cli.model_validate(
        PatchedCliSettingsSource(cli, cli_parse_args=[*argv, "--symbol", "AAPL"])()
    )
    assert args.v is True
    assert args.vv is True
    assert args.symbol == "AAPL"


@pytest.mark.parametrize("settings_first", [False, True])
def test_explicit_implicit_flags_and_hide_none_false_win(settings_first):
    cli = _cli_class(SearchArgs, settings_first)
    source = PatchedCliSettingsSource(
        cli, cli_prog_name="tool", cli_implicit_flags=False, cli_hide_none_type=False
    )
    assert _action(source, "--symbol").metavar == "{SYMBOL,null}"
    verbose = _action(source, "-v")
    assert verbose.metavar == "bool"
    assert verbose.nargs is None
    args = cli.model_validate(
        PatchedCliSettingsSource(
            cli, cli_parse_args=["-v", "true"], cli_implicit_flags=False, cli_hide_none_type=False
        )()
    )
    assert args.v is True


@pytest.mark.parametrize("settings_first", [False, True])
def test_positional_args_reach_the_parent_signature(settings_first):
    # CliSettingsSource takes cli_hide_none_type 5th and cli_implicit_flags 12th positionally
    cli = _cli_class(SearchArgs, settings_first)
    positional = ["tool", None, "null", False, None, None, None, None, None, None, False]
    source = PatchedCliSettingsSource(cli, *positional)
    assert source.cli_prog_name == "tool"
    assert source.cli_hide_none_type is False
    assert source.cli_implicit_flags is False
    assert source.cli_kebab_case is True
    assert _action(source, "--symbol").metavar == "{SYMBOL,null}"


def test_positional_none_still_gets_the_default():
    cli = _cli_class(SearchArgs, settings_first=False)
    source = PatchedCliSettingsSource(cli, "tool", None, "null", None)
    assert source.cli_hide_none_type is True
    assert _action(source, "--symbol").metavar == "SYMBOL"
