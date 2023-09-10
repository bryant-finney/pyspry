"""Execute component-level tests for the `pyspry` package."""
from __future__ import annotations

# stdlib
import logging
from itertools import product
from pathlib import Path
from typing import Any, Iterator

# third party
import pytest

# local
from pyspry import conftest
from pyspry.base import Settings

logger = logging.getLogger(__name__)

logger.debug("imported conftest module %s", conftest.__name__)

# pylint: disable=redefined-outer-name


@pytest.fixture()
def bootstrapped_settings() -> Iterator[Settings]:
    """Bootstrap a module named `bootstrapped.settings` in the same manner as `pyspry.settings`.

    After the test has completed, restore the original module.

    Yields:
        Iterator[Settings]: the `Settings` object after replacing `bootstrapped.settings`
    """
    settings = Settings.load(Path("sample-config.yml"), "PYSPRY")
    settings.bootstrap("bootstrapped.settings")
    try:
        yield settings
    finally:
        settings.restore()


def test_keys_merged(config: dict[str, Any], settings: Settings) -> None:
    """Verify that nested keys are properly merged."""
    attr_names = ["APP_NAME_ATTR_B", "APP_NAME_ATTR_B_K"]
    sources: list[dict[str, Any] | Settings] = [config, settings]

    for attr_name, source in product(attr_names, sources):
        assert attr_name in source

    assert config["APP_NAME_ATTR_B_K"] == settings.APP_NAME_ATTR_B_K
    assert config["APP_NAME_ATTR_B_K"] == settings.APP_NAME_ATTR_B["K"]


def test_infra_486(bootstrapped_settings: Settings) -> None:
    """Reproduce the error condition from INFRA-486 and assert it has been resolved."""
    assert len(bootstrapped_settings.AUTH_PASSWORD_VALIDATORS)
    assert (
        bootstrapped_settings.AUTH["PASSWORD_VALIDATORS"]
        == bootstrapped_settings.AUTH_PASSWORD_VALIDATORS
    )
    assert "AUTH_PASSWORD_VALIDATORS" in dir(bootstrapped_settings)
