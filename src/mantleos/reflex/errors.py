"""Compatibility alias; implementation is maintained in reflex_book."""
import importlib as _importlib
import sys as _sys
_sys.modules[__name__] = _importlib.import_module('mantleos.reflex_book.errors')
