"""Reuse `pytest` configuration from the `pyspry` package."""

from __future__ import annotations

# stdlib
import importlib
from typing import TYPE_CHECKING, Iterator, TypeAlias, TypeVar

# third party
import pytest
from _pytest.config import Config
from _pytest.monkeypatch import MonkeyPatch

# local
from pyspry.base import Settings, SettingsContainer

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

if TYPE_CHECKING:
    imported_settings: Settings

T = TypeVar("T")
Yields: TypeAlias = Iterator[T]


def pytest_configure(config: Config) -> None:
    """Register the `setenv` marker with `pytest`."""
    config.addinivalue_line(
        "markers",
        "setenv: Set environment variables before initializing the `pyspry_settings` fixture.",
    )


@pytest.fixture()
def pyspry_settings(request: pytest.FixtureRequest, monkeypatch: MonkeyPatch) -> SettingsContainer:
    """Introspect the request context for environment variables to monkeypatch.

    Environment variables may be monkeypatched by adding a `setenv` marker to the test function:

    >>> import os
    >>> @pytest.mark.setenv(EXAMPLE_ENV_VAR="foo")
    ... def test_foo(pyspry_settings):
    ...     assert os.getenv("EXAMPLE_ENV_VAR") == "foo"
    """
    marker: pytest.Mark | None = request.node.get_closest_marker("setenv")
    if marker is not None:
        for name, value in marker.kwargs.items():
            monkeypatch.setenv(name, value)

    settings = importlib.import_module("pyspry.settings")  # type: ignore[assignment]
    return importlib.reload(settings)  # type: ignore[return-value]
