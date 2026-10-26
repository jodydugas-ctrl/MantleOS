"""Compatibility imports for the maintained mantleos.reflex_book toolkit.

KPP's unrelated Python Reflex staging stays in mantleos.kpp.reflex.
The legacy fresh-Body data transport remains available as .native.
"""
import importlib as _importlib
import sys as _sys
from ..reflex_book import __version__
for _name in ['admission', 'bytecode', 'canonical', 'checker', 'compiler', 'errors', 'evidence', 'parser', 'reference', 'registry', 'types', 'vm', 'carriers', 'carriers.contract', 'carriers.raw', 'carriers.zip_reflex', 'carriers.native']:
    _module = _importlib.import_module('mantleos.reflex_book.' + _name)
    _sys.modules[__name__ + '.' + _name] = _module
    if '.' not in _name:
        globals()[_name] = _module
