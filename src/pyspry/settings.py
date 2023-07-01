"""Bootstrap this module with a `Settings` object created from the `PYSPRY_CONFIG_PATH` file.

To update the settings in this module, open the default YAML file path and change the settings
there.
"""
# stdlib
from os import getenv
from pathlib import Path

# local
from pyspry.base import Settings

config_path = Path(getenv("PYSPRY_CONFIG_PATH", "config.yml"))
prefix = getenv("PYSPRY_VAR_PREFIX", None)

Settings.load(config_path, prefix).bootstrap(__name__)
