"""Define acceptance tests for feat(#6)."""
from __future__ import annotations

# stdlib
import importlib
import json
from pathlib import Path

# third party
import pytest
import yaml
from _pytest.monkeypatch import MonkeyPatch
from _pytest.tmpdir import TempPathFactory

# local
from pyspry.base import ConfigLoader, SettingsContainer

# pylint: disable=redefined-outer-name

PARSED_INSTALLED_APPS = {
    "PYSPRY_INSTALLED_APPS": [
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.messages",
        "django.contrib.staticfiles",
        # django_extensions explicitly omitted
    ]
}
CFG_INSTALLED_APPS = yaml.dump(PARSED_INSTALLED_APPS, indent=2)

PARSED_LOGGING = {"PYSPRY_LOGGING": {"root": {"level": "WARNING"}}}
CFG_LOGGING = yaml.dump(PARSED_LOGGING, indent=2)


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


@pytest.mark.setenv(PYSPRY_CONFIG_PATH="sample-config.yml", PYSPRY_VAR_PREFIX="PYSPRY")
def test_no_overrides(pyspry_settings: SettingsContainer) -> None:
    """Verify that the default settings do not match the values in the overrides."""
    assert pyspry_settings.INSTALLED_APPS != PARSED_INSTALLED_APPS["PYSPRY_INSTALLED_APPS"]
    assert pyspry_settings.LOGGING_root_level != PARSED_LOGGING["PYSPRY_LOGGING"]["root"]["level"]


def test_installed_apps_override(cfg_installed_apps: Path, monkeypatch: MonkeyPatch) -> None:
    """Test #6 by loading a config file that overrides the `INSTALLED_APPS` setting."""
    # Arrange
    monkeypatch.setenv(
        ConfigLoader.VARNAME_CONFIG_PATH,
        json.dumps(["sample-config.yml", str(cfg_installed_apps.absolute())]),
    )
    monkeypatch.setenv(ConfigLoader.VARNAME_VAR_PREFIX, "PYSPRY")

    # Act
    settings = importlib.import_module("pyspry.settings")
    settings_ = importlib.reload(settings)

    # Assert
    assert settings_.INSTALLED_APPS == PARSED_INSTALLED_APPS["PYSPRY_INSTALLED_APPS"]


def test_logging_override(cfg_logging: Path, monkeypatch: MonkeyPatch) -> None:
    """Test #6 by loading a config file that overrides the `LOGGING` setting."""
    # Arrange
    monkeypatch.setenv(
        ConfigLoader.VARNAME_CONFIG_PATH,
        json.dumps(["sample-config.yml", str(cfg_logging.absolute())]),
    )
    monkeypatch.setenv(ConfigLoader.VARNAME_VAR_PREFIX, "PYSPRY")

    # Act
    settings = importlib.import_module("pyspry.settings")
    settings_ = importlib.reload(settings)

    # Assert
    assert settings_.LOGGING_root_level == PARSED_LOGGING["PYSPRY_LOGGING"]["root"]["level"]


def test_both_overrides(
    cfg_installed_apps: Path, cfg_logging: Path, monkeypatch: MonkeyPatch
) -> None:
    """Verify that both files can be used to override the default settings."""
    # Arrange
    monkeypatch.setenv(
        ConfigLoader.VARNAME_CONFIG_PATH,
        json.dumps(
            ["sample-config.yml", str(cfg_logging.absolute()), str(cfg_installed_apps.absolute())]
        ),
    )
    monkeypatch.setenv(ConfigLoader.VARNAME_VAR_PREFIX, "PYSPRY")

    # Act
    settings = importlib.import_module("pyspry.settings")
    settings_ = importlib.reload(settings)

    # Assert
    assert settings_.LOGGING_root_level == PARSED_LOGGING["PYSPRY_LOGGING"]["root"]["level"]
    assert settings_.INSTALLED_APPS == PARSED_INSTALLED_APPS["PYSPRY_INSTALLED_APPS"]
