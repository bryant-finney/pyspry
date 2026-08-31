"""Execute component-level tests for the `pyspry` package."""

from __future__ import annotations

# stdlib
import logging
from itertools import product
from typing import Any

# third party
import pytest
from _pytest.monkeypatch import MonkeyPatch

# local
from pyspry import conftest
from pyspry.base import ConfigLoader, Settings, SettingsContainer

logger = logging.getLogger(__name__)

logger.debug("imported conftest module %s", conftest.__name__)

# pylint: disable=redefined-outer-name


@pytest.fixture()
def bootstrapped_settings(monkeypatch: MonkeyPatch) -> SettingsContainer:
    """Bootstrap a module named `__bootstrapped_settings` in the same way as `pyspry.settings`."""
    monkeypatch.setenv(ConfigLoader.VARNAME_CONFIG_PATH, "sample-config.yml")
    monkeypatch.setenv(ConfigLoader.VARNAME_VAR_PREFIX, "PYSPRY")

    return SettingsContainer.bootstrap("__bootstrapped_settings")


def test_keys_merged(configuration: dict[str, Any], settings: Settings) -> None:
    """Verify that nested keys are properly merged."""
    attr_names = ["APP_NAME_ATTR_B", "APP_NAME_ATTR_B_K"]
    sources: list[dict[str, Any] | Settings] = [configuration, settings]

    for attr_name, source in product(attr_names, sources):
        assert attr_name in source

    assert configuration["APP_NAME_ATTR_B_K"] == settings.APP_NAME_ATTR_B_K
    assert configuration["APP_NAME_ATTR_B_K"] == settings.APP_NAME_ATTR_B["K"]


def test_infra_486(bootstrapped_settings: SettingsContainer) -> None:
    """Reproduce the error condition from INFRA-486 and assert it has been resolved."""
    assert len(bootstrapped_settings.AUTH_PASSWORD_VALIDATORS)
    assert (
        bootstrapped_settings.AUTH["PASSWORD_VALIDATORS"]
        == bootstrapped_settings.AUTH_PASSWORD_VALIDATORS
    )
    assert "AUTH_PASSWORD_VALIDATORS" in dir(bootstrapped_settings)
