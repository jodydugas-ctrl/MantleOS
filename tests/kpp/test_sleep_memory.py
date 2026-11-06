"""Offline synthetic qualification for BODY-only sleep-time memory views."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from mantleos import engram
from mantleos.kpp.sleep_memory import ZERO, due_tiers, project


def record(seq, previous, *, kind='experience', body=None, schema='mantle.engram-record/1'):
    value = {'schema': schema, 'seq': seq, 'id': f'synthetic-{seq}',
             'type': kind, 'source': 'synthetic-fixture', 'body': body or {},
             'prev' if schema == 'raven.engram-record/1' else 'prev_sha256': previous}
    value['sha256'] = engram.hash_record(value)
    return value


def chain(n=7):
    records, prior = [], ZERO
    for i in range(1, n+1):
        item = record(i, prior, kind='observation' if i % 2 else 'experience',
                      body={'private': f'SECRET-{i}'})
        records.append(item)
        prior = item['sha256']
    return records


class SleepMemoryTests(unittest.TestCase):
    def test_multi_timescale_is_not_a_new_scheduler(self):
        self.assertEqual(due_tiers(1), ['fast'])
        self.assertEqual(due_tiers(6), ['fast', 'medium'])
        self.assertEqual(due_tiers(144), ['fast', 'medium', 'slow'])
        with self.assertRaises(ValueError): due_tiers(0)
        with self.assertRaises(ValueError): due_tiers(True)
        with self.assertRaises(ValueError): due_tiers(1, cadences={'fast': 1})

    def test_offline_projection_is_pure_deterministic_and_redacted(self):
        records = chain()
        original = copy.deepcopy(records)
        a = project(records, beat_number=6)
        self.assertEqual(a, project(records, beat_number=6))
        self.assertEqual(records, original)
        self.assertEqual(a['mind_calls'], 0)
        self.assertEqual(a['effect_claim'], 'NONE')
        self.assertEqual(a['delta_count'], 7)
        self.assertEqual(set(a['tier_views']), {'fast', 'medium'})
        self.assertEqual(a['tier_views']['fast']['type_counts'],
                         {'experience': 3, 'observation': 4})
        self.assertNotIn('SECRET-', json.dumps(a))

    def test_replay_and_incremental_delta(self):
        records = chain()
        seen = project(records, beat_number=6)
        replay = project(records, beat_number=7, previous_head=seen['source_head'])
        self.assertEqual(replay['status'], 'PROJECTED')
        self.assertEqual(replay['delta_refs'], [])
        later = record(8, records[-1]['sha256'])
        appended = project(records + [later], beat_number=8, previous_head=seen['source_head'])
        self.assertEqual(appended['delta_count'], 1)
        self.assertEqual(appended['delta_refs'], [later['sha256']])
        self.assertEqual(appended['status'], 'PROJECTED')

    def test_later_tier_refreshes_with_no_new_records(self):
        records = chain()
        fast = project(records, beat_number=1)
        self.assertEqual(set(fast['tier_views']), {'fast'})
        head = fast['source_head']
        slow = project(records, beat_number=144, previous_head=head, expected_head=head)
        self.assertEqual(set(slow['tier_views']), {'fast', 'medium', 'slow'})
        self.assertEqual(slow['delta_count'], 0)
        self.assertEqual(slow['tier_views']['slow']['source_refs'], fast['delta_refs'])
        with self.assertRaisesRegex(ValueError, 'expected head'):
            project(records[:-1], beat_number=144, expected_head=head)

    def test_custom_type_names_are_bucketed(self):
        records = [record(1, ZERO, kind='private-account-name')]
        view = project(records, beat_number=1)
        self.assertEqual(view['tier_views']['fast']['type_counts'], {'other': 1})
        self.assertNotIn('private-account-name', json.dumps(view))

    def test_historical_head_and_tampering_fail_closed(self):
        records = chain()
        with self.assertRaises(ValueError): project(records, beat_number=1, previous_head='f'*64)
        damaged = copy.deepcopy(records)
        damaged[0]['body']['private'] = 'CHANGED'
        with self.assertRaises(ValueError): project(damaged, beat_number=1)
        damaged = copy.deepcopy(records)
        damaged[1]['prev_sha256'] = ZERO
        with self.assertRaises(ValueError): project(damaged, beat_number=1)
        with self.assertRaises(ValueError): project(records + [records[-1]], beat_number=1)

    def test_bounds_and_empty_cases(self):
        self.assertEqual(project([], beat_number=1)['status'], 'EMPTY')
        with self.assertRaises(ValueError): project([{}]*513, beat_number=1)
        with self.assertRaises(ValueError): project([{'body': 'x'*70000}], beat_number=1)
        self.assertEqual(project(chain(1), beat_number=2,
                                 cadences={'fast': 3, 'medium': 6, 'slow': 144})['status'], 'DEFERRED')

    def test_raven_schema_and_no_model_requirement(self):
        r = record(1, ZERO, schema='raven.engram-record/1')
        self.assertEqual(project([r], beat_number=1)['status'], 'PROJECTED')

    def test_current_ledger_remains_byte_identical(self):
        with tempfile.TemporaryDirectory() as work:
            ledger = Path(work) / 'ENGRAM.jsonl'
            entry = engram.append(ledger, 'observation', 'synthetic', {'text': 'a note'})
            before = ledger.read_bytes()
            result = project(engram.read(ledger), beat_number=6, expected_head=entry['sha256'])
            self.assertEqual(result['source_head'], entry['sha256'])
            self.assertEqual(ledger.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
