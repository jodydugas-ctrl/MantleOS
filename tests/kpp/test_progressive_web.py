"""Fixed-oracle tests for explicit product/delivery classification and non-Notepad previews."""
import copy
import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from mantleos.kpp.core import KPPError, find_repo_root, read_json, validate_recipe
from mantleos.kpp.workshop import begin, load, inspection, install_module, finish

ROOT=find_repo_root()
CALC=read_json(ROOT/'recipes/progressive-calculator.json')


class ProgressivePreviewTests(unittest.TestCase):
    def test_custom_id_immediately_stages_live_shell_not_notepad(self):
        with tempfile.TemporaryDirectory() as td:
            recipe=copy.deepcopy(CALC)
            recipe['id']='another-calculator-bake'
            ws=Path(td)/'ws'
            state=begin(ws,recipe,ROOT)
            self.assertEqual(state['preview_kind'],'progressive-web')
            self.assertEqual(state['phase'],'BUILDING')
            self.assertEqual(load(ws)[0]['id'],recipe['id'])
            html=(ws/'app/index.html').read_text()
            self.assertIn('Calculator',html)
            self.assertNotIn('Progressive Notes',html)
            self.assertEqual(inspection(ws)['preview']['interactivity'],'NOT_VERIFIED')
            self.assertFalse(inspection(ws)['all_required_satisfied'])
            with self.assertRaises(KPPError):finish(ws)

    def test_recipe_identity_is_independent_of_construction_and_delivery(self):
        recipe=copy.deepcopy(CALC)
        self.assertEqual(validate_recipe(recipe)['mode'],'chase')
        self.assertEqual(recipe['product_kind'],'biosoftware')
        self.assertEqual(recipe['capabilities'],{'agent':False,'mind':False,'mantleos_splice':False})
        recipe['product_kind']='appai'
        with self.assertRaisesRegex(KPPError,'splice'):validate_recipe(recipe)
        recipe['product_kind']='bioagent'
        with self.assertRaisesRegex(KPPError,'agent'):validate_recipe(recipe)
        recipe['capabilities']['agent']=True
        validate_recipe(recipe)

    def test_product_and_preview_schema_validation_negative(self):
        for field, value in [('product_kind','anything'),('delivery_mode','stream'),('capabilities',{'mind':'false'})]:
            bad=copy.deepcopy(CALC);bad[field]=value
            with self.subTest(field=field),self.assertRaises(KPPError):validate_recipe(bad)
        bad=copy.deepcopy(CALC);bad.pop('preview')
        with self.assertRaisesRegex(KPPError,'preview contract'):validate_recipe(bad)
        bad=copy.deepcopy(CALC);bad['delivery_mode']='artifact'
        with self.assertRaises(KPPError):validate_recipe(bad)
        bad=copy.deepcopy(CALC);bad.pop('preview');bad['delivery_mode']='bundled-notepad'
        with self.assertRaisesRegex(KPPError,'Unsupported delivery'):validate_recipe(bad)
        bad=copy.deepcopy(CALC);bad['preview']['assets']['base.js']['path']='previews/../../private.js'
        with self.assertRaises(KPPError):validate_recipe(bad)
        bad=copy.deepcopy(CALC);bad['preview']['assets']['base.js']['sha256']='z'*64
        with self.assertRaises(KPPError):validate_recipe(bad)
        bad=copy.deepcopy(CALC);bad['preview']['assets']['extra.js']={'path':'previews/calculator/square.js','sha256':'0'*64}
        with self.assertRaises(KPPError):validate_recipe(bad)

    def test_pinned_preview_rejects_modified_seed_before_workspace_is_created(self):
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td)/'repo';(repo/'previews/calculator').mkdir(parents=True)
            for name in ('index.html','base.js','style.css'):
                (repo/'previews/calculator'/name).write_bytes((ROOT/'previews/calculator'/name).read_bytes())
            (repo/'previews/calculator/base.js').write_text('changed')
            from mantleos.kpp.workshop import preview_files
            with self.assertRaisesRegex(KPPError,'pin mismatch'):
                preview_files(CALC,repo)
            # The workspace is untouched if a seed fails validation.
            from unittest.mock import patch
            with patch('mantleos.kpp.workshop.preview_files') as staged:
                staged.side_effect=KPPError('Preview seed source pin mismatch')
                ws=Path(td)/'candidate'
                with self.assertRaisesRegex(KPPError,'pin mismatch'):begin(ws,CALC,ROOT)
                self.assertFalse(ws.exists())

    def test_actual_seed_hashes_match_recipe(self):
        for name, info in CALC['preview']['assets'].items():
            self.assertEqual(hashlib.sha256((ROOT/info['path']).read_bytes()).hexdigest(),info['sha256'],name)

    def test_custom_preview_retains_seed_and_current_workspace_evidence_when_module_installs(self):
        with tempfile.TemporaryDirectory() as td:
            ws=Path(td)/'ws';begin(ws,CALC,ROOT)
            previous=(ws/'app/index.html').read_bytes()
            previous_base=(ws/'app/base.js').read_bytes()
            state=install_module(ws,'square',ROOT/'previews/calculator/square.js')
            self.assertEqual(state['modules'][0]['id'],'square')
            self.assertEqual(state['revision'],2)
            self.assertEqual((ws/'app/index.html').read_bytes(),previous)
            self.assertEqual((ws/'app/base.js').read_bytes(),previous_base)
            self.assertEqual(inspection(ws)['preview']['surface'],'STAGED')
            self.assertEqual(inspection(ws)['accepted'],0)

    def test_preview_tamper_fails_closed_and_prevents_additions(self):
        with tempfile.TemporaryDirectory() as td:
            ws=Path(td)/'ws';begin(ws,CALC,ROOT)
            (ws/'app/base.js').write_text('modified')
            with self.assertRaisesRegex(KPPError,'Published preview'):load(ws)
            with self.assertRaises(KPPError):install_module(ws,'square',ROOT/'previews/calculator/square.js')

    def test_modified_preview_state_claim_cannot_rewrite_recipe_source_pin(self):
        from mantleos.kpp.core import write_json
        with tempfile.TemporaryDirectory() as td:
            ws=Path(td)/'ws';begin(ws,CALC,ROOT)
            (ws/'app/base.js').write_text('forged')
            state=read_json(ws/'state.json')
            state['preview_asset_sha256']['base.js']=hashlib.sha256(b'forged').hexdigest()
            write_json(ws/'state.json',state)
            with self.assertRaisesRegex(KPPError,'pins disagree'):load(ws)

    def test_symlink_preview_directory_refused(self):
        with tempfile.TemporaryDirectory() as td:
            ws=Path(td)/'ws';begin(ws,CALC,ROOT)
            external=Path(td)/'outside'
            (ws/'app').rename(external)
            try:(ws/'app').symlink_to(external,target_is_directory=True)
            except (OSError,NotImplementedError):self.skipTest('symlinks not supported')
            with self.assertRaisesRegex(KPPError,'Unsafe progressive preview directory'):load(ws)

    def test_notepad_and_calculator_use_one_runtime_and_artifacts_have_none(self):
        with tempfile.TemporaryDirectory() as td:
            note=Path(td)/'notes'
            begin(note,read_json(ROOT/'recipes/notepad-demo.json'),ROOT)
            self.assertEqual(load(note)[1]['preview_kind'],'progressive-web')
            install_module(note,'edit',ROOT/'previews/notepad/edit.js')
            self.assertEqual((note/'app/runtime.js').read_bytes(),(Path(__import__('mantleos.kpp', fromlist=['x']).__file__).parent/'assets/progressive.js').read_bytes())
            plain=Path(td)/'plain'
            begin(plain,read_json(ROOT/'recipes/portable-memory-bake.json'),ROOT)
            self.assertEqual(load(plain)[1]['preview_kind'],'none')

    def test_server_serves_only_pinned_custom_assets_and_sanitizes_request_paths(self):
        with tempfile.TemporaryDirectory() as td:
            ws=Path(td)/'ws';begin(ws,CALC,ROOT)
            with socket.socket() as s:
                s.bind(('127.0.0.1',0));port=s.getsockname()[1]
            env={**os.environ,'PYTHONPATH':str(Path(__import__('mantleos').__file__).parent.parent)}
            proc=subprocess.Popen([sys.executable,'-m','mantleos','kpp','serve','--workspace',str(ws),'--port',str(port)],
                                  cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            try:
                base=f'http://127.0.0.1:{port}'
                for _ in range(60):
                    try:
                        with urllib.request.urlopen(base+'/snapshot',timeout=.25) as response:
                            self.assertEqual(response.status,200)
                        break
                    except OSError:
                        if proc.poll() is not None:self.fail('preview exited early')
                        time.sleep(.05)
                else:self.fail('preview did not start')
                for path, expected in [('/',b'Calculator'),('/base.js',b'CalculatorBody'),('/style.css',b'font-family'),('/runtime.js',b'define')]:
                    with urllib.request.urlopen(base+path,timeout=2) as resp:
                        self.assertEqual(resp.status,200)
                        self.assertIn(expected,resp.read())
                        self.assertEqual(resp.headers['X-Content-Type-Options'],'nosniff')
                for path in ('/missing','/previews/calculator/base.js','/app/base.js','/../../KPP.md'):
                    with self.assertRaises(urllib.error.HTTPError) as ctx:
                        urllib.request.urlopen(base+path,timeout=2)
                    self.assertEqual(ctx.exception.code,404)
                with urllib.request.urlopen(base+'/snapshot') as response:
                    shot=json.loads(response.read())
                    self.assertEqual(shot['phase'],'BUILDING')
                    self.assertEqual(shot['report']['accepted'],0)
            finally:
                proc.terminate()
                try:proc.wait(timeout=3)
                except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=3)

if __name__=='__main__':unittest.main()
