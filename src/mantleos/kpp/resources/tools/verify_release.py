"""Recheck all and only released repository files (integrity, NOT authenticity)."""
import hashlib
import json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'SHA256SUMS.json').read_text(encoding='utf-8'))
if manifest.get('schema')!='kpp.release-files/1' or not isinstance(manifest.get('files'),dict):
    raise SystemExit('Unsupported release hash schema')
for name, expected in sorted(manifest['files'].items()):
    p=root/name
    if p.is_symlink() or not p.resolve().is_relative_to(root.resolve()) or not p.is_file():
        raise SystemExit('MISSING/UNSAFE '+name)
    actual=hashlib.sha256(p.read_bytes()).hexdigest()
    if actual!=expected:
        raise SystemExit('HASH MISMATCH '+name)
# Ignore ordinary local development outputs, not extra shipped source files.
SKIP={'.git','__pycache__','.pytest_cache','.venv','dist','build','workspaces'}
observed=set()
for path in root.rglob('*'):
    rel=path.relative_to(root)
    if any(part in SKIP or part.endswith('.egg-info') for part in rel.parts):
        continue
    if path.is_symlink():
        raise SystemExit('UNEXPECTED SYMLINK '+rel.as_posix())
    if path.is_file() and not path.name.endswith(('.pyc','.pyo','.tmp')):
        observed.add(rel.as_posix())
expected=set(manifest['files'])|{'SHA256SUMS.json'}
if observed != expected:
    raise SystemExit('FILE INVENTORY DIFF: missing='+str(sorted(expected-observed))+' extra='+str(sorted(observed-expected)))
print('PASS:',len(manifest['files']),'release file hashes and exact source inventory match. Hashes are not signatures.')
