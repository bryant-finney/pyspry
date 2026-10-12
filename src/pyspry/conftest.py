"""Configure test execution for `doctest`."""

from __future__ import annotations

# stdlib
import sys
from pathlib import Path
from typing import Any

# third party
import pytest

# local
from pyspry import settings


@pytest.fixture(autouse=True)
def settings_doctest_namespace(
    config_path: Path, doctest_namespace: dict[str, Any]
) -> dict[str, Any]:
    """Add the path to a generated config file to the namespace exposed to `doctest` tests."""
    doctest_namespace["config_path"] = config_path
    doctest_namespace["settings"] = settings
    doctest_namespace["sys"] = sys
    return doctest_namespace
