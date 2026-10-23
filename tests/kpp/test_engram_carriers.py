"""Synthetic fresh-birth, encoding equivalence and publication boundaries."""
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from mantleos import cartridge, chromamem, engram, lifecycle
from mantleos.kpp import engram_carriers as ec
from mantleos.kpp import artifacts
from mantleos.kpp.pantry import view, discover

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'src/mantleos').is_dir())
PANTRY=ec.PERSONA.parent.parent

class EngramCarrierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.temp.cleanup)
        cls.work=Path(cls.temp.name);cls.body=cls.work/'body'
        ec.fresh_body(cls.body,identity='synthetic-encoding-test')
        ec.encode(cls.body,cls.work/'sample.vcw','vcw')
        ec.encode(cls.body,cls.work/'sample.png','chroma')

    def test_equivalent_fresh_roundtrips(self):
        cartridge.unpack(self.work/'sample.vcw',self.work/'restored-vcw')
        chromamem.extract_body(self.work/'sample.png',self.work/'restored-chroma')
        for name in ('BIRTH.json','ENGRAM.jsonl','SYSTEMS.json','PRIMER/PERSONA.md'):
            self.assertEqual((self.work/'restored-vcw'/name).read_bytes(),(self.work/'restored-chroma'/name).read_bytes())
        for body in (self.work/'restored-vcw',self.work/'restored-chroma'):
            cartridge.verify(body)
            self.assertEqual((body/'PRIMER/PERSONA.md').read_text(encoding='utf-8'),ec.PERSONA.read_text(encoding='utf-8'))
            self.assertFalse((body/'ARCHIVE.rvcar').exists())
            self.assertFalse((body/'runtime_lib/mantleos/kpp/resources/examples/engrams/artifacts').exists())
            # Initialization is empty in the current builder; no remembered history.
            self.assertEqual(engram.read(body/'ENGRAM.jsonl'),[])
            before=(body/'ENGRAM.jsonl').read_bytes()
            lifecycle.admit(body,'synthetic-memory',{'text':'synthetic observation'},expected_head=engram.head(body/'ENGRAM.jsonl'))
            self.assertTrue((body/'ENGRAM.jsonl').read_bytes().startswith(before))
            prior=(body/'ENGRAM.jsonl').read_bytes()
            lifecycle.admit(body,'synthetic-memory',{'text':'second observation'},expected_head=engram.head(body/'ENGRAM.jsonl'))
            self.assertTrue((body/'ENGRAM.jsonl').read_bytes().startswith(prior))
            saved=self.work/(body.name+'.png')
            ec.encode(body,saved,'chroma')
            restored=self.work/(body.name+'-saved')
            chromamem.extract_body(saved,restored)
            self.assertEqual(engram.read(body/'ENGRAM.jsonl'),engram.read(restored/'ENGRAM.jsonl'))

    def test_default_and_custom_persona(self):
        out=self.work/'custom'
        ec.fresh_body(out,persona='Synthetic custom persona.',persona_name='Custom',identity='synthetic-custom')
        self.assertEqual((out/'PRIMER/PERSONA.md').read_text(encoding='utf-8'),'Synthetic custom persona.\n')
        self.assertNotIn('Raven',(out/'PRIMER/PERSONA.md').read_text(encoding='utf-8'))
        with self.assertRaises(ValueError):ec.fresh_body(self.work/'bad',persona='custom')

    def test_selection_and_refusals(self):
        recipe=json.loads((PANTRY/'recipes/raven-engram-vcw.json').read_text(encoding='utf-8'))
        self.assertEqual(ec.selection(recipe),'vcw')
        for choices in ([],['engram-continuity'],['engram-continuity',*ec.CARRIERS]):
            with self.assertRaises(ValueError):ec.selection({**recipe,'ingredients':choices})
        for output,encoding in [(self.work/'sample.vcw','vcw'),(self.work/'bad.png','vcw'),(self.work/'bad.vcw','unknown')]:
            with self.assertRaises(ValueError):ec.encode(self.body,output,encoding)

    def test_fresh_identity_and_cli(self):
        import subprocess,sys,os
        recipe=PANTRY/'recipes/raven-engram-vcw.json'
        outputs=[]
        for number in range(2):
            output=self.work/('cli-'+str(number)+'.vcw')
            result=subprocess.run([sys.executable,'-m','mantleos','kpp','engram','create','--recipe',str(recipe),'--output',str(output)],
                capture_output=True,env={**os.environ,'PYTHONPATH':str(ROOT/'src'),'PYTHONUTF8':'1'},timeout=90)
            self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))
            outputs.append(json.loads(result.stdout)['identity'])
        self.assertNotEqual(*outputs)

    def test_corrupt_carriers(self):
        bad=self.work/'corrupt.png'
        raw=bytearray((self.work/'sample.png').read_bytes());raw[80]^=1;bad.write_bytes(raw)
        with self.assertRaises(ValueError):chromamem.inspect(bad)
        bad=self.work/'corrupt.vcw';bad.write_bytes(b'not a cartridge')
        with self.assertRaises((ValueError,zipfile.BadZipFile)):cartridge.unpack(bad,self.work/'bad-extract')

    def test_discovery_and_source_pins(self):
        for ident in ec.CARRIERS:
            result=view(PANTRY,ident,'source')
            self.assertEqual(result['source']['integrity'],'PIN_MATCH')
            self.assertTrue(discover(PANTRY,query=ident)['matches'])

    def test_artifact_inventory_is_explicit(self):
        self.assertEqual(len(artifacts.inventory(ROOT)),3)
        with tempfile.TemporaryDirectory() as work:
            folder=Path(work)/artifacts.DIRECTORY;folder.mkdir(parents=True)
            (folder/'unexpected.vcw').write_bytes(b'private')
            with self.assertRaises((ValueError,OSError)):artifacts.inventory(work)
