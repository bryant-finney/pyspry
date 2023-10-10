"""Define acceptance tests for feat(#6)."""
from __future__ import annotations

# stdlib
import importlib
from pathlib import Path

# third party
import pytest
from _pytest.tmpdir import TempPathFactory

# local
from pyspry.base import SettingsContainer

CFG_INSTALLED_APPS = """
PYSPRY_INSTALLED_APPS:
  - django.contrib.admin
  - django.contrib.auth
  - django.contrib.contenttypes
  - django.contrib.sessions
  - django.contrib.messages
  - django.contrib.staticfiles
  # django_extensions explicitly omitted
"""

CFG_LOGGING = """
PYSPRY_LOGGING:
  root:
    level: WARNING
"""


# ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯
#                                  fixture definitions


@pytest.fixture(scope="module")
def tmp_directory(tmp_path_factory: TempPathFactory) -> Path:
    """Create a temporary directory for the duration of the test module."""
    dirname: Path = tmp_path_factory.mktemp("pyspry-feat-6-")
    return dirname


@pytest.fixture(scope="module")
def cfg_installed_apps(tmp_directory: Path) -> Path:
    fname = tmp_directory / "installed-apps.yml"
    fname.write_text(CFG_INSTALLED_APPS)
    return fname


@pytest.fixture(scope="module")
def cfg_logging(tmp_directory: Path) -> Path:
    fname = tmp_directory / "logging.yml"
    fname.write_text(CFG_LOGGING)
    return fname


# ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯
#                                   tests for fixtures


def test_cfg_installed_apps_fixture(cfg_installed_apps: Path) -> None:
    """Test the `cfg_installed_apps` fixture."""
    assert cfg_installed_apps.read_text() == CFG_INSTALLED_APPS


def test_cfg_logging_fixture(cfg_logging: Path) -> None:
    """Test the `cfg_logging` fixture."""
    assert cfg_logging.read_text() == CFG_LOGGING


@pytest.mark.setenv(PYSPRY_CONFIG_PATH="sample-config.yml", PYSPRY_VAR_PREFIX="PYSPRY")
def test_pyspry_settings_fixture(pyspry_settings: SettingsContainer) -> None:
    """Test the `pyspry_settings` fixture."""
    importlib.reload(pyspry_settings)
    assert isinstance(pyspry_settings, SettingsContainer)


# ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯
#                                    acceptance tests
