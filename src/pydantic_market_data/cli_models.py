import inspect
import json
import re
from argparse import Action, ArgumentParser
from collections.abc import Callable
from enum import Enum
from typing import Annotated, Any, Literal, TypeAlias, get_args, get_origin

from pydantic import BaseModel, BeforeValidator, Field, GetCoreSchemaHandler
from pydantic.fields import FieldInfo
from pydantic_core import core_schema
from pydantic_settings import BaseSettings, CliSettingsSource, SettingsConfigDict

from .models import AssetClass, Currency, FlexibleDate, HistoryPeriod


def _lower_str(v: Any) -> Any:
    return v.lower() if isinstance(v, str) else v


# AssetClass that accepts any letter case from Python callers ("Equity", "EQUITY" ->
# AssetClass.EQUITY). The JSON schema keeps the lowercase AssetClass enum, so schema-driven
# CLIs that validate against it accept lowercase values only (#19)
CaseInsensitiveAssetClass: TypeAlias = Annotated[AssetClass, BeforeValidator(_lower_str)]

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


class LIMIT(int):
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
    v: bool = Field(False, description="Verbose output (INFO level)")
    vv: bool = Field(False, description="Debug output (DEBUG level)")
    format: FORMAT = Field(FORMAT("text"), description="Output format (text, json, yaml)")
    print_schema: bool = Field(
        False, alias="schema", description="Output the JSON schema of the CLI interface"
    )


class SecurityQueryArgs(BaseModel):
    """Domain-only security lookup arguments, without CLI-framework options"""

    model_config = SettingsConfigDict(
        cli_kebab_case=True,
        cli_implicit_flags="toggle",
        cli_hide_none_type=True,
    )
    symbol: SYMBOL | None = Field(None, description="Security symbol to search for")
    isin: ISIN | None = Field(None, description="ISIN code to search for")
    desc: NAME | None = Field(None, description="Security name or description")
    exchange: EXCHANGE | None = Field(None, description="Exchange code (e.g. US, L, GY)")
    currency: CURR | None = Field(None, description="Currency code (e.g. USD, EUR, GBP)")
    country: CC | None = Field(None, description="Two-letter country code")
    asset_class: CaseInsensitiveAssetClass | None = Field(
        None, description="Asset class, lowercase: equity, commodity, etc."
    )
    date: FlexibleDate | None = Field(None, description="Reference date for price/validation")
    price: PRICE | None = Field(None, description="Reference price for validation")


class HistoryQueryArgs(BaseModel):
    """Domain-only history arguments, without CLI-framework options"""

    model_config = SettingsConfigDict(
        cli_kebab_case=True,
        cli_implicit_flags="toggle",
        cli_hide_none_type=True,
    )
    symbol: SYMBOL | None = Field(None, description="Security symbol")
    isin: ISIN | None = Field(None, description="ISIN code")
    desc: NAME | None = Field(None, description="Security description")
    exchange: EXCHANGE | None = Field(None, description="Exchange code")
    period: HistoryPeriod = Field(
        HistoryPeriod.MO1, description="Range of historical data (e.g. 1mo, 1y, max)"
    )
    date: FlexibleDate | None = Field(None, description="Specific date to validate price against")
    price: PRICE | None = Field(None, description="Expected price for validation")


# GlobalArgs is listed last so its fields come first (pydantic collects fields in reverse MRO)
class SearchArgs(SecurityQueryArgs, GlobalArgs):
    """Lookup a security symbol"""

    # Paging option, not a domain field: frameworks that own --limit use SecurityQueryArgs
    limit: LIMIT = Field(LIMIT(1), description="Maximum number of results to return")


class HistoryArgs(HistoryQueryArgs, GlobalArgs):
    """Fetch history and validate"""


# CliSettingsSource.__init__ parameters after (self, settings_cls), in positional order
_PARENT_POSITIONAL = list(inspect.signature(CliSettingsSource.__init__).parameters)[2:]


class PatchedCliSettingsSource(CliSettingsSource):
    """Custom CLI settings source to refine help text and flags.

    Defaults three settings the arg models declare in their `model_config`, because pydantic
    merges `model_config` along the MRO: `class Cli(SearchArgs, BaseSettings)` picks up
    BaseSettings' explicit defaults and the models' own settings are lost.

    - `cli_kebab_case=True`: `--asset-class`, not `--asset_class`
    - `cli_implicit_flags="toggle"`: `-v` is a valueless flag, not `-v bool`
    - `cli_hide_none_type=True`: `--symbol SYMBOL`, not `--symbol {SYMBOL,null}`

    Pass any of them explicitly to override.
    """

    def __init__(
        self,
        settings_cls: type[BaseSettings],
        *args: Any,
        cli_kebab_case: bool | Literal["all", "no_enums"] | None = None,
        cli_implicit_flags: bool | Literal["dual", "toggle"] | None = None,
        cli_hide_none_type: bool | None = None,
        **kwargs: Any,
    ) -> None:
        positional = list(args)
        for name, value, default in (
            ("cli_kebab_case", cli_kebab_case, True),
            ("cli_implicit_flags", cli_implicit_flags, "toggle"),
            ("cli_hide_none_type", cli_hide_none_type, True),
        ):
            index = _PARENT_POSITIONAL.index(name)
            if index < len(positional):
                # Passed positionally: the parent signature still owns it
                if positional[index] is None:
                    positional[index] = default
                if value is not None:
                    kwargs[name] = value  # parent raises "multiple values", like CliSettingsSource
            else:
                kwargs[name] = default if value is None else value
        super().__init__(settings_cls, *positional, **kwargs)

    def _help_format(
        self, field_name: str, field_info: FieldInfo, model_default: Any, is_model_suppressed: bool
    ) -> str:
        _help = super()._help_format(field_name, field_info, model_default, is_model_suppressed)
        # Remove (default: ...) or (default factory: ...)
        _help = re.sub(r"\s*\(default:.*?\)", "", _help)
        _help = re.sub(r"\s*\(default factory:.*?\)", "", _help)
        return _help

    def _metavar_format_recurse(self, obj: Any) -> str:
        # Show enums by value ({equity,...}, {1d,5d,1mo,...}), the form the JSON schema
        # advertises, instead of pydantic-settings' member names ({EQUITY,...}, {D1,...})
        # (#19, #22). Unions recurse through here, so `HistoryPeriod | None` is covered too
        enum_type = get_args(obj)[0] if get_origin(obj) is Annotated else obj
        if isinstance(enum_type, type) and issubclass(enum_type, Enum):
            return "{" + ",".join(str(member.value) for member in enum_type) + "}"
        return str(super()._metavar_format_recurse(obj))

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
            # Support short and long flags for verbosity
            if any(arg in new_args for arg in ("--v", "-v", "--verbose")):
                new_args = ["-v", "--verbose"]

            if any(arg in new_args for arg in ("--vv", "-vv", "--debug")):
                new_args = ["-vv", "--debug"]

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
