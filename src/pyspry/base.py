"""Define the base `Settings` class."""
from __future__ import annotations

# stdlib
import importlib
import importlib.util
import json
import logging
import os
import sys
import types
from importlib.machinery import ModuleSpec
from io import TextIOWrapper
from pathlib import Path
from typing import Any, Iterable

# third party
import yaml

# local
from pyspry.nested_dict import NestedDict

__all__ = ["Settings"]

logger = logging.getLogger(__name__)


class Settings:
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
    """Store the config file contents as a `NestedDict` object."""

    prefix: str
    """Only load settings whose names start with this prefix."""

    def __init__(
        self, config: dict[str, Any] | list[Any], environ: dict[str, str], prefix: str
    ) -> None:
        """Deserialize all JSON-encoded environment variables during initialization.

        Args:
            config (builtins.dict[builtins.str, typing.Any]): the values loaded from a JSON/YAML
                file
            environ (builtins.dict[builtins.str, builtins.str]): override config settings with these
                environment variables
            prefix (builtins.str): insert / strip this prefix when needed

        The `prefix` is automatically added when accessing attributes:

        >>> settings = Settings({"APP_NAME_EXAMPLE_PARAM": 0}, {}, prefix="APP_NAME")
        >>> settings.APP_NAME_EXAMPLE_PARAM == settings.EXAMPLE_PARAM == 0
        True
        """  # noqa: RST203
        self.__config = NestedDict(config)
        env: dict[str, Any] = {}
        for key, value in environ.items():
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                # the value must just be a simple string
                parsed = value

            if isinstance(parsed, (dict, list)):
                env[key] = NestedDict(parsed)  # pyright: ignore
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
        """Retrieve the setting from `self.__config`.

        Args:
            name (str): the name of the setting to retrieve

        Returns:
            `Any`: the value of the setting
        """
        try:
            return self.__getattr_override(name)
        except (AttributeError, TypeError):
            return super().__getattribute__(name)

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

    def __or__(self, other: Settings) -> Settings:
        """Merge the two `Settings` objects, with `other` taking precedence over `self`.

        >>> merged = Settings({"A": {"B": 1, "C": 2}}, {}, "") | Settings({"A": {"B": 2}}, {}, "")
        >>> merged.A_B == merged.A_C == 2
        True

        Lists cannot be merged:

            >>> Settings([1, 2, 3], {}, "") | {"A": {"B": 1}}
            Traceback (most recent call last):
            ...
            TypeError: cannot merge <pyspry.base.Settings object at ...> with {'A': {'B': 1}}
        """
        if self.__config.is_list or isinstance(other_config := other.config, list):
            raise TypeError(f"cannot merge {self} with {other}")
        merged = self.__config | other_config
        return Settings(merged.serialize(self.prefix), {}, self.prefix)

    @property
    def config(self) -> dict[str, Any] | list[Any]:
        """Return a copy of the serialized data structure.

        >>> s = Settings({"A": {"B": [1, 2, 3]}}, {}, "")
        >>> s.config
        {'A': {'B': [1, 2, 3]}}
        """
        return self.__config.serialize(self.prefix)

    @classmethod
    def load(cls, file_path: Path | str, prefix: str | None = None) -> Settings:
        """Load the specified configuration file and environment variables.

        Args:
            file_path (pathlib.Path | builtins.str): the path to the config file to load
            prefix (typing.Optional[builtins.str]): if provided, parse all env variables containing
                this prefix

        Returns:
            pyspry.base.Settings: the `Settings` object loaded from file with environment variable
                overrides
        """  # noqa: RST301
        with Path(file_path).open("r", encoding="UTF-8") as f:
            config_data = load_yaml(f, prefix)

        environ = load_env(prefix)

        return cls(config_data, environ, prefix or "")

    def maybe_add_prefix(self, name: str) -> str:
        """If the given name is missing the prefix configured for these settings, insert it.

        Args:
            name (builtins.str): the attribute / key name to massage

        Returns:
            builtins.str: the name with the prefix inserted `iff` the prefix was missing
        """
        if not name.startswith(self.prefix):
            return f"{self.prefix}{self.__config.sep}{name}"
        return name


class SettingsContainer(types.ModuleType):
    """Provide the machinery to create a `Settings` object on import.

    This class implements a
    [delegation pattern](https://medium.com/anymind-group/importance-of-delegation-in-python-20c3160c93ab)
    to proxy attributes of its `Settings` object:

      - `Settings` is responsible for accessing items in its `pyspry.NestedDict`
      - this class is responsible for instantiating the `Settings` object and interfacing with
        Python's import mechanisms
    """

    VARNAME_CONFIG_PATH = "PYSPRY_CONFIG_PATH"
    """The name of the environment variable identifying the path to the config file."""

    VARNAME_VAR_PREFIX = "PYSPRY_VAR_PREFIX"
    """The name of the environment variable identifying the prefix for environment variables."""

    __name__: str
    """The name of the module that has been bootstrapped by this object."""

    __spec__: ModuleSpec | None
    """The `ModuleSpec` object is used by `importlib` internals."""

    __settings: Settings
    """Store the `pyspry.Settings` object that was initialized from the config file and environment
    variables"""

    def __init__(self, module_name: str, spec: ModuleSpec | None, settings: Settings) -> None:
        # these properties are used by `importlib.reload()`
        self.__name__ = module_name
        self.__spec__ = spec

        self.__settings = settings

    def __contains__(self, obj: Any) -> bool:
        """Thin wrapper around `Settings.__contains__`."""
        return obj in self.__settings

    def __dir__(self) -> Iterable[str]:
        """Thin wrapper around `Settings.__dir__`."""
        return dir(self.__settings)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.__settings, name)

    def __getattribute__(self, name: str) -> Any:
        """Retrieve the setting from `self.__config`.

        Args:
            name (str): the name of the setting to retrieve

        Returns:
            `Any`: the value of the setting
        """
        return super().__getattribute__(name)

    def __repr__(self) -> str:
        return repr(self.__settings)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in self.__class__.__annotations__:
            super().__setattr__(name, value)
        else:
            setattr(self.__settings, name, value)

    def __str__(self) -> str:
        return yaml.dump(self.__settings.config, indent=2)

    @classmethod
    def bootstrap(cls, module_name: str) -> SettingsContainer:
        """Store the named module object, replacing it with `self` to bootstrap the import mechanic.

        This object will replace the named module in `sys.modules`.

        Args:
            module_name (builtins.str): the name of the module to replace

        Returns:
            typing.Optional[types.ModuleType]: the module object that was replaced, or `None` if the
                module wasn't already in `sys.modules`
        """
        if sys.modules.get(module_name):
            logger.info("replacing module '%s' with settings object", module_name)
            del sys.modules[module_name]

        fname = Path(os.environ.get(cls.VARNAME_CONFIG_PATH, "config.yml"))
        prefix = os.environ.get(cls.VARNAME_VAR_PREFIX, None)

        settings = Settings.load(fname, prefix)
        spec = importlib.util.find_spec(module_name)

        container = cls(module_name, spec, settings)
        sys.modules[module_name] = container

        return container


def load_env(prefix: str | None) -> dict[str, Any]:
    """Load the environment variables into a dictionary.

    Args:
        prefix (typing.Optional[builtins.str]): if provided, parse all env variables containing
            this prefix

    Returns:
        dict[builtins.str, typing.Any]: the deserialized environment variables
    """
    return (
        {
            key: value
            for key, value in os.environ.items()
            if key.startswith(f"{prefix}{NestedDict.sep}")
        }
        if prefix
        else {}
    )


def load_yaml(f_obj: TextIOWrapper, prefix: str | None) -> dict[str, Any]:
    """Load the YAML file from the given file object.

    Args:
        f_obj (io.TextIOWrapper): the file object to read
        prefix (builtins.str): if specified, filter keys to those starting with this prefix

    Returns:
        dict[builtins.str, typing.Any]: the deserialized YAML file
    """
    return {
        str(key): value
        for key, value in yaml.safe_load(f_obj).items()
        if not prefix or str(key).startswith(f"{prefix}{NestedDict.sep}")
    }


logger.debug("successfully imported %s", __name__)
