import argparse
import json
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import TypeAdapter, ValidationError
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
from pydantic_market_data.models import AssetClass, HistoryPeriod


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


@pytest.mark.parametrize("model", _QUERY_MODELS)
@pytest.mark.parametrize("raw", ["", "nan", "NaT"])
def test_date_rejects_empty_and_nat_with_validation_error(model, raw):
    # pd.to_datetime returns NaT for these; NaT.date() raised a raw TypeError
    with pytest.raises(ValidationError, match="Invalid date"):
        model(date=raw)


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


def test_schema_flag_prints_and_exits_with_kebab_default(capsys):
    cli = _cli_class(SearchArgs, settings_first=False)
    with pytest.raises(SystemExit) as exc:
        PatchedCliSettingsSource(cli, cli_parse_args=["--schema"])
    assert exc.value.code == 0
    assert "asset_class" in json.loads(capsys.readouterr().out)["properties"]
