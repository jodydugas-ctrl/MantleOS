"""M0/M1 adversarial conformance and seeded differential sampling."""
import copy
import hashlib
import json
import random
from pathlib import Path
import unittest

from mantleos.reflex.bytecode import decode, encode
from mantleos.reflex.canonical import dumps, loads, sha256
from mantleos.reflex.checker import validate
from mantleos.reflex.compiler import compile_ir
from mantleos.reflex.errors import ReflexError
from mantleos.reflex.parser import parse_inputs, parse_program
from mantleos.reflex.reference import run as oracle
from mantleos.reflex.vm import run as interpreter

from .fixtures import workspace
BASE = workspace() / 'examples' / 'reflex_book'


def read(name):
    return (BASE / name).read_bytes()


class AdversarialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.geo = parse_program(read('location_rule.json'))
        cls.counter = parse_program(read('counter_rule.json'))
        cls.binary = encode(compile_ir(cls.geo))

    def refuse(self, fn, expected):
        with self.assertRaises(ReflexError) as ctx:
            fn()
        self.assertEqual(ctx.exception.code, expected)

    def test_signed_int32_input_bounds_and_bool_noncoercion(self):
        for x in (-2**31, 2**31-1):
            env={'schema':'mantle.reflex-input/0.1','clock_utc':'2026-10-23T12:00:00Z','values':{'count':x}}
            parse_inputs(env, self.counter)
        for x in (-2**31-1,2**31,True,False,'15',15.0):
            env={'schema':'mantle.reflex-input/0.1','clock_utc':'2026-10-23T12:00:00Z','values':{'count':x}}
            self.refuse(lambda:parse_inputs(env,self.counter), 'E_TYPE' if type(x) is float else 'E_RANGE')

    def test_direct_api_bypasses_are_refused(self):
        altered=copy.deepcopy(self.geo); altered['inputs']['position']=float('nan')
        self.refuse(lambda:validate(altered),'E_TYPE')
        env={'schema':'mantle.reflex-input/0.1','clock_utc':'2026-10-23T12:00:00Z','values':{'count':{'deep':'not an integer'}}}
        self.refuse(lambda:parse_inputs(env,self.counter),'E_RANGE')
        env['values']['count']=2**64
        self.refuse(lambda:parse_inputs(env,self.counter),'E_NUMBER')
        env['values']['count']=10
        env['unexpected']=True
        self.refuse(lambda:parse_inputs(env,self.counter),'E_SHAPE')

    def test_nfc_and_invalid_unicode(self):
        self.refuse(lambda:loads('{"value":"e\\u0301"}'),'E_TEXT')
        self.refuse(lambda:loads('{"value":"\\ud800"}'),'E_TEXT')
        self.refuse(lambda:loads(chr(0xd800)),'E_TEXT')
        self.refuse(lambda:loads('{"value":01}'),'E_JSON')

    def test_reject_duplicate_nested_keys(self):
        self.refuse(lambda:loads('{"a":{"b":1,"b":2}}'),'E_DUPLICATE_KEY')

    def test_node_depth_and_byte_limits(self):
        program=copy.deepcopy(self.counter)
        for _ in range(33):
            program['predicate']={'op':'not','arg':program['predicate']}
        self.refuse(lambda:validate(program),'E_DEPTH')
        too_long = b'"' + b'a'*65536 + b'"'
        self.refuse(lambda:loads(too_long),'E_SIZE')

    def test_static_result_budget(self):
        program=copy.deepcopy(self.geo)
        program['limits']['max_result_bytes']=1
        self.refuse(lambda:compile_ir(program),'E_LIMIT')

    def test_implicit_network_effect_and_extra_keys(self):
        for key in ('exec','network','permission','self_update','model_prompt'):
            proposal=copy.deepcopy(self.geo)
            proposal[key]={'mode':'allow'}
            self.refuse(lambda:validate(proposal),'E_SHAPE')

    def test_reordered_keys_and_whitespace_canonical_equivalence(self):
        src=read('counter_rule.json')
        program=loads(src)
        pretty=json.dumps(program, indent=4, sort_keys=False).encode('utf-8')
        self.assertEqual(dumps(parse_program(src)),dumps(parse_program(pretty)))
        self.assertEqual(encode(compile_ir(parse_program(src))),encode(compile_ir(parse_program(pretty))))

    def test_bytecode_corruption_at_multiple_offsets(self):
        original=self.binary
        for at in (0,3,4,7,8,39,40,len(original)-1):
            altered=bytearray(original); altered[at]^=1
            with self.subTest(byte_index=at),self.assertRaises(ReflexError):
                decode(bytes(altered))
        self.refuse(lambda:decode(original+b'!'),'E_BINARY')

    def test_forged_payload_with_correct_sha_but_bad_compiler(self):
        bc=decode(self.binary)
        bc['instructions'][-1]=['REQUEST_REVIEW_SIDE_EFFECT']
        self.refuse(lambda:decode(encode(bc)),'E_INTEGRITY')
        bc=decode(self.binary)
        bc['abi']='reflex-vm/0.9'
        self.refuse(lambda:decode(encode(bc)),'E_INTEGRITY')

    def test_missing_observations_do_not_mask_guard(self):
        env=loads(read('location_anomaly.json'))
        del env['values']['position']
        result=interpreter(self.binary,dumps(env))
        self.assertEqual(result['result']['status'],'UNKNOWN')
        env=loads(read('location_normal.json'))
        env['values']['position']['accuracy_m']=100000
        self.assertEqual(interpreter(self.binary,dumps(env))['result']['status'],'UNKNOWN')

    def test_clock_future_stale_boundaries(self):
        env=loads(read('location_normal.json'))
        env['values']['position']['observed_at']='2026-10-23T12:00:00Z'
        self.assertEqual(interpreter(self.binary,dumps(env))['result']['status'],'NORMAL')
        env['values']['position']['observed_at']='2026-10-23T11:57:00Z'
        self.assertEqual(interpreter(self.binary,dumps(env))['result']['status'],'NORMAL')
        env['values']['position']['observed_at']='2026-10-23T11:56:59Z'
        self.assertEqual(interpreter(self.binary,dumps(env))['result']['status'],'UNKNOWN')

    def test_refusal_for_noncanonical_program_object(self):
        proposal=copy.deepcopy(self.geo)
        proposal['inputs'][17]='Int'
        self.refuse(lambda:validate(proposal),'E_SHAPE')

    def test_250_seeded_int_decision_differentials(self):
        rand=random.Random(0x5245464C4558)
        def make_node(depth=0):
            if depth>2:
                op=rand.choice(['literal','known','range','eq'])
            else:
                op=rand.choice(['literal','known','range','eq','not','and','or'])
            if op=='literal':return {'op':'literal','value':rand.choice(['TRUE','FALSE','UNKNOWN'])}
            if op=='known':return {'op':'known','input':'count'}
            if op=='range':
                a,b=sorted([rand.randint(-40,40),rand.randint(-40,40)])
                return {'op':'compare_range','input':'count','min':a,'max':b}
            if op=='eq':
                return {'op':'compare_eq','left':{'input':'count'},
                        'right':{'const':{'type':'Int','value':rand.randint(-40,40)}}}
            if op=='not':return {'op':'not','arg':make_node(depth+1)}
            return {'op':op,'args':[make_node(depth+1),make_node(depth+1)]}
        for i in range(250):
            p=copy.deepcopy(self.counter)
            p['predicate']=make_node()
            # Capabilities bind exactly to static references, not merely declared inputs.
            p['capabilities']=(['read:count'] if 'count' in json.dumps(p['predicate']) else [])
            b=encode(compile_ir(p))
            val=rand.choice([None,rand.randint(-50,50)])
            env={'schema':'mantle.reflex-input/0.1','clock_utc':'2026-10-23T12:00:00Z',
                 'values':({} if val is None else {'count':val})}
            with self.subTest(iteration=i):
                self.assertEqual(interpreter(b,dumps(env))['result'],oracle(p,dumps(env)))

    def test_pinned_golden_artifact_hashes(self):
        pins=loads(read('golden_hashes.json'))
        self.assertEqual(pins['schema'],'mantle.reflex-golden-hashes/0.1')
        for name,record in pins['programs'].items():
            with self.subTest(program=name):
                p=parse_program(read(name))
                binary=encode(compile_ir(p))
                self.assertEqual(sha256(p),record['canonical_ir_sha256'])
                self.assertEqual(hashlib.sha256(binary).hexdigest(),record['framed_binary_sha256'])
                self.assertEqual(len(binary),record['framed_binary_bytes'])

if __name__=='__main__':
    unittest.main()
