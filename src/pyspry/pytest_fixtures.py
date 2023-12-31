"""Define fixtures for this package's test suite."""
from __future__ import annotations

# stdlib
from pathlib import Path
from typing import Any, Iterator

# third party
import pytest
import yaml
from _pytest.monkeypatch import MonkeyPatch
from _pytest.tmpdir import TempPathFactory

# local
from pyspry.base import Settings

# pylint: disable=redefined-outer-name

CONFIG_YAML = """
    APP_NAME_ATTR_A: [1, 2, 3]
    APP_NAME_EXAMPLE_PARAM: a string!
    APP_NAME_ATTR_B_K: 0
    APP_NAME_ATTR_B:
        K: "V"

    # note: these settings should be ignored
    OTHER_APP_NAME_ATTR_B: nope
    OTHER_APP_NAME_ATTR_C:
        K: 1
        V: 2
"""


@pytest.fixture(scope="session")
def configuration() -> dict[str, Any]:
    """Provide a `dict` containing dummy config settings.

    Returns:
        dict[str, Any]: the dummy config for `NestedDict` objects
    """
    config: dict[str, Any] = yaml.safe_load(CONFIG_YAML)
    return config


@pytest.fixture()
def monkey_example_param(monkeypatch: MonkeyPatch) -> dict[str, str]:
    """Monkeypatch the environment variable named `APP_NAME_EXAMPLE_PARAM`.

    Args:
        monkeypatch (MonkeyPatch): depend on this fixture for patching the environment

    Returns:
        dict[str, str]: this `dict` includes changes to `os.environ`
    """
    environ = {"APP_NAME_EXAMPLE_PARAM": "monkeypatched!"}
    for name, value in environ.items():
        monkeypatch.setenv(name, value)
    return environ


@pytest.fixture()
def monkey_attr_a(monkeypatch: MonkeyPatch) -> dict[str, str]:
    """Monkeypatch the environment variable named `APP_NAME_ATTR_A`.

    Args:
        monkeypatch (MonkeyPatch): depend on this fixture for patching the environment

    Returns:
        dict[str, str]: this `dict` includes changes to `os.environ`
    """
    environ = {"APP_NAME_ATTR_A": "[4, 5, 6]"}
    for name, value in environ.items():
        monkeypatch.setenv(name, value)
    return environ


@pytest.fixture(scope="session")
def config_path(
    tmp_path_factory: TempPathFactory, worker_id: str, configuration: dict[str, Any]
) -> Iterator[Path]:
    """Create a test configuration file in the machine's temporary directory.

    After the test session completes, remove the temporary file.

    Args:
        tmp_path_factory (TempPathFactory): depend on this fixture for creating the directory
        worker_id (str): use the `worker_id` in the `/tmp` path to avoid concurrency issues
        configuration (dict[str, Any]): use this fixture for dummy data to write to file

    Yields:
        Iterator[Path]: the path to the config file to use during tests
    """
    tmp = tmp_path_factory.mktemp(f"pyspry-{worker_id}", numbered=True)
    config_path = tmp / "config.yml"

    with open(config_path, "w", encoding="UTF-8") as f:
        yaml.dump(configuration, f, indent=2)

    try:
        yield config_path
    finally:
        config_path.unlink(missing_ok=True)
        tmp.rmdir()


@pytest.fixture()
def settings(config_path: Path) -> Settings:
    """Instantiate a `Settings` object with this fixture.

    Args:
        config_path (Path): load this test config file

    Returns:
        Settings: the settings loaded from `config_path`
    """
    return Settings.load(config_path, prefix="APP_NAME")
