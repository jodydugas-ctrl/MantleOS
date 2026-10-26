"""Canonical Kitchen Party Protocol within the one MantleOS system."""
import sys as _sys
from .. import anchors
__version__ = "1.1.0a5"
_sys.modules[__name__ + '.anchors'] = anchors

from .language import implementation_plan
