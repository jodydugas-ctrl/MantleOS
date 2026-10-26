"""Materialize original golden bytes in a disposable test workspace only."""
import atexit
import os
from pathlib import Path
import tempfile
import mantleos.kpp

_temporary = None


def workspace():
    global _temporary
    if _temporary is None:
        _temporary = tempfile.TemporaryDirectory(prefix='reflex-fixtures-')
        atexit.register(_temporary.cleanup)
        root = Path(_temporary.name)
        resources = Path(mantleos.kpp.__file__).parent/'resources'
        # Original CLI cases run from their disposable fixture workspace.
        os.environ['PYTHONPATH'] = str(Path(mantleos.kpp.__file__).resolve().parents[2])
        for tree, destination in [('examples/reflex_book', 'examples/reflex_book'),
                                  ('docs/reflex-history', 'docs/reflex')]:
            for source in (resources/tree).rglob('*'):
                if not source.is_file():
                    continue
                target = root/destination/source.relative_to(resources/tree)
                raw = source.read_bytes()
                if source.name.endswith('.hex.txt'):
                    target = target.with_name(target.name[:-8])
                    raw = bytes.fromhex(raw.decode('ascii'))
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
    return Path(_temporary.name)
