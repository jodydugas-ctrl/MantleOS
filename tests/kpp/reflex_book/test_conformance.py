from mantleos.reflex_book.fixtures import root as fixture_root
import copy
import hashlib
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from mantleos.reflex_book.bytecode import encode,decode,disassemble
from mantleos.reflex_book.canonical import loads,dumps,sha256
from mantleos.reflex_book.checker import validate
from mantleos.reflex_book.compiler import compile_ir
from mantleos.reflex_book.errors import ReflexError
from mantleos.reflex_book.parser import parse_program
from mantleos.reflex_book.reference import run as ast_run
from mantleos.reflex_book.types import TRUE,FALSE,UNKNOWN,and3,or3,not3
from mantleos.reflex_book.vm import run as vm_run

EXAMPLES=fixture_root()/'examples'/'reflex_book'


def fixture(name):
    return (EXAMPLES/name).read_bytes()


def compiled(rule='location_rule.json'):
    return encode(compile_ir(parse_program(fixture(rule))))


class ReflexTests(unittest.TestCase):
    def test_bool3_truth_table(self):
        self.assertEqual([not3(x) for x in (TRUE,FALSE,UNKNOWN)], [FALSE,TRUE,UNKNOWN])
        for x in (TRUE,FALSE,UNKNOWN):
            for y in (TRUE,FALSE,UNKNOWN):
                self.assertEqual(and3([x,y]), FALSE if FALSE in (x,y) else UNKNOWN if UNKNOWN in (x,y) else TRUE)
                self.assertEqual(or3([x,y]), TRUE if TRUE in (x,y) else UNKNOWN if UNKNOWN in (x,y) else FALSE)

    def test_canonical_order_and_digest(self):
        self.assertEqual(dumps(loads('{"b":2,"a":1}')), b'{"a":1,"b":2}')
        self.assertEqual(sha256(loads('{"b":2,"a":1}')),sha256(loads('{"a":1,"b":2}')))

    def test_json_parser_negative(self):
        for file,code in [('invalid_duplicate_key.json','E_DUPLICATE_KEY'),('invalid_float.json','E_NUMBER')]:
            with self.subTest(file=file),self.assertRaises(ReflexError) as ctx:
                loads(fixture(file))
            self.assertEqual(ctx.exception.code,code)

    def test_negative_programs_stable_codes(self):
        entries=loads(fixture('invalid_program_manifest.json'))['cases']
        for entry in entries:
            with self.subTest(entry=entry),self.assertRaises(ReflexError) as ctx:
                parse_program(fixture(entry['file']))
            self.assertEqual(ctx.exception.code,entry['code'])

    def test_golden_vectors_oracle_and_vm(self):
        vectors=loads(fixture('golden_vectors.json'))['vectors']
        self.assertGreaterEqual(len(vectors),15)
        for entry in vectors:
            with self.subTest(entry=entry):
                ir=parse_program(fixture(entry['rule']))
                raw=compiled(entry['rule'])
                got=vm_run(raw,fixture(entry['input']))
                expected=ast_run(ir,fixture(entry['input']))
                self.assertEqual(got['result'],expected)
                self.assertEqual(got['result']['status'],entry['expected'])
                self.assertEqual(got['program_sha256'],sha256(ir))
                self.assertFalse(got['authorized'])
                self.assertEqual(got['refusal_code'],None)

    def test_compile_decode_roundtrip(self):
        ir=parse_program(fixture('location_rule.json'))
        bc=decode(compiled())
        self.assertEqual(bc['ir'],ir)
        self.assertEqual(dumps(bc['ir']),dumps(ir))
        self.assertEqual(bc['program_sha256'],sha256(ir))
        self.assertEqual(encode(decode(compiled())),compiled())

    def test_instruction_disassembly(self):
        ops=[x['op'] for x in disassemble(compiled())['instructions']]
        self.assertIn('GEO_OUTSIDE',ops)
        self.assertIn('GUARD3',ops)
        self.assertEqual(ops[-1],'HALT')
        self.assertNotIn('CALL',ops)

    def test_binary_header_tamper(self):
        original=compiled()
        cases=[b'wrong',original[:-1],original[:8]+bytes([original[8]^1])+original[9:]]
        expected=['E_BINARY','E_BINARY','E_INTEGRITY']
        for blob,code in zip(cases,expected):
            with self.subTest(code=code),self.assertRaises(ReflexError) as ctx:
                decode(blob)
            self.assertEqual(ctx.exception.code,code)

    def test_recomputed_integrity_cannot_change_opcode(self):
        bc=decode(compiled())
        bc['instructions'][0][0]='CALL_NETWORK'
        with self.assertRaises(ReflexError) as ctx:
            decode(encode(bc))
        self.assertEqual(ctx.exception.code,'E_INTEGRITY')

    def test_no_self_granted_authority(self):
        ir=parse_program(fixture('location_rule.json'))
        for mutation in [lambda x:x['capabilities'].append('write:self'),
                         lambda x:x.__setitem__('install',True),
                         lambda x:x.__setitem__('on_anomaly','SEND_SMS')]:
            obj=copy.deepcopy(ir);mutation(obj)
            with self.assertRaises(ReflexError):
                validate(obj)

    def test_unsupported_book_refused(self):
        ir=parse_program(fixture('location_rule.json'))
        ir['book']['edition']='0.2'
        with self.assertRaises(ReflexError) as ctx:
            compile_ir(ir)
        self.assertEqual(ctx.exception.code,'E_EDITION')

    def test_input_malformed_refusal(self):
        env=loads(fixture('location_normal.json'))
        for mutate,code in [(lambda x:x['values']['position'].__setitem__('accuracy_m',-1),'E_RANGE'),
                            (lambda x:x['values']['position'].__setitem__('observed_at','2026-10-23 12:00'),'E_TIMESTAMP'),
                            (lambda x:x['values'].__setitem__('secret',1),'E_INPUT_REF'),
                            (lambda x:x['values']['position'].__setitem__('source','real patient'),'E_SOURCE')]:
            trial=copy.deepcopy(env);mutate(trial)
            with self.subTest(code=code),self.assertRaises(ReflexError) as ctx:
                vm_run(compiled(),dumps(trial))
            self.assertEqual(ctx.exception.code,code)

    def test_not_a_host_effect(self):
        result=vm_run(compiled(),fixture('location_anomaly.json'))['result']
        self.assertEqual(result,{'status':'ANOMALY','review_requested':True})
        self.assertEqual(set(result),{'status','review_requested'})

    def test_10000_identical_runs(self):
        binary=compiled()
        data=fixture('location_anomaly.json')
        with patch('socket.socket',side_effect=AssertionError('network access forbidden')):
            first=vm_run(binary,data)
            for _ in range(10000):
                self.assertEqual(vm_run(binary,data),first)


if __name__=='__main__':
    unittest.main()

class HostileShapeTests(unittest.TestCase):
    def test_malformed_shapes_return_refusal_not_python_exception(self):
        program=parse_program(fixture('location_rule.json'))
        cases=[
            ('inputs', {'position':[], 'routine_region':'Region'}),
            ('predicate', {'op':'compare_eq','left':23,'right':{'const':{'type':'Int','value':1}}}),
            ('outcomes', {'true':[], 'false':'NORMAL','unknown':'UNKNOWN'}),
            ('predicate', {'op':'known','input':[]}),
            ('on_anomaly', [])]
        for k,v in cases:
            candidate=copy.deepcopy(program)
            candidate[k]=v
            with self.subTest(k=k,v=v),self.assertRaises(ReflexError):
                validate(candidate)

    def test_unapproved_candidate_has_no_install_path(self):
        from mantleos.reflex_book.admission import install
        with self.assertRaises(ReflexError) as exc:
            install(loads(fixture('candidate_unapproved.json')))
        self.assertEqual(exc.exception.code,'E_AUTHORITY')
