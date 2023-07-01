"""Execute tests for the `pyspry.nested_dict` module."""
from __future__ import annotations

# stdlib
from typing import Any

# local
from pyspry.nested_dict import NestedDict


def test_nested_dict_keys(config: dict[str, Any]) -> None:
    """Verify the nested-structure-traversing setting has been consumed."""
    nested_dict = NestedDict(config)
    assert "APP_NAME_ATTR_B_K" in list(nested_dict.keys())
    assert "APP_NAME" not in list(nested_dict.keys())
