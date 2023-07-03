"""Define a `NestedDict` class designed for nested configuration settings."""
from __future__ import annotations

# stdlib
import logging
import sys
from collections.abc import MutableMapping
from typing import Any, Iterator, TypeVar

KT = TypeVar("KT")

logger = logging.getLogger(__name__)


# note: py3.8 handles these type definitions differently than 3.10
if sys.version_info.minor > 8:
    # stdlib
    from typing import KeysView, Mapping

    class NestedKeysView(KeysView[KT]):
        """Override `KeysView` to recurse through nesting.

        >>> v = NestedKeysView(
        ...     {
        ...       "A0": {"B00": {"C000": 1, "C001": 2}, "B01": {"C010": 3, "C011": 4}},
        ...       "A1": {"B10": {"C100": 5, "C101": 6}, "B11": {"C110": 7, "C111": 8}}
        ...     }
        ... )
        >>> list(v)
        ['A0', 'A0_B00', 'A0_B00_C000', 'A0_B00_C001', 'A0_B01', 'A0_B01_C010', 'A0_B01_C011', 'A1', 'A1_B10', 'A1_B10_C100', 'A1_B10_C101', 'A1_B11', 'A1_B11_C110', 'A1_B11_C111']
        """  # pylint: disable=line-too-long

        _mapping: Mapping[KT, Any]
        prefix: str
        sep: str

        def __init__(self, mapping: Mapping[KT, Any], prefix: str = "", sep: str = "_") -> None:
            """Prepend `prefix` to each key in the view, with a `sep` delimiter.

            Args:
                mapping (Mapping[KT, Any]): create a view of this mapping object's keys
                prefix (str): prepend this string to each key in the view; defaults to ""
                sep (str): join each layer of nested keys with this separator; defaults to "_".
            """
            self.sep = sep
            self.prefix = prefix
            super().__init__(mapping)

        def __iter__(self) -> Iterator[str]:  # type: ignore[override]
            """Override the parent class to return a string matching layers of nesting."""
            start = f"{self.prefix}{self.sep}" if self.prefix else ""
            for key, value in self._mapping.items():
                if hasattr(value, "items"):
                    yield f"{start}{key}"
                    yield from self.__class__(value, f"{start}{key}", self.sep)
                else:
                    yield f"{start}{key}"


# TODO: drop after support for 3.8 is dropped
else:  # pragma: no cover
    # stdlib
    from collections.abc import KeysView, Mapping  # pylint: disable=ungrouped-imports

    class NestedKeysView(KeysView):  # type: ignore[no-redef,type-arg]
        """Override `KeysView` to recurse through nesting.

        >>> v = NestedKeysView(
        ...     {
        ...       "A0": {"B00": {"C000": 1, "C001": 2}, "B01": {"C010": 3, "C011": 4}},
        ...       "A1": {"B10": {"C100": 5, "C101": 6}, "B11": {"C110": 7, "C111": 8}}
        ...     }
        ... )
        >>> list(v)
        ['A0', 'A0_B00', 'A0_B00_C000', 'A0_B00_C001', 'A0_B01', 'A0_B01_C010', 'A0_B01_C011', 'A1', 'A1_B10', 'A1_B10_C100', 'A1_B10_C101', 'A1_B11', 'A1_B11_C110', 'A1_B11_C111']
        """  # pylint: disable=line-too-long

        _mapping: Mapping  # type: ignore[type-arg]

        def __init__(self, mapping: Mapping, prefix: str = "", sep: str = "_") -> None:  # type: ignore[type-arg]
            """Prepend `prefix` to each key in the view, with a `sep` delimiter.

            Args:
                mapping (Mapping[KT, Any]): create a view of this mapping object's keys
                prefix (str): prepend this string to each key in the view; defaults to ""
                sep (str): join each layer of nested keys with this separator; defaults to "_".
            """
            self.sep = sep
            self.prefix = prefix
            super().__init__(mapping)

        def __iter__(self) -> Iterator[str]:
            """Override the parent class to return a string matching layers of nesting."""
            start = f"{self.prefix}{self.sep}" if self.prefix else ""
            for key, value in self._mapping.items():
                if hasattr(value, "items"):
                    yield f"{start}{key}"
                    yield from self.__class__(value, f"{start}{key}", self.sep)
                else:
                    yield f"{start}{key}"


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

    __data: dict[str, Any]
    __is_list: bool
    sep = "_"

    def __init__(self, *args: MutableMapping[str, Any] | list[Any], **kwargs: Any) -> None:
        """Similar to the `dict` signature, accept a single optional positional argument."""
        if len(args) > 1:
            raise TypeError(f"expected at most 1 argument, got {len(args)}")
        self.__is_list = False
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
        else:
            data_structure = {}

        self._ensure_structure(kwargs)
        data_structure.update(kwargs)

        self.__data = data_structure
        self.squash()

    def __contains__(self, key: Any) -> bool:
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

    def __getitem__(self, key: str) -> Any:
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

    def __ior__(self, other: Mapping[str, Any]) -> NestedDict:
        """Override settings in this object with settings from the specified object."""
        for key, value in other.items():
            self[key] = value
        return self

    def __iter__(self) -> Iterator[Any]:
        """Return an iterator from the internal data structure."""
        return iter(self.__data)

    def __len__(self) -> int:
        """Proxy the `__len__` method of the `__data` attribute."""
        return len(self.__data)

    def __or__(self, other: Mapping[str, Any]) -> NestedDict:
        """Override the bitwise `or` operator to support merging `NestedDict` objects.

        >>> ( NestedDict({"A": {"B": 0}}) | NestedDict({"A_B": 1}) ).serialize()
        {'A': {'B': 1}}
        """
        return NestedDict({**self.__data, **other})

    def __repr__(self) -> str:
        """Use a `str` representation similar to `dict`, but wrap it in the class name."""
        return f"{self.__class__.__name__}({repr(self.__data)})"

    def __ror__(self, other: MutableMapping[str, Any]) -> NestedDict:
        """Cast the other object to a `NestedDict` when needed.

        >>> {"A": 0, "B": 1} | NestedDict({"A": 2})
        NestedDict({'A': 2, 'B': 1})
        """
        return NestedDict(other) | self

    def __setitem__(self, name: str, value: Any) -> None:
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
    def _ensure_structure(cls, data: dict[Any, Any]) -> None:
        for key, maybe_nested in list(data.items()):
            if isinstance(maybe_nested, (dict, list)):
                data[key] = NestedDict(maybe_nested)

    def get_first_match(self, nested_name: str) -> Any:
        """Traverse nested settings to retrieve the value of `nested_name`.

        Args:
            nested_name (str): the key to break across the nested data structure

        Returns:
            Any: the value retrieved from this object or a nested object

        Raises:
            ValueError: `nested_name` does not correctly identify a key in this object
                or any of its child objects
        """
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

    def keys(self) -> KeysView[Any]:
        """Flatten the nested dictionary to collect the full list of keys.

        >>> example = NestedDict({"KEY": {"SUB": {"NAME": "test", "OTHER": 1}}})
        >>> list(example.keys())
        ['KEY', 'KEY_SUB', 'KEY_SUB_NAME', 'KEY_SUB_OTHER']
        """
        return NestedKeysView(self, sep=self.sep)

    @staticmethod
    def maybe_merge(incoming: Mapping[str, Any] | Any, target: MutableMapping[str, Any]) -> bool:
        """If the given objects are both `Mapping` subclasses, merge them.

        Args:
            incoming (Mapping[str, Any] | Any): test this object to verify it is a `Mapping`
            target (MutableMapping[str, Any]): update this `MutableMapping` with `incoming`

        Returns:
            bool: the two `Mapping` objects were merged
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

    def serialize(self, strip_prefix: str = "") -> dict[str, Any] | list[Any]:
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
