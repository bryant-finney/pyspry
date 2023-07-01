# noqa: D200,D212,D400,D415
"""
.. include:: ../../README.md
"""  # noqa: RST499
# stdlib
import logging

# local
from pyspry.base import Settings
from pyspry.nested_dict import NestedDict

logger = logging.getLogger(__name__)

logger.debug(
    "the following classes are exposed for this package's public API: %s",
    ",".join([Settings.__name__, NestedDict.__name__]),
)
