"""Define a `KeysView` class based on the current Python interpreter version."""
# stdlib
import sys

__all__ = ["KT", "NestedKeysView"]

if sys.version_info.minor > 8:
    # local
    from pyspry.keysview.py38plus import KT, NestedKeysView
else:  # pragma: no cover
    # local
    from pyspry.keysview.py38 import KT, NestedKeysView  # type: ignore[no-redef,assignment]
