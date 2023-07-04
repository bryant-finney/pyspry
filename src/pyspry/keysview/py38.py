"""Override the `collections.abc.KeysView` class for Python 3.8."""
# stdlib
from collections.abc import KeysView, Mapping
from typing import Iterator

# third party
from typing_extensions import TypeAlias

# pylint: disable=duplicate-code

KT: TypeAlias = str


class NestedKeysView(KeysView):  # type: ignore[type-arg]
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
