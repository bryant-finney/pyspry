"""Define the base `Settings` class."""
from __future__ import annotations

# stdlib
import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any, Iterable, Type

# third party
import yaml

# local
from pyspry.nested_dict import NestedDict

if TYPE_CHECKING:  # pragma: no cover
    try:
        # stdlib
        from typing import TypeAlias
    except ImportError:
        # third party
        from typing_extensions import TypeAlias

logger = logger = logging.getLogger(__name__)


class NullMeta(type):
    """Classes using this ``metaclass`` return themselves for every operation / interaction.

    >>> Null == None, Null is None
    (True, False)

    >>> for result in [
    ...     Null(),
    ...     Null[0],
    ...     Null["any-key"],
    ...     Null.any_attr,
    ...     Null().any_attr,
    ...     Null + 5,
    ...     Null - 5,
    ...     Null * 5,
    ...     Null / 5,
    ...     Null % 5,
    ...     5 + Null,
    ...     5 - Null,
    ...     5 * Null,
    ...     5 / Null,
    ...     5 % Null,
    ... ]:
    ...     assert result is Null, result

    >>> str(Null)
    'Null'

    >>> bool(Null)
    False

    # Null is always false-y
    >>> Null or "None"
    'None'
    """

    def _null_operator(cls, *__o: Any) -> NullMeta:
        return cls

    __add__ = _null_operator

    def __bool__(cls) -> bool:
        # noqa: D105  # docstring -> noise for this method
        return bool(None)

    def __call__(cls, *args: Any, **kwargs: Any) -> NullMeta:
        # noqa: D102  # docstring -> noise for this method
        return cls

    __div__ = _null_operator

    def __eq__(cls, __o: object) -> bool:
        """Check ``cls`` for equivalence, as well as ``None``."""
        return __o is cls or __o is None

    def __getattr__(cls, __name: str) -> NullMeta:
        """Unless `__name` starts with `_`, return the `NullMeta` class instance.

        The check for a `_` prefix allows Python's internal mechanics (such as the `__dict__`
        or `__doc__` attributes) to function correctly.
        """
        if __name.startswith("_"):
            return super().__getattribute__(__name)  # type: ignore[no-any-return]
        return cls._null_operator(__name)

    __getitem__ = _null_operator
    __mod__ = _null_operator
    __mul__ = _null_operator
    __or__ = _null_operator  # type: ignore[assignment]
    __radd__ = _null_operator
    __rmod__ = _null_operator
    __rmul__ = _null_operator
    __rsub__ = _null_operator
    __rtruediv__ = _null_operator
    __sub__ = _null_operator
    __truediv__ = _null_operator

    def __new__(cls: type, name: str, bases: tuple[type], dct: dict[str, Any]) -> Any:
        """Create new `class` instances from this `metaclass`."""
        return super().__new__(cls, name, bases, dct)  # type: ignore[misc]

    def __repr__(cls) -> str:
        # noqa: D105  # docstring -> noise for this method
        return "Null"


class Null(metaclass=NullMeta):
    """Define a class which returns itself for all interactions."""


@dataclass
class ModuleContainer:
    """Name module instances."""

    name: str
    module: ModuleType | None


NullType: TypeAlias = Type[Null]


class Settings(ModuleType):
    """Store settings from environment variables and a config file.

    # Usage

    >>> settings = Settings.load(config_path, prefix="APP_NAME")
    >>> settings.APP_NAME_EXAMPLE_PARAM
    'a string!'

    ## Environment Variables

    Monkeypatch an environment variable for this test:

    >>> getfixture("monkey_example_param")  # use an env var to override the above setting
    {'APP_NAME_EXAMPLE_PARAM': 'monkeypatched!'}

    Setting an environment variable (above) can override specific settings values:

    >>> settings = Settings.load(config_path, prefix="APP_NAME")
    >>> settings.APP_NAME_EXAMPLE_PARAM
    'monkeypatched!'

    The prefix specified on load is automatically added when accessing attributes:

    >>> settings.APP_NAME_EXAMPLE_PARAM == settings.EXAMPLE_PARAM
    True

    ## JSON Values

    Environment variables in JSON format are parsed:

    >>> list(settings.APP_NAME_ATTR_A)
    [1, 2, 3]

    >>> getfixture("monkey_attr_a")    # override an environment variable
    {'APP_NAME_ATTR_A': '[4, 5, 6]'}

    >>> settings = Settings.load(config_path, prefix="APP_NAME")    # and reload the settings
    >>> list(settings.APP_NAME_ATTR_A)
    [4, 5, 6]

    To list all settings, use the built-in `dir()` function:

    >>> dir(settings)
    ['ATTR_A', 'ATTR_A_0', 'ATTR_A_1', 'ATTR_A_2', 'ATTR_B', 'ATTR_B_K', 'EXAMPLE_PARAM']

    """  # noqa: F821

    __config: NestedDict

    prefix: str

    # the following property is set by the `Settings.bootstrap()` method and removed by
    # `Settings.restore()`
    module_container: ModuleContainer | NullType = Null

    def __init__(self, config: dict[str, Any], environ: dict[str, str], prefix: str) -> None:
        """Deserialize all JSON-encoded environment variables during initialization.

        Args:
            config (dict[str, Any]): this object was loaded from a JSON/YAML file
            environ (dict[str, Any]): override config settings with these environment variables
            prefix (str): insert / strip this prefix when needed
        """
        self.__config = NestedDict(config)
        env: dict[str, Any] = {}
        for key, value in environ.items():
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                # the value must just be a simple string
                parsed = value

            if isinstance(parsed, (dict, list)):
                env[key] = NestedDict(parsed)
            else:
                env[key] = parsed

        self.__config |= NestedDict(env)
        self.prefix = prefix

    def __contains__(self, obj: Any) -> bool:
        """Check the merged `NestedDict` config for a setting with the given name.

        Keys must be strings to avoid unexpected behavior.

        >>> settings = Settings({20: "oops", "20": "okay"}, environ={}, prefix="")
        >>> "20" in settings
        True
        >>> 20 in settings
        False
        """
        if not isinstance(obj, str):
            return False
        return self.maybe_add_prefix(obj) in self.__config

    def __dir__(self) -> Iterable[str]:
        """Return a set of the names of all settings provided by this object."""
        return {self.__config.maybe_strip(self.prefix, key) for key in self.__config.keys()}.union(
            self.__config.maybe_strip(self.prefix, key) for key in self.__config
        )

    def __getattr__(self, name: str) -> Any:
        """Prioritize retrieving values from environment variables, falling back to the file config.

        Args:
            name (str): the name of the setting to retrieve

        Returns:
            Any: the value of the setting
        """
        try:
            return self.__getattr_override(name)
        except (AttributeError, TypeError):
            return self.__getattr_base(name)

    def __getattr_base(self, name: str) -> Any:
        try:
            return super().__getattribute__(name)
        except AttributeError:
            pass

        try:
            return getattr(self.module_container.module, name)
        except AttributeError:
            pass

        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def __getattr_override(self, name: str) -> Any:
        attr_name = self.maybe_add_prefix(name)

        try:
            attr_val = self.__config[attr_name]
        except KeyError as e:
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{attr_name}'"
            ) from e

        return (
            attr_val.serialize(strip_prefix=self.prefix)
            if isinstance(attr_val, NestedDict)
            else attr_val
        )

    def bootstrap(self, module_name: str) -> ModuleType | None:
        """Store the given module object and bootstrap the import mechanic.

        This object will replace the named module in `sys.modules`.
        """
        logger.info("replacing module '%s' with self", module_name)
        try:
            replaced_module = sys.modules[module_name]
        except KeyError:
            replaced_module = None
        self.module_container = ModuleContainer(name=module_name, module=replaced_module)
        sys.modules[module_name] = self
        return replaced_module

    @classmethod
    def load(cls, file_path: Path, prefix: str | None = None) -> Settings:
        """Load the specified configuration file and environment variables.

        Args:
            file_path (Path): the path to the config file to load
            prefix (Optional[str]): if provided, parse all env variables containing this prefix

        Returns:
            Settings: the `Settings` object
        """
        with file_path.open("r", encoding="UTF-8") as f:
            config_data = {
                str(key): value
                for key, value in yaml.safe_load(f).items()
                if not prefix or str(key).startswith(f"{prefix}{NestedDict.sep}")
            }

        if prefix:
            environ = {
                key: value
                for key, value in os.environ.items()
                if key.startswith(f"{prefix}{NestedDict.sep}")
            }
        else:
            environ = {}

        return cls(config_data, environ, prefix or "")

    def maybe_add_prefix(self, name: str) -> str:
        """If the given name is missing the prefix configured for these settings, insert it.

        Args:
            name (str): the attribute / key name to massage

        Returns:
            str: the name with the prefix inserted `iff` the prefix was missing
        """
        if not name.startswith(self.prefix):
            return f"{self.prefix}{self.__config.sep}{name}"
        return name

    def restore(self) -> ModuleType | None:
        """Remove self from `sys.modules` and restore the module that was bootstrapped.

        When a module is bootstrapped, it is replaced by a `Settings` object:

            >>> type(sys.modules["pyspry.settings"])
            <class 'pyspry.base.Settings'>

        Calling the `.restore()` method reverts the bootstrapping:

            >>> mod = settings.restore()
            >>> type(sys.modules["pyspry.settings"])
            <class 'module'>

            >>> mod is sys.modules["pyspry.settings"]
            True
        """  # noqa: F821
        if self.module_container is Null:
            return None

        module_container: ModuleContainer = self.module_container  # type: ignore[assignment]

        module_name, module = module_container.name, module_container.module
        self.module_container = Null

        logger.info("restoring '%s' and removing self from `sys.modules`", module_name)

        if not module:
            del sys.modules[module_name]
        else:
            sys.modules[module_name] = module

        return module


logger.debug("successfully imported %s", __name__)
