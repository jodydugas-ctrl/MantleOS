import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mantleos.reflex_book import evaluation as ev, cli, vm, admission, registry
from mantleos.reflex_book.bytecode import encode
from mantleos.reflex_book.compiler import compile_ir
from mantleos.reflex_book.parser import parse_program
from mantleos.reflex_book.canonical import loads, dumps, sha256
from mantleos.reflex_book.fixtures import root
from mantleos.reflex_book.errors import ReflexError
from mantleos import console, effects
from mantleos.kpp import core, pantry, workshop


class EvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=root()/'examples/reflex_book'
        cls.program=encode(compile_ir(parse_program((cls.fixture/'location_rule.json').read_bytes())))
        cls.input=loads((cls.fixture/'location_normal.json').read_bytes())

    def record(self):
        return ev.evaluate(self.program,self.input,evaluated_at='2026-10-26T12:00:00Z')

    def reseal(self, record):
        record['digests']['trace_sha256']=sha256(record['trace'])
        record.pop('record_sha256',None)
        record['record_sha256']=sha256(record)
        return record

    def test_same_observation_two_clocks_and_reproduction(self):
        fresh=self.record()
        data=copy.deepcopy(self.input);data['clock_utc']='2026-10-23T12:10:00Z'
        stale=ev.evaluate(self.program,data)
        result=ev.compare(fresh,stale)
        self.assertEqual(result['status'],'COMPARED')
        self.assertTrue(result['same_program']);self.assertTrue(result['same_observation_values'])
        self.assertFalse(result['same_input']);self.assertTrue(result['freshness_changed'])
        self.assertEqual(fresh['trace']['result']['status'],'NORMAL')
        self.assertEqual(stale['trace']['result']['status'],'UNKNOWN')
        self.assertEqual(stale['trace']['reasons'][0]['code'],'OBSERVATION_STALE')
        observations=result['left']['checked']['observations']
        self.assertEqual(observations[0]['age_seconds'],30)
        self.assertEqual(result['right']['checked']['observations'][0]['age_seconds'],630)
        self.assertEqual(result['left']['checked']['guards'][0]['max_age_seconds'],180)
        for record in (fresh,stale):
            self.assertEqual(ev.reproduce(record)['status'],'REPRODUCED')

    def test_inspect_compare_never_evaluate_admit_or_dispatch_effect(self):
        record=self.record()
        with contextlib.ExitStack() as stack:
            for obj,name in ((vm,'run'),(vm,'run_prepared'),(vm,'prepare'),
                             (registry.ExperimentalRegistry,'install'),(admission,'operator_issue_receipt'),
                             (effects.CheckedActionExecutor,'execute')):
                stack.enter_context(patch.object(obj,name,side_effect=AssertionError(name)))
            self.assertEqual(ev.inspect_record(record)['execution'],'NOT_PERFORMED')
            self.assertEqual(ev.compare(record,record)['status'],'COMPARED')

    def test_reproduce_only_bounded_evaluation_and_detects_forged_claim(self):
        record=self.record()
        with patch.object(registry.ExperimentalRegistry,'install',side_effect=AssertionError('install')), \
             patch.object(admission,'operator_issue_receipt',side_effect=AssertionError('approve')), \
             patch.object(effects.CheckedActionExecutor,'execute',side_effect=AssertionError('effect')), \
             patch('socket.socket',side_effect=AssertionError('network')):
            self.assertEqual(ev.reproduce(record)['status'],'REPRODUCED')
        # A self-consistent hash cannot prove the claimed trace came from execution.
        record['trace']['decision']='TRUE'
        record['trace']['result']={'status':'ANOMALY','review_requested':True}
        self.reseal(record)
        self.assertEqual(ev.inspect_record(record)['status'],'INTEGRITY_CHECKED')
        self.assertEqual(ev.reproduce(record)['status'],'MISMATCH')

    def test_tampered_record_and_each_digest_refused(self):
        original=self.record()
        for key in original['digests']:
            record=copy.deepcopy(original);record['digests'][key]='0'*64
            with self.subTest(key=key),self.assertRaises(ReflexError): ev.validate(record)
        for mutate in (lambda r:r.__setitem__('record_sha256','0'*64),
                       lambda r:r.__setitem__('executable_hex','00'+r['executable_hex'][2:]),
                       lambda r:r['inputs'].__setitem__('clock_utc','2026-10-23T13:00:00Z'),
                       lambda r:r.__setitem__('evaluated_at','2026-10-27T12:00:00Z')):
            record=copy.deepcopy(original);mutate(record)
            with self.assertRaises(ReflexError):ev.validate(record)

    def test_versions_limits_and_malformed_shapes_fail_closed(self):
        original=self.record()
        mutations=[lambda r:r.__setitem__('schema','mantle.reflex-evaluation/2'),
                   lambda r:r.__setitem__('authority','APPROVED'),lambda r:r.__setitem__('implementation',[]),
                   lambda r:r.__setitem__('executable_hex','0'*(2*65576+2)),
                   lambda r:r['trace'].__setitem__('decision',[]),
                   lambda r:r['trace'].__setitem__('executed_pcs',[True]),
                   lambda r:r['trace'].__setitem__('reasons',[{'code':'INPUT_MISSING','input':[],'pc':0}]),
                   lambda r:r.__setitem__('trace',None),lambda r:r.__setitem__('extra','bad')]
        for mutate in mutations:
            record=copy.deepcopy(original);mutate(record)
            with self.subTest(record=record.get('schema')),self.assertRaises(ReflexError):ev.validate(record)
        for raw in (b' '*(ev.MAX_RECORD_BYTES+1),b'{"schema":1,"schema":2}',b'{"a":1.1}',b'\xff',b'['*1000):
            with self.assertRaises(ReflexError):ev._load(raw)
        # Larger record contract doesn't weaken program/input 64 KiB bounds.
        with self.assertRaises(ReflexError):loads(b' '*65537)
        record=copy.deepcopy(original);record['padding']='X'*65536
        self.assertEqual(ev._load(dumps(record)),record)

    def test_untrusted_labels_are_escaped_in_both_views(self):
        data=copy.deepcopy(self.input)
        data['values']['position']['source']='synthetic:\x1b[31m\n\u202e'
        record=ev.evaluate(self.program,data)
        text=ev.render(ev.inspect_record(record))
        self.assertNotIn('\x1b',text);self.assertNotIn('\u202e',text)
        self.assertIn('\\u001b',text);self.assertIn('\\u202e',text)
        self.assertEqual(json.loads(text),ev.inspect_record(record))

    def test_incompatible_source_vm_and_program(self):
        record=self.record()
        for change in ('source','toolkit','vm'):
            other=copy.deepcopy(record)
            if change=='source':other['implementation']['source_sha256']='0'*64
            elif change=='toolkit':other['implementation']['toolkit']='unknown/99'
            else:other['trace']['vm_version']='unknown/99'
            self.reseal(other)
            with patch.object(vm,'run_prepared',side_effect=AssertionError('executed')):
                self.assertEqual(ev.compare(record,other)['status'],'INCOMPATIBLE')
                self.assertEqual(ev.reproduce(other)['status'],'INCOMPATIBLE')
        binary=encode(compile_ir(parse_program((self.fixture/'counter_rule.json').read_bytes())))
        other=ev.evaluate(binary,(self.fixture/'counter_normal.json').read_bytes())
        self.assertEqual(ev.compare(record,other)['status'],'INCOMPATIBLE')

    def test_equivalent_input_key_order_cannot_change_freshness_projection(self):
        ir=parse_program((self.fixture/'location_rule.json').read_bytes())
        ir['inputs']['another_position']='GeoFix'
        ir['capabilities'].append('read:another_position')
        ir['predicate']={'op':'and','args':[ir['predicate'],{'op':'known','input':'another_position'}]}
        binary=encode(compile_ir(ir))
        data=copy.deepcopy(self.input)
        data['values']['another_position']=copy.deepcopy(data['values']['position'])
        left=ev.evaluate(binary,data)
        data['values']=dict(reversed(list(data['values'].items())))
        right=ev.evaluate(binary,data)
        result=ev.compare(left,right)
        self.assertTrue(result['same_input'])
        self.assertFalse(result['freshness_changed'])
        self.assertEqual(result['left']['checked']['observations'],result['right']['checked']['observations'])

    def test_cli_installed_style_workflow_and_exclusive_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'demo'
            with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(console.main(['reflex-book','demo','--output',str(output)]),0)
                before=(output/'fresh.json').read_bytes()
                self.assertEqual(cli.main(['demo','--output',str(output)]),2)
                self.assertEqual((output/'fresh.json').read_bytes(),before)
                record=output/'extra.json'
                argv=['evaluate',str(output/'program.rfx'),'--input',str(output/'input.json'),'--output',str(record)]
                self.assertEqual(cli.main(argv),0);saved=record.read_bytes()
                self.assertEqual(cli.main(argv),2);self.assertEqual(saved,record.read_bytes())
                for fmt in ('text','json'):
                    self.assertEqual(cli.main(['inspect',str(record),'--format',fmt]),0)
                    self.assertEqual(cli.main(['compare',str(record),str(output/'stale.json'),'--format',fmt]),0)
                self.assertEqual(cli.main(['reproduce',str(record)]),0)
            with patch.object(cli.os,'fsync',side_effect=OSError('flush failed')):
                with self.assertRaises(OSError):ev.demo(Path(tmp)/'failed')
            self.assertFalse((Path(tmp)/'failed').exists())

    def test_pantry_locator_never_imports_and_new_recipe_unaccepted(self):
        resources=Path(core.__file__).parent/'resources'
        with patch('importlib.import_module',side_effect=AssertionError('candidate import')):
            label=pantry.view(resources,'reflex-book','source')
        self.assertEqual(label['source']['module'],'mantleos.reflex_book')
        recipe=json.loads((resources/'recipes/reflex-reference-inspector.json').read_text())
        core.validate_recipe(recipe)
        self.assertEqual(recipe['anchor_binding'],'none')
        with tempfile.TemporaryDirectory() as tmp:
            workspace=Path(tmp)/'bake'
            workshop.begin(workspace,recipe,resources)
            self.assertEqual(len(workshop.inspection(workspace)['unmet']),10)
            self.assertFalse(workshop.load(workspace)[1]['accepted'])
