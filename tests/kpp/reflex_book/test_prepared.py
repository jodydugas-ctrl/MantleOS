from mantleos.reflex_book.fixtures import root as fixture_root
import copy
from dataclasses import FrozenInstanceError
import hashlib
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from mantleos.reflex_book import bytecode, compiler, vm
from mantleos.reflex_book.canonical import dumps, loads
from mantleos.reflex_book.errors import ReflexError
from mantleos.reflex_book.parser import parse_program

FIX = fixture_root() / 'examples/reflex_book'


def binary(name='location_rule.json'):
    return bytecode.encode(compiler.compile_ir(parse_program((FIX / name).read_bytes())))


class PreparedTests(unittest.TestCase):
    def test_canonical_binary_only(self):
        original = binary()
        bc = bytecode.decode(original)
        for payload in (json.dumps(bc, indent=2).encode(), dumps(bc) + b'\n'):
            changed = b'RFX1' + struct.pack('>I', len(payload)) + hashlib.sha256(payload).digest() + payload
            with self.assertRaises(ReflexError) as exc:
                vm.prepare(changed)
            self.assertEqual(exc.exception.code, 'E_CANONICAL')
        self.assertEqual(bytecode.encode(bytecode.decode(original)), original)

    def test_prepare_once_execute_10000_times_without_compiler(self):
        raw = binary()
        data = (FIX / 'location_normal.json').read_bytes()
        expected = vm.run(raw, data)
        with patch.object(bytecode, 'compile_ir', wraps=compiler.compile_ir) as compile_check:
            prepared = vm.prepare(raw)
            self.assertEqual(compile_check.call_count, 1)
            with patch.object(vm, 'decode', side_effect=AssertionError('decoded again')), \
                 patch('socket.socket', side_effect=AssertionError('network access')):
                for _ in range(10000):
                    self.assertEqual(vm.run_prepared(prepared, data), expected)
            self.assertEqual(compile_check.call_count, 1)

    def test_handle_is_immutable_and_supplies_no_authority(self):
        prepared = vm.prepare(binary())
        with self.assertRaises(FrozenInstanceError):
            prepared._program_sha256 = 'f' * 64
        with self.assertRaises(TypeError):
            prepared._program['inputs']['position'] = 'Int'
        with self.assertRaises(TypeError):
            prepared._instructions[0][0] = 'EVIL'
        for handle in ({}, vm.PreparedProgram(), None):
            with self.assertRaises(ReflexError):
                vm.run_prepared(handle, (FIX / 'location_normal.json').read_bytes())
        self.assertFalse(vm.run_prepared(prepared, (FIX / 'location_normal.json').read_bytes())['authorized'])

    def test_every_call_still_validates_inputs(self):
        prepared = vm.prepare(binary())
        data = loads((FIX / 'location_normal.json').read_bytes())
        data['values']['position']['accuracy_m'] = -1
        with self.assertRaises(ReflexError):
            vm.run_prepared(prepared, data)

    def test_unknown_explanations_and_legacy_trace(self):
        prepared = vm.prepare(binary())
        cases = {'location_stale.json': 'OBSERVATION_STALE',
                 'location_future.json': 'OBSERVATION_FUTURE',
                 'location_poor_quality.json': 'QUALITY_INADEQUATE',
                 'location_boundary.json': 'BOUNDARY_UNCERTAIN',
                 'location_high_latitude.json': 'GEOMETRY_UNSUPPORTED',
                 'location_missing_region.json': 'INPUT_MISSING'}
        for name, code in cases.items():
            data = (FIX / name).read_bytes()
            legacy = vm.run_prepared(prepared, data)
            explained = vm.run_prepared(prepared, data, explain=True)
            self.assertEqual(legacy['result'], explained['result'])
            self.assertEqual(explained['decision'], 'UNKNOWN', name)
            self.assertIn(code, [r['code'] for r in explained['reasons']], name)
            self.assertNotIn('reasons', legacy)
            self.assertNotIn('values', explained)
            for reason in explained['reasons']:
                self.assertEqual(set(reason), {'code', 'input', 'pc'})

    def test_global_guards_keep_priority_and_known_means_present(self):
        raw = binary()
        program = bytecode.decode(raw)['ir']
        program['predicate'] = {'op': 'and', 'args': [program['predicate'], {'op': 'literal', 'value': 'FALSE'}]}
        prepared = vm.prepare(bytecode.encode(compiler.compile_ir(program)))
        report = vm.run_prepared(prepared, (FIX / 'location_stale.json').read_bytes(), explain=True)
        self.assertEqual(report['decision'], 'UNKNOWN')
        self.assertEqual({r['code'] for r in report['reasons']}, {'OBSERVATION_STALE'})

    def test_decisive_boolean_discards_irrelevant_unknown_reasons(self):
        program = parse_program((FIX / 'counter_rule.json').read_bytes())
        program['predicate'] = {'op': 'or', 'args': [
            {'op': 'literal', 'value': 'TRUE'},
            {'op': 'compare_range', 'input': 'count', 'min': 1, 'max': 2}]}
        prepared = vm.prepare(bytecode.encode(compiler.compile_ir(program)))
        data = {'schema': 'mantle.reflex-input/0.1', 'clock_utc': '2026-10-24T12:00:00Z', 'values': {}}
        report = vm.run_prepared(prepared, data, explain=True)
        self.assertEqual(report['decision'], 'TRUE')
        self.assertEqual(report['reasons'], [])

    def test_independent_bool3_tables(self):
        # Expected tables are literal vectors, independent of shared logic helpers.
        states = ['TRUE', 'FALSE', 'UNKNOWN']
        expected = {'and': [['TRUE', 'FALSE', 'UNKNOWN'], ['FALSE', 'FALSE', 'FALSE'],
                            ['UNKNOWN', 'FALSE', 'UNKNOWN']],
                    'or': [['TRUE', 'TRUE', 'TRUE'], ['TRUE', 'FALSE', 'UNKNOWN'],
                           ['TRUE', 'UNKNOWN', 'UNKNOWN']]}
        base = parse_program((FIX / 'counter_rule.json').read_bytes())
        base['capabilities'] = []
        data = {'schema': 'mantle.reflex-input/0.1', 'clock_utc': '2026-10-24T12:00:00Z', 'values': {}}
        for op, table in expected.items():
            for i, left in enumerate(states):
                for j, right in enumerate(states):
                    program = copy.deepcopy(base)
                    program['predicate'] = {'op': op, 'args': [
                        {'op': 'literal', 'value': left}, {'op': 'literal', 'value': right}]}
                    prepared = vm.prepare(bytecode.encode(compiler.compile_ir(program)))
                    report = vm.run_prepared(prepared, data, explain=True)
                    self.assertEqual(report['decision'], table[i][j])

    def test_independent_integer_oracle(self):
        base = parse_program((FIX / 'counter_rule.json').read_bytes())
        base['predicate'] = {'op': 'and', 'args': [
            {'op': 'compare_range', 'input': 'count', 'min': -10, 'max': 20},
            {'op': 'not', 'arg': {'op': 'compare_eq', 'left': {'input': 'count'},
                                'right': {'const': {'type': 'Int', 'value': 13}}}}]}
        prepared = vm.prepare(bytecode.encode(compiler.compile_ir(base)))
        for count in list(range(-30, 31)) + [-(2**31), 2**31 - 1, None]:
            data = {'schema': 'mantle.reflex-input/0.1', 'clock_utc': '2026-10-24T12:00:00Z',
                    'values': {} if count is None else {'count': count}}
            expected = 'UNKNOWN' if count is None else 'TRUE' if -10 <= count <= 20 and count != 13 else 'FALSE'
            self.assertEqual(vm.run_prepared(prepared, data, explain=True)['decision'], expected)

    def test_independent_canonical_vectors(self):
        # Expected UTF-8 bytes are literals, not another call to the serializer.
        vectors = [({'z': 0, 'a': -12}, b'{"a":-12,"z":0}'),
                   ({'a': True, 'b': None, 'c': False}, b'{"a":true,"b":null,"c":false}'),
                   ({'text': 'é/\u2028\u2029'}, '{"text":"é/\u2028\u2029"}'.encode('utf-8')),
                   ({'\U00010000': 1, '\ue000': 2}, '{"\ue000":2,"\U00010000":1}'.encode('utf-8')),
                   ({'text': '\b\t\n\f\r\x00'}, b'{"text":"\\b\\t\\n\\f\\r\\u0000"}')]
        for value, expected in vectors:
            self.assertEqual(dumps(value), expected)
            self.assertEqual(loads(expected), value)
        self.assertEqual(dumps(loads(b'{"zero":-0}')), b'{"zero":0}')
        with self.assertRaises(ReflexError) as exc:
            dumps({'text': 'e\u0301'})
        self.assertEqual(exc.exception.code, 'E_TEXT')
