"""BODY-only multi-cadence Engram projections; no MIND, I/O or authority.

Pure, bounded reference. The caller must obtain permitted records and admit any
persisted projection separately. This does not update model weights or history.
"""
from __future__ import annotations

from .. import engram
from ..engram import ZERO
from ..json_contract import canonical, digest

SCHEMA = 'kpp.sleep-memory-projection/1'
PUBLIC_TYPES = frozenset({'experience', 'observation', 'program-commit', 'tissue-revision'})
CADENCES = {'fast': 1, 'medium': 6, 'slow': 144}
WINDOWS = {'fast': 32, 'medium': 256, 'slow': 512}
MAX_RECORDS = 512
MAX_RECORD_BYTES = 65536


def due_tiers(beat_number, *, cadences=None):
    """Select due memory views; the Heart's 600-second rhythm is unchanged."""
    if type(beat_number) is not int or beat_number < 1:
        raise ValueError('beat_number must be a positive integer')
    rates = CADENCES if cadences is None else cadences
    if not isinstance(rates, dict) or set(rates) != set(CADENCES):
        raise ValueError('Exactly fast, medium, slow cadences are required')
    if any(type(v) is not int or not 1 <= v <= 1000000 for v in rates.values()):
        raise ValueError('Cadences must be bounded positive integers')
    return [tier for tier in CADENCES if beat_number % rates[tier] == 0]


def project(records, *, beat_number, previous_head=ZERO, expected_head=None, cadences=None):
    """Build deterministic derived indexes over a *complete* verified Engram prefix.

    Validation is repeated here so a forged source head cannot be passed through.
    Never mutates input, writes files, removes source, or calls a model.
    """
    due = due_tiers(beat_number, cadences=cadences)
    if not isinstance(records, list) or len(records) > MAX_RECORDS:
        raise ValueError('Bounded record list required')
    if not isinstance(previous_head, str) or not engram.HEX64.fullmatch(previous_head):
        raise ValueError('Invalid previous head')
    if expected_head is not None and (not isinstance(expected_head, str)
                                      or not engram.HEX64.fullmatch(expected_head)):
        raise ValueError('Invalid expected head')
    prev, index = ZERO, {ZERO: 0}
    safe_types = []
    for seq, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            raise ValueError('Invalid source record')
        canonical(record, limit=MAX_RECORD_BYTES)
        schema = record.get('schema')
        if schema not in ('mantle.engram-record/1', 'raven.engram-record/1'):
            raise ValueError('Unsupported Engram schema')
        prev_key = 'prev' if schema == 'raven.engram-record/1' else 'prev_sha256'
        sha = record.get('sha256')
        if (type(record.get('seq')) is not int or record['seq'] != seq
                or record.get(prev_key) != prev
                or not isinstance(sha, str) or not engram.HEX64.fullmatch(sha)
                or engram.hash_record(record) != sha):
            raise ValueError('Engram integrity or order failed')
        prev = sha
        index[sha] = seq
        kind = record.get('type')
        safe_types.append(kind if isinstance(kind, str) and kind in PUBLIC_TYPES else 'other')
    if expected_head is not None and expected_head != prev:
        raise ValueError('Source does not match the expected head')
    if previous_head not in index:
        raise ValueError('Previous head is not in source history; reconcile before use')
    delta_start = index[previous_head]
    new = records[delta_start:]
    tiers = {}
    if records:
        for tier in due:
            begin = max(0, len(records) - WINDOWS[tier])
            visible = records[begin:]
            counts = {}
            for kind in safe_types[begin:]:
                counts[kind] = counts.get(kind, 0) + 1
            tiers[tier] = {
                'window_start_seq': begin + 1,
                'window_count': len(visible),
                'type_counts': dict(sorted(counts.items())),
                'source_refs': [r['sha256'] for r in visible],
            }
    report = {
        'schema': SCHEMA,
        'beat_number': beat_number,
        'source_head': prev,
        'previous_head': previous_head,
        'delta_count': len(new),
        'delta_refs': [r['sha256'] for r in new],
        'due_tiers': due,
        'tier_views': tiers,
        'status': 'EMPTY' if not records else 'PROJECTED' if tiers else 'DEFERRED' if new else 'UNCHANGED',
        'authority': 'NONE',
        'effect_claim': 'NONE',
        'source_truth': 'APPEND_ONLY_ENGRAM',
        'mind_calls': 0,
    }
    return {**report, 'projection_sha256': digest(report)}
