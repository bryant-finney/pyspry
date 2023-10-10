"""Bootstrap this module with a `Settings` object created from the `PYSPRY_CONFIG_PATH` file.

To update the settings in this module, open the default YAML file path and change the settings
there.
"""
# local
from pyspry.base import SettingsContainer

# note: importlib.reload() sets __name__ to 'builtins', causing issues. so hardcode it instead.
SettingsContainer.bootstrap("pyspry.settings")
