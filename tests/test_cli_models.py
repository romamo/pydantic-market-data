import argparse
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import TypeAdapter
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
from pydantic_market_data.models import HistoryPeriod


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

_FIXTURE = Path(__file__).parent / "fixtures" / "cli_args_v0_4_1.json"
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
def test_cli_args_schema_unchanged_since_v0_4_1(model):
    frozen = _frozen()[model.__name__]
    # json.dumps keeps key order, so property order, title, description, alias all count
    assert json.dumps(model.model_json_schema()) == json.dumps(frozen["schema"])
    assert list(model.model_fields) == frozen["fields"]
    assert list(model.model_fields)[:4] == ["v", "vv", "format", "print_schema"]


@pytest.mark.parametrize("model", [SearchArgs, HistoryArgs])
def test_cli_args_parser_unchanged_since_v0_4_1(model):
    structure = _cli_parser_structure(model)
    assert structure == _frozen()["parser"][model.__name__]
    option_strings = [action["option_strings"] for action in structure]
    for flags in (["-v", "--verbose"], ["-vv", "--debug"], ["--format"], ["--schema"]):
        assert flags in option_strings
    schema_action = next(a for a in structure if a["option_strings"] == ["--schema"])
    assert schema_action["action"] == "PrintSchemaAction"


@pytest.mark.parametrize(
    ("query_model", "cli_model"),
    [(SecurityQueryArgs, SearchArgs), (HistoryQueryArgs, HistoryArgs)],
)
def test_query_args_are_domain_only(query_model, cli_model):
    schema = query_model.model_json_schema()
    assert _CLI_ONLY_KEYS.isdisjoint(schema["properties"])
    assert _CLI_ONLY_KEYS.isdisjoint(query_model.model_fields)
    # Same domain fields, in the same order, as the CLI model minus the GlobalArgs fields
    assert list(query_model.model_fields) == list(cli_model.model_fields)[4:]
    assert issubclass(cli_model, query_model)
    assert issubclass(cli_model, GlobalArgs)
    assert not issubclass(query_model, GlobalArgs)
    assert query_model.model_config == cli_model.model_config


@pytest.mark.parametrize("model", [SecurityQueryArgs, HistoryQueryArgs])
def test_query_args_cli_has_no_framework_flags(model):
    flags = {f for action in _cli_parser_structure(model) for f in action["option_strings"]}
    assert "--symbol" in flags
    assert flags.isdisjoint({"-v", "--verbose", "-vv", "--debug", "--format", "--schema"})


def test_query_args_exported_from_package():
    assert pmd.SecurityQueryArgs is SecurityQueryArgs
    assert pmd.HistoryQueryArgs is HistoryQueryArgs
    assert {"SecurityQueryArgs", "HistoryQueryArgs"} <= set(pmd.__all__)
