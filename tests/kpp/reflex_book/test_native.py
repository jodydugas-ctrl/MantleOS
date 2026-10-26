"""Native data-only compatibility and prototype admission correction."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from mantleos import cartridge,chromamem,engram,lifecycle
from mantleos.reflex import native,admission,vm
from mantleos.reflex.registry import ExperimentalRegistry
from mantleos.reflex.canonical import dumps
from mantleos.reflex.errors import ReflexError
from mantleos.reflex.parser import parse_program
from .fixtures import workspace
from .test_admission import package,KEYS,NOW,SECRET

FIX=workspace()/'examples/reflex_book'


class NativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='reflex-native-tests-')
        cls.root=Path(cls.temp.name)
        cls.payload=dumps(parse_program((FIX/'location_rule.json').read_bytes()))
        cls.digest=hashlib.sha256(cls.payload).hexdigest()
        cls.body=cls.root/'body'
        native.make_body(cls.payload,cls.body,identity='synthetic-reflex-test')
        cls.carriers={}
        for fmt,name,fn in [('cartridge','sample.vcw',cartridge.pack),('chroma','sample.png',chromamem.export_body)]:
            path=cls.root/name;fn(cls.body,path);cls.carriers[fmt]=path

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_two_native_formats_preserve_founding_and_program_bytes(self):
        for fmt,path in self.carriers.items():
            with self.subTest(fmt=fmt),tempfile.TemporaryDirectory() as t:
                restored=Path(t)/'body'
                (cartridge.unpack if fmt=='cartridge' else chromamem.extract_body)(path,restored)
                cartridge.verify(restored)
                for name in ['BIRTH.json','BIO-SOFTWARE.json','PRIMER/PERSONA.md','PRIMER/COMMANDMENTS.md']:
                    self.assertEqual((restored/name).read_bytes(),(self.body/name).read_bytes())
                self.assertFalse((restored/'TISSUE.json').exists())
                self.assertEqual(engram.read(restored/'ENGRAM.jsonl'),[])
                self.assertFalse((restored/'ARCHIVE.rvcar').exists())
                self.assertEqual((restored/'REFLEX-DATA/program.json').read_bytes(),self.payload)
                self.assertEqual({p.name for p in (restored/'REFLEX-DATA').iterdir()},native.FILES)
                self.assertNotIn(SECRET,(restored/'REFLEX-DATA/manifest.json').read_bytes())
                for name in ('SPEC.md','PROVENANCE.md'):
                    self.assertTrue((restored/'runtime_lib/mantleos/reflex'/name).is_file())

    def test_decode_never_invokes_vm_admission_or_registry(self):
        with patch.object(vm,'run',side_effect=AssertionError('VM invoked')), \
             patch.object(admission,'operator_issue_receipt',side_effect=AssertionError('approval invoked')), \
             patch.object(ExperimentalRegistry,'install',side_effect=AssertionError('install invoked')):
            for fmt,path in self.carriers.items():
                payload,report=native.extract(path,fmt,self.digest)
                self.assertEqual(payload,self.payload)
                self.assertFalse(report['authorized']);self.assertFalse(report['installed']);self.assertFalse(report['executed'])

    def test_wrong_digest_unknown_codec_corruption_and_size(self):
        for fmt,path in self.carriers.items():
            with self.assertRaises(ReflexError):native.extract(path,fmt,'0'*64)
        with self.assertRaises(ReflexError):native.extract(self.carriers['cartridge'],'rgba',self.digest)
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'bad.vcw';path.write_bytes(b'not a cartridge')
            with self.assertRaises(ReflexError):native.extract(path,'cartridge',self.digest)
            path.write_bytes(b'x'*(native.MAX_NATIVE_BYTES+1))
            with self.assertRaises(ReflexError):native.extract(path,'cartridge',self.digest)

    def test_overwrite_refused_and_failed_verify_does_not_publish(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'output.json'
            with self.assertRaises(ReflexError):native.unpack(self.carriers['cartridge'],path,'cartridge','0'*64)
            self.assertFalse(path.exists())
            native.unpack(self.carriers['cartridge'],path,'cartridge',self.digest)
            with self.assertRaises(ReflexError):native.unpack(self.carriers['cartridge'],path,'cartridge',self.digest)
            with self.assertRaises(ReflexError):native.pack(self.payload,path,'cartridge')
            self.assertEqual(path.read_bytes(),self.payload)

    def test_native_archive_traversal_and_truncated_png_refused(self):
        import zipfile
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'unsafe.vcw'
            path.write_bytes(self.carriers['cartridge'].read_bytes())
            with zipfile.ZipFile(path,'a') as archive:archive.writestr('../escaped.json',b'{}')
            with self.assertRaises(ReflexError):native.extract(path,'cartridge',self.digest)
            path=Path(t)/'broken.png';path.write_bytes(self.carriers['chroma'].read_bytes()[:32])
            with self.assertRaises(ReflexError):native.extract(path,'chroma',self.digest)
            self.assertFalse((Path(t)/'escaped.json').exists())

    def test_rehashed_body_cannot_smuggle_authority_or_noncanonical_ir(self):
        import shutil
        for mutation in ('authority','boolean-type','extra','noncanonical','escape-path'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as t:
                body=Path(t)/'body';shutil.copytree(self.body,body)
                p=body/'REFLEX-DATA/manifest.json';value=json.loads(p.read_bytes())
                if mutation=='authority':value['installed']=True
                elif mutation=='boolean-type':value['installed']=0
                elif mutation=='extra':value['approval']='forged'
                elif mutation=='noncanonical':(body/'REFLEX-DATA/program.json').write_bytes(self.payload+b' ')
                else:(body/'REFLEX-DATA/approval.json').write_text('{}')
                p.write_bytes(dumps(value));lifecycle.finalize(body)
                path=Path(t)/'bad.vcw';cartridge.pack(body,path)
                with self.assertRaises(ReflexError):native.extract(path,'cartridge',self.digest)

    def test_native_cli_and_fresh_identity(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'new.vcw'
            args=[sys.executable,'-m','mantleos','kpp','reflex-book']
            p=subprocess.run(args+['native-pack',str(FIX/'location_rule.json'),'--carrier','cartridge','--output',str(path)],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)
            restored=Path(t)/'body';cartridge.unpack(path,restored)
            self.assertNotEqual(json.loads((restored/'BIRTH.json').read_bytes())['id'],'synthetic-reflex-test')
            self.assertFalse(json.loads(p.stdout)['authorized'])
            p=subprocess.run(args+['native-verify',str(path),'--carrier','cartridge','--expected-sha256',self.digest],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)

    def test_original_golden_fixture_bytes_retained(self):
        import mantleos.kpp
        resources=Path(mantleos.kpp.__file__).parent/'resources'
        pins=json.loads((resources/'docs/REFLEX-PROVENANCE.json').read_text())['original_source_files']
        for name,digest in pins.items():
            if name.startswith('examples/reflex_book/'):
                self.assertEqual(hashlib.sha256((workspace()/name).read_bytes()).hexdigest(),digest,name)


class ApprovalRegressionTests(unittest.TestCase):
    def test_placeholder_names_are_valid_proposers(self):
        for proposer in ('test_reviewer','test_issuer','test_nonce'):
            with self.subTest(proposer=proposer):
                c,_,_,a=package(proposed_by=proposer)
                self.assertEqual(admission.verify_approval(c,a,KEYS,NOW)['result'],'APPROVAL_VERIFIED')

    def test_actual_self_approval_and_receipt_field_drift_still_refused(self):
        c,_,_,a=package()
        bad=copy.deepcopy(a);bad['reviewed_by']=c['proposed_by']
        with self.assertRaises(ReflexError):admission.verify_approval(c,bad,KEYS,NOW)
        for edit in ('extra','missing'):
            bad=copy.deepcopy(a)
            if edit=='extra':bad['grant']=True
            else:bad.pop('nonce')
            with self.assertRaises(ReflexError):admission.verify_approval(c,bad,KEYS,NOW)
