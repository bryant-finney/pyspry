"""Define a `NestedDict` class designed for nested configuration settings."""
from __future__ import annotations

# stdlib
import logging
import typing
from collections.abc import Mapping, MutableMapping

# local
from pyspry.keysview import NestedKeysView

__all__ = ["NestedDict"]


logger = logging.getLogger(__name__)


class NestedDict(MutableMapping):  # type: ignore[type-arg]
    """Traverse nested data structures.

    # Usage

    >>> d = NestedDict(
    ...     {
    ...         "PARAM_A": "a",
    ...         "PARAM_B": 0,
    ...         "SUB": {"A": 1, "B": ["1", "2", "3"]},
    ...         "list": [{"A": 0, "B": 1}, {"a": 0, "b": 1}],
    ...         "deeply": {"nested": {"dict": {"ionary": {"zero": 0}}}},
    ...         "strings": ["should", "also", "work"]
    ...     }
    ... )

    Simple keys work just like standard dictionaries:

    >>> d["PARAM_A"], d["PARAM_B"]
    ('a', 0)

    Nested containers are converted to `NestedDict` objects:

    >>> d["SUB"]
    NestedDict({'A': 1, 'B': NestedDict({'0': '1', '1': '2', '2': '3'})})

    >>> d["SUB_B"]
    NestedDict({'0': '1', '1': '2', '2': '3'})

    Nested containers can be accessed by appending the nested key name to the parent key name:

    >>> d["SUB_A"] == d["SUB"]["A"]
    True

    >>> d["SUB_A"]
    1

    >>> d["deeply_nested_dict_ionary_zero"]
    0

    List indices can be accessed too:

    >>> d["SUB_B_0"], d["SUB_B_1"]
    ('1', '2')

    Similarly, the `in` operator also traverses nesting:

    >>> "SUB_B_0" in d
    True
    """

    __data: dict[str, typing.Any]
    __is_list: bool
    sep = "_"

    def __init__(
        self, *args: MutableMapping[str, typing.Any] | list[typing.Any], **kwargs: typing.Any
    ) -> None:
        """Similar to the `dict` signature, accept a single optional positional argument."""
        if len(args) > 1:
            raise TypeError(f"expected at most 1 argument, got {len(args)}")
        self.__is_list = False
        data_structure = {}

        if args:
            data = args[0]
            if isinstance(data, dict):
                self._ensure_structure(data)
                data_structure = data
            elif isinstance(data, list):
                self.__is_list = True
                data_structure = {
                    str(i_item): maybe_nested for i_item, maybe_nested in enumerate(data)
                }
                self._ensure_structure(data_structure)

        self._ensure_structure(kwargs)
        data_structure.update(kwargs)

        self.__data = data_structure
        self.squash()

    def __contains__(self, key: typing.Any) -> bool:
        """Check if `self.__data` provides the specified key.

        Also consider nesting when evaluating the condition, i.e.

        >>> example = NestedDict({"KEY": {"SUB": {"NAME": "test"}}})
        >>> "KEY_SUB" in example
        True
        >>> "KEY_SUB_NAME" in example
        True

        >>> "KEY_MISSING" in example
        False
        """
        if key in self.__data:
            return True
        for k, value in self.__data.items():
            if key.startswith(f"{k}{self.sep}") and self.maybe_strip(k, key) in value:
                return True
        return False

    def __delitem__(self, key: str) -> None:
        """Delete the object with the specified key from the internal data structure."""
        del self.__data[key]

    def __getitem__(self, key: str) -> typing.Any:
        """Traverse nesting according to the `NestedDict.sep` property."""
        try:
            return self.get_first_match(key)
        except ValueError:
            pass

        try:
            return self.__data[key]
        except KeyError:
            pass
        raise KeyError(key)

    def __ior__(self, other: typing.Mapping[str, typing.Any]) -> NestedDict:
        """Override settings in this object with settings from the specified object."""
        for key, value in other.items():
            self[key] = value
        return self

    def __iter__(self) -> typing.Iterator[typing.Any]:
        """Return an iterator from the internal data structure."""
        return iter(self.__data)

    def __len__(self) -> int:
        """Proxy the `__len__` method of the `__data` attribute."""
        return len(self.__data)

    def __or__(self, other: typing.Mapping[str, typing.Any]) -> NestedDict:
        """Override the bitwise `or` operator to support merging `NestedDict` objects.

        >>> ( NestedDict({"A": {"B": 0}}) | NestedDict({"A_B": 1}) ).serialize()
        {'A': {'B': 1}}
        """
        return NestedDict({**self.__data, **other})

    def __repr__(self) -> str:
        """Use a `str` representation similar to `dict`, but wrap it in the class name."""
        return f"{self.__class__.__name__}({repr(self.__data)})"

    def __ror__(self, other: MutableMapping[str, typing.Any]) -> NestedDict:
        """Cast the other object to a `NestedDict` when needed.

        >>> {"A": 0, "B": 1} | NestedDict({"A": 2})
        NestedDict({'A': 2, 'B': 1})
        """
        return NestedDict(other) | self

    def __setitem__(self, name: str, value: typing.Any) -> None:
        """Similar to `__getitem__`, traverse nesting at `NestedDict.sep` in the key."""
        for data_key, data_val in list(self.__data.items()):
            if data_key == name:
                if not self.maybe_merge(value, data_val):
                    self.__data[name] = value
                return

            if name.startswith(f"{data_key}{self.sep}"):
                one_level_down = {self.maybe_strip(data_key, name): value}
                if not self.maybe_merge(one_level_down, data_val):
                    continue
                self.__data.pop(name, None)
                return

        self.__data[name] = value

    @classmethod
    def _ensure_structure(cls, data: dict[typing.Any, typing.Any]) -> None:
        for key, maybe_nested in list(data.items()):
            if isinstance(maybe_nested, (dict, list)):
                data[key] = NestedDict(maybe_nested)

    def get_first_match(self, nested_name: str) -> typing.Any:
        """Traverse nested settings to retrieve the value of `nested_name`.

        Args:
            nested_name (builtins.str): the key to break across the nested data structure

        Returns:
            `typing.Any`: the value retrieved from this object or a nested object

        Raises:
            builtins.ValueError: `nested_name` does not correctly identify a key in this object
                or any of its child objects
        """  # noqa: DAR401, DAR402
        matching_keys = sorted(
            [
                (key, self.maybe_strip(key, nested_name))
                for key in self.__data
                if str(nested_name).startswith(key)
            ],
            key=lambda match: len(match[0]) if match else 0,
        )

        for key, remainder in matching_keys:
            nested_obj = self.__data[key]
            if key == remainder:
                return nested_obj

            try:
                return nested_obj[remainder]
            except (KeyError, TypeError):
                pass

        raise ValueError("no match found")

    def keys(self) -> typing.KeysView[typing.Any]:
        """Flatten the nested dictionary to collect the full list of keys.

        >>> example = NestedDict({"KEY": {"SUB": {"NAME": "test", "OTHER": 1}}})
        >>> list(example.keys())
        ['KEY', 'KEY_SUB', 'KEY_SUB_NAME', 'KEY_SUB_OTHER']
        """
        return NestedKeysView(self, sep=self.sep)

    @staticmethod
    def maybe_merge(
        incoming: Mapping[str, typing.Any] | typing.Any,
        target: MutableMapping[str, typing.Any],
    ) -> bool:
        """If the given objects are both `typing.Mapping` subclasses, merge them.

        Args:
            incoming (typing.Mapping[builtins.str, typing.Any] | typing.Any): test this object to
                verify it is a `typing.Mapping`
            target (typing.MutableMapping[builtins.str, typing.Any]): update this
                `typing.MutableMapping` with the `incoming` mapping

        Returns:
            builtins.bool: the two `typing.Mapping` objects were merged
        """
        if not hasattr(incoming, "items") or not hasattr(target, "items"):
            return False

        for k, v in incoming.items():
            target[k] = v
        return True

    @classmethod
    def maybe_strip(cls, prefix: str, from_: str) -> str:
        """Remove the specified prefix from the given string (if present)."""
        return from_[len(prefix) + 1 :] if from_.startswith(f"{prefix}{cls.sep}") else from_

    def serialize(self, strip_prefix: str = "") -> dict[str, typing.Any] | list[typing.Any]:
        """Convert the `NestedDict` back to a `dict` or `list`."""
        return (
            [
                item.serialize() if isinstance(item, self.__class__) else item
                for item in self.__data.values()
            ]
            if self.__is_list
            else {
                self.maybe_strip(strip_prefix, key): (
                    value.serialize() if isinstance(value, self.__class__) else value
                )
                for key, value in self.__data.items()
            }
        )

    def squash(self) -> None:
        """Collapse all nested keys in the given dictionary.

        >>> sample = {"A": {"B": {"C": 0}, "B_D": 2}, "A_THING": True, "A_B_C": 1, "N_KEYS": 0}
        >>> nested = NestedDict(sample)
        >>> nested.squash()
        >>> nested.serialize()
        {'A': {'B': {'C': 1, 'D': 2}, 'THING': True}, 'N_KEYS': 0}
        """
        for key, value in list(self.__data.items()):
            if isinstance(value, NestedDict):
                value.squash()
            self.__data.pop(key)
            try:
                self[key] = value
            except AttributeError:
                self.__data[key] = value


logger.debug("successfully imported %s", __name__)
