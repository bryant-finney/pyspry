"""Define a `NestedDict` class designed for nested configuration settings."""
from __future__ import annotations

# stdlib
import logging
import typing
from collections.abc import Mapping, MutableMapping

# local
from pyspry.keysview import NestedKeysView

__all__ = ["NestedDict", "NestedKeyPair"]


logger = logging.getLogger(__name__)


class NestedKeyPair(typing.NamedTuple):
    """A pair of keys `NestedDict` keys separated at a layer of nesting.

    >>> d = NestedDict({"A": {"B": {"C": {"D": 0}}}})
    >>> nkp = NestedKeyPair("A_B", "C_D")
    >>> d[nkp.parents][nkp.children]
    0
    """

    parents: str
    children: str | None = None

    @classmethod
    def dedupe(cls, parents: str, children: str | None = None) -> NestedKeyPair:
        """Create a new `NestedKeyPair` object without duplication.

        >>> NestedKeyPair.dedupe("A_B_C_D", "A_B_C_D")
        NestedKeyPair(parents='A_B_C_D', children=None)
        """
        if parents == children:
            return cls(parents)
        return cls(parents, children)


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
        self, *args: typing.Mapping[str, typing.Any] | list[typing.Any], **kwargs: typing.Any
    ) -> None:
        """Similar to the `dict` signature, accept a single optional positional argument."""
        if len(args) > 1:  # pragma: no cover
            raise TypeError(f"expected at most 1 argument, got {len(args)}")
        self.__is_list = False
        structured_data: dict[str, typing.Any] = {}

        if args:
            data = args[0]
            operations: dict[type, tuple[typing.Callable[[typing.Any], typing.Any], bool]] = {
                dict: (self._ensure_structure, self.__is_list),
                list: (
                    lambda d: self._ensure_structure(dict(enumerate(d))),  # pyright: ignore
                    True,
                ),
                self.__class__: (dict, getattr(data, "is_list", False)),
            }

            for data_type, (restructure, is_list) in operations.items():
                if isinstance(data, data_type):
                    structured_data = restructure(data)
                    self.__is_list = is_list
                    break

        restructured = self._ensure_structure(kwargs)
        structured_data.update(restructured)

        self.__data = structured_data
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

    def __ior__(self, other: typing.Mapping[str, typing.Any] | list[typing.Any]) -> NestedDict:
        """Override settings in this object with settings from the specified object.

        >>> example = NestedDict({"KEY": {"SUB": {"NAME": "test", "OTHER": 99}}})
        >>> example |= NestedDict({"KEY_SUB_NAME": "test2"})
        >>> example.serialize()
        {'KEY': {'SUB': {'NAME': 'test2', 'OTHER': 99}}}

        >>> example = NestedDict(["A", "B", "C"])
        >>> example |= NestedDict(["D", "E"])
        >>> example.serialize()
        ['D', 'E']
        """
        converted = NestedDict(other)
        self.maybe_merge(converted, self)

        if converted.is_list:
            self._reduce(self, converted)
        return self

    def __iter__(self) -> typing.Iterator[typing.Any]:
        """Return an iterator from the internal data structure."""
        return iter(self.__data)

    def __len__(self) -> int:
        """Proxy the `__len__` method of the `__data` attribute."""
        return len(self.__data)

    def __or__(self, other: typing.Mapping[str, typing.Any] | list[typing.Any]) -> NestedDict:
        """Override the bitwise `or` operator to support merging `NestedDict` objects.

        >>> ( NestedDict({"A": {"B": 0}}) | {"A_B": 1} ).serialize()
        {'A': {'B': 1}}

        >>> NestedDict({"A": 0}) | [0, 1]
        Traceback (most recent call last):
        ...
        TypeError: cannot merge [0, 1] (list: True) with NestedDict({'A': 0}) (list: False)

        >>> NestedDict([0, {"A": 1}]) | [1, {"B": 2}]
        NestedDict({'0': 1, '1': NestedDict({'A': 1, 'B': 2})})
        """
        if self.is_list ^ (converted := NestedDict(other)).is_list:
            raise TypeError(
                f"cannot merge {other} (list: {converted.is_list}) with {self} (list: "
                f"{self.is_list})"
            )

        self.maybe_merge(converted, self)
        if converted.is_list:
            self._reduce(self, converted)
            return self

        return self

    def __repr__(self) -> str:
        """Use a `str` representation similar to `dict`, but wrap it in the class name."""
        return f"{self.__class__.__name__}({repr(self.__data)})"

    def __ror__(self, other: MutableMapping[str, typing.Any] | list[typing.Any]) -> NestedDict:
        """Cast the other object to a `NestedDict` when needed.

        >>> {"A": 0, "B": 1} | NestedDict({"A": 2})
        NestedDict({'A': 2, 'B': 1})

        >>> merged_lists = ["A", "B", "C"]  | NestedDict([1, 2])
        >>> merged_lists.serialize()
        [1, 2]
        """
        return NestedDict(other) | self

    def __setitem__(self, name: str, value: typing.Any) -> None:
        """Similar to `__getitem__`, traverse nesting at `NestedDict.sep` in the key."""
        for data_key, data_val in list(self.__data.items()):
            if data_key == name:
                self._merge_or_set(name, value, data_val)
                return

            if name.startswith(f"{data_key}{self.sep}"):
                one_level_down = {self.maybe_strip(data_key, name): value}
                if not self.maybe_merge(one_level_down, data_val):
                    continue
                self.__data.pop(name, None)
                return

        self.__data[name] = value

    @classmethod
    def _ensure_structure(
        cls, data: typing.Mapping[typing.Any, typing.Any]
    ) -> dict[str, typing.Any]:
        out: dict[str, typing.Any] = {}
        for key, maybe_nested in list(data.items()):
            k = str(key)
            if isinstance(maybe_nested, (dict, list)):
                out[k] = NestedDict(maybe_nested)  # pyright: ignore
            else:
                out[k] = maybe_nested
        return out

    def _merge_or_set(
        self,
        name: str,
        incoming: typing.Mapping[str, typing.Any],
        target: typing.MutableMapping[str, typing.Any],
    ) -> None:
        if not self.maybe_merge(incoming, target):
            self.__data[name] = incoming

    @staticmethod
    def _reduce(
        base: typing.MutableMapping[str, typing.Any],
        incoming: typing.Mapping[str, typing.Any],
    ) -> None:
        """Delete keys from `base` that are not present in `incoming`."""
        for key_to_remove in set(base).difference(incoming):
            del base[key_to_remove]

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
        for key, remainder in self.get_matches(nested_name):
            nested_obj = self.__data[key]
            if not remainder:
                return nested_obj

            try:
                return nested_obj[remainder]
            except (KeyError, TypeError):
                pass

        raise ValueError("no match found")

    def get_matches(self, nested_name: str) -> list[NestedKeyPair]:
        """Traverse nested settings to retrieve all values of `nested_name`.

        Args:
            nested_name (builtins.str): the key to break across the nested data structure

        Returns:
            list[`typing.Any`]: the values retrieved from this object or any of its child objects
        """
        return sorted(
            [
                NestedKeyPair.dedupe(key, self.maybe_strip(key, nested_name))
                for key in self.__data
                if str(nested_name).startswith(key)
            ],
            key=lambda match: len(match[0]) if match else 0,
        )

    @property
    def is_list(self) -> bool:
        """Return `True` if the internal data structure is a `list`.

        >>> NestedDict([1, 2, 3]).is_list
        True

        >>> NestedDict({"A": 0}).is_list
        False
        """
        return self.__is_list

    def keys(self) -> typing.KeysView[typing.Any]:
        """Flatten the nested dictionary to collect the full list of keys.

        >>> example = NestedDict({"KEY": {"SUB": {"NAME": "test", "OTHER": 1}}})
        >>> list(example.keys())
        ['KEY', 'KEY_SUB', 'KEY_SUB_NAME', 'KEY_SUB_OTHER']
        """
        return NestedKeysView(self, sep=self.sep)

    @classmethod
    def _maybe_merge(
        cls, key: str, val: typing.Any, target: MutableMapping[str, typing.Any]
    ) -> None:
        if not cls.maybe_merge(val, target[key]):
            target[key] = val
        elif hasattr(target[key], "is_list") and target[key].is_list:
            cls._reduce(target[key], val)

    @classmethod
    def maybe_merge(
        cls,
        incoming: Mapping[str, typing.Any] | typing.Any,
        target: MutableMapping[str, typing.Any],
    ) -> bool:
        """If the given objects are both `typing.Mapping` subclasses, merge them.

        Also check if the `target` object is an instance of this class. If it is, and if it's based
        on a list, reduce the result to remove list elements that are not present in `incoming`.

        >>> example = NestedDict({"key": [1, 2, 3], "other": "val"})
        >>> NestedDict.maybe_merge(NestedDict({"key": [4, 5]}), example)
        True
        >>> example.serialize()
        {'key': [4, 5], 'other': 'val'}

        Args:
            incoming (typing.Mapping[builtins.str, typing.Any] | typing.Any): test this object to
                verify it is a `typing.Mapping`
            target (typing.MutableMapping[builtins.str, typing.Any]): update this
                `typing.MutableMapping` with the `incoming` mapping

        Returns:
            builtins.bool: the two `typing.Mapping` objects were merged
        """
        if not hasattr(incoming, "items") or not incoming.items():
            return False

        for k, v in incoming.items():
            if k not in target:
                target[k] = v
                continue

            cls._maybe_merge(k, v, target)

        return True

    @classmethod
    def maybe_strip(cls, prefix: str, from_: str) -> str:
        """Remove the specified prefix from the given string (if present)."""
        return from_[len(prefix) + 1 :] if from_.startswith(f"{prefix}{cls.sep}") else from_

    def _serialize_dict(self, strip_prefix: str) -> dict[str, typing.Any]:
        """Serialize the internal data structure as a `dict`."""
        return {
            self.maybe_strip(strip_prefix, key): (
                value.serialize() if isinstance(value, self.__class__) else value
            )
            for key, value in self.__data.items()
        }

    def _serialize_list(self) -> list[typing.Any]:
        """Serialize the internal data structure as a `list`."""
        return [
            item.serialize() if isinstance(item, self.__class__) else item
            for item in self.__data.values()
        ]

    def serialize(self, strip_prefix: str = "") -> dict[str, typing.Any] | list[typing.Any]:
        """Convert the `NestedDict` back to a `dict` or `list`."""
        return self._serialize_list() if self.__is_list else self._serialize_dict(strip_prefix)

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
            self[key] = value


logger.debug("successfully imported %s", __name__)
