import json
from unittest.mock import MagicMock, patch

from pydantic import TypeAdapter

from pydantic_market_data.cli_models import (
    CC,
    CLASS,
    CURR,
    DATE,
    EXCHANGE,
    FORMAT,
    ISIN,
    LEVEL,
    NAME,
    PATH,
    PATHS,
    PERIOD,
    PRICE,
    SYMBOL,
    GlobalArgs,
    HistoryArgs,
    PatchedCliSettingsSource,
    SearchArgs,
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
    assert TypeAdapter(LEVEL).json_schema() == {"type": "integer"}

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
    assert args.limit == 100
    assert args.ticker is None


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

    # Verify that --vv was patched to also include -vv
    mock_add_argument.assert_any_call(
        root_parser,
        "--vv",
        "-vv",
        dest="vv",
        default="==SUPPRESS==",
        help="Debug output (DEBUG level)",
        required=False,
        action="store_true",
    )
    # Verify that -v was used (pydantic-settings uses -v for single-char alias)
    mock_add_argument.assert_any_call(
        root_parser,
        "-v",
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
