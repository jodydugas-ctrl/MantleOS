"""Unicode 16.0.0 full default fold, represented by finite literal rows.

Derived from CaseFolding.txt (C+F, excluding Turkic T). Copyright 2024 Unicode,
Inc. Unicode License v3; see reference_materials/unicode/LICENSE.txt.
The editor profile rejects expanding folds to preserve scalar offsets.
"""
import hashlib,json
# BEGIN TABLE RESOURCE
from pathlib import Path
_primer = (Path(__file__).resolve().parents[1] / 'templates/primer_notepad_llm_v1.txt').read_text('utf-8')
TABLE_JSON = next(line for line in _primer.splitlines() if line.startswith('{"unicode":'))
# END TABLE RESOURCE
TABLE_SHA256='11a6037f07386e3f8918a0bf75afdec2bf256877101f1d702d88cadefe51961a'

if hashlib.sha256(TABLE_JSON.encode('utf-8')).hexdigest()!=TABLE_SHA256:
    raise ValueError('Case-fold table fingerprint mismatch')
TABLE=json.loads(TABLE_JSON)
PAIRS={a:b for source,target in TABLE['rows'] for a,b in zip(source,target)}
EXPANDS=frozenset(TABLE['expands'])
def fold_scalar(value):
    return None if value in EXPANDS else PAIRS.get(value,value)
