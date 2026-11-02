"""Reproduce the error from [#5](https://gitlab.com/bfosi/pyspry/-/issues/5)."""

from __future__ import annotations

# stdlib
import json
from os import environ

# third party
import pytest
from _pytest.monkeypatch import MonkeyPatch

# local
from pyspry import Settings


@pytest.mark.skipif(
    len(environ.get("PYSPRY_INSTALLED_APPS", "")) > 0,
    reason="Skipping because the env variable PYSPRY_INSTALLED_APPS="
    + environ.get("PYSPRY_INSTALLED_APPS", ""),
)
def test_shorter_env_variable(monkeypatch: MonkeyPatch) -> None:
    """Set an env variable `PYSPRY_INSTALLED_APPS` to a shorter array than its YAML."""
    # Arrange
    override = [f"{__name__}-0", f"{__name__}-1"]
    monkeypatch.setenv("PYSPRY_INSTALLED_APPS", json.dumps(override))

    # Act
    settings = Settings.load("sample-config.yml", prefix="PYSPRY")

    # Assert
    assert settings.INSTALLED_APPS == override
