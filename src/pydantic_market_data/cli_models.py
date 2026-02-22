import json
import re
from argparse import Action, ArgumentParser
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field, GetCoreSchemaHandler
from pydantic.fields import FieldInfo
from pydantic_core import core_schema
from pydantic_settings import CliSettingsSource, SettingsConfigDict

from .models import Currency, HistoryPeriod

# Custom types for better CLI help labels (metavars)
# We use classes instead of NewType because pydantic-settings uses __qualname__ for help text.
# We implement __get_pydantic_core_schema__ so Pydantic treats them as the base type.


class SYMBOL(str):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, _st: Any, _h: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.str_schema()


class ISIN(str):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, _st: Any, _h: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.str_schema()


class NAME(str):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, _st: Any, _h: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.str_schema()


class EXCHANGE(str):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, _st: Any, _h: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.str_schema()


class CURR(str):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, _st: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return handler.generate_schema(Currency)


class CC(str):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, _st: Any, _h: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.str_schema()


class CLASS(str):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, _st: Any, _h: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.str_schema()


class DATE(str):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, _st: Any, _h: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.str_schema()


class PRICE(float):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, _st: Any, _h: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.float_schema()


class LEVEL(int):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, _st: Any, _h: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.int_schema()


class PERIOD(str):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, _st: Any, _h: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.str_schema()


class FORMAT(str):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, _st: Any, _h: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.str_schema()


class PATH(str):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, _st: Any, _h: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.str_schema()


class PATHS(str):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, _st: Any, _h: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.str_schema()


class GlobalArgs(BaseModel):
    model_config = SettingsConfigDict(
        cli_kebab_case=True,
        cli_implicit_flags="toggle",
        cli_hide_none_type=True,
    )
    v: bool = Field(False, alias="v", description="Verbose output (INFO level)")
    vv: bool = Field(False, alias="vv", description="Debug output (DEBUG level)")
    format: FORMAT = Field(FORMAT("text"), description="Output format (text, json, yaml)")
    print_schema: bool = Field(
        False, alias="schema", description="Output the JSON schema of the CLI interface"
    )


class SearchArgs(GlobalArgs):
    """Lookup a ticker symbol"""

    ticker: SYMBOL | None = Field(None, description="Ticker symbol to search for")
    isin: ISIN | None = Field(None, description="ISIN code to search for")
    desc: NAME | None = Field(None, description="Security name or description")
    exchange: EXCHANGE | None = Field(None, description="Exchange code (e.g. US, L, GY)")
    currency: CURR | None = Field(None, description="Currency code (e.g. USD, EUR, GBP)")
    country: CC | None = Field(None, description="Two-letter country code")
    asset_class: CLASS | None = Field(None, description="Asset class (Equity, Commodity, etc.)")
    date: DATE | None = Field(None, description="Reference date for price/validation")
    price: PRICE | None = Field(None, description="Reference price for validation")
    limit: LEVEL = Field(LEVEL(100), description="Maximum number of results to return")


class HistoryArgs(GlobalArgs):
    """Fetch history and validate"""

    ticker: SYMBOL | None = Field(None, description="Ticker symbol")
    isin: ISIN | None = Field(None, description="ISIN code")
    desc: NAME | None = Field(None, description="Security description")
    exchange: EXCHANGE | None = Field(None, description="Exchange code")
    period: HistoryPeriod = Field(
        HistoryPeriod.MO1, description="Range of historical data (e.g. 1mo, 1y, max)"
    )
    date: DATE | None = Field(None, description="Specific date to validate price against")
    price: PRICE | None = Field(None, description="Expected price for validation")


class PatchedCliSettingsSource(CliSettingsSource):
    """Custom CLI settings source to refine help text and flags."""

    def _help_format(
        self, field_name: str, field_info: FieldInfo, model_default: Any, is_model_suppressed: bool
    ) -> str:
        _help = super()._help_format(field_name, field_info, model_default, is_model_suppressed)
        # Remove (default: ...) or (default factory: ...)
        _help = re.sub(r"\s*\(default:.*?\)", "", _help)
        _help = re.sub(r"\s*\(default factory:.*?\)", "", _help)
        return _help

    def _connect_root_parser(  # type: ignore[override]
        self,
        root_parser: Any,
        parse_args_method: Callable[..., Any] | None,
        add_argument_method: Callable[..., Any] | None = ArgumentParser.add_argument,
        **kwargs: Any,
    ) -> None:
        model = self.settings_cls

        class PrintSchemaAction(Action):
            # Using a nested class to capture 'model' closure or just passing it
            def __init__(self, *args, **akwargs):
                akwargs.pop("model", None)  # Clean up just in case
                super().__init__(*args, **akwargs, nargs=0)

            def __call__(self, parser, namespace, values, option_string=None):
                print(json.dumps(model.model_json_schema(), indent=2))
                parser.exit()

        def patched_add_argument(parser: Any, *args: Any, **pkwargs: Any) -> Any:
            new_args = list(args)
            # Support short flags in addition to long pydantic-settings flags
            if "--vv" in new_args and "-vv" not in new_args:
                new_args.append("-vv")
            if "--v" in new_args and "-v" not in new_args:
                new_args.append("-v")

            # Use custom action for schema to bypass required args
            if "--schema" in new_args:
                pkwargs["action"] = PrintSchemaAction

            return (add_argument_method or ArgumentParser.add_argument)(
                parser, *new_args, **pkwargs
            )

        super()._connect_root_parser(
            root_parser,
            parse_args_method,
            add_argument_method=patched_add_argument,
            **kwargs,
        )
