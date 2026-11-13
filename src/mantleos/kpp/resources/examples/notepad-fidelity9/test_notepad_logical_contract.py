"""Contract-coverage and externally specified trace tests (not a new Anchor).

Fixtures are authored as expected observations in LOGICAL-TRACE-CORPUS.json.
They do not execute or generate behavior from LOGICAL-CONTRACT.json, and do
not constitute an independent LLM-reasoning qualification.
"""
from pathlib import Path
import json
import os
import tempfile
import unittest

from notepad_document import NeutralDocument, DocumentSnapshot
from notepad_history import NeutralEditHistory
from notepad_input import BlackHoleEditorInput
from notepad_guard import WhiteHoleCommandGuard, CommandRejected
from notepad_files import NeutralFileSession
from notepad_clipboard import NeutralClipboardSelection
from notepad_search import NeutralSearchReplace, ReplaceResult, MatchRange

HERE = Path(__file__).parent
CONTRACT = json.loads((HERE / 'LOGICAL-CONTRACT.json').read_text(encoding='utf-8'))
CASES = json.loads((HERE / 'LOGICAL-TRACE-CORPUS.json').read_text(encoding='utf-8'))['cases']


class TestLogicalEndStateContract(unittest.TestCase):
    def test_nine_anchor_economy_and_exact_identity(self):
        spec = json.loads((HERE / 'anchorforge-spec.json').read_text(encoding='utf-8'))
        manifest = json.loads((HERE / 'blueprint-manifest.json').read_text(encoding='utf-8'))
        ids = {a['id'] for a in spec['responsibilities']}
        self.assertEqual(len(ids), 9)
        self.assertEqual({a['id'] for a in CONTRACT['anchors']}, ids)
        self.assertEqual(CONTRACT['anchor_count'], 9)
        self.assertEqual(CONTRACT['anchor_round'], 9)
        self.assertEqual(len(manifest['sources']), 9)

    def test_all_runtime_actions_have_exactly_one_gate_condition(self):
        rules = CONTRACT['gate_conditions']
        self.assertEqual(len(rules), 19)
        self.assertEqual(len({r['gate_id'] for r in rules}), 19)
        runtime = [r for r in rules if r['phase']=='RUNTIME']
        self.assertEqual(len(runtime), 17)
        self.assertEqual({r['action'] for r in runtime}, set(WhiteHoleCommandGuard.supported_actions))
        self.assertEqual({r['phase'] for r in rules if r['phase']!='RUNTIME'}, {'UI-PROJECTION', 'BUILD-CONFORMANCE'})
        ids = {a['id'] for a in CONTRACT['anchors']}
        for r in rules:
            if r['phase']=='RUNTIME':
                self.assertTrue({'BH-EDITOR-INPUT', 'WH-COMMAND-GUARD'}.issubset(r['participants']))
            self.assertTrue(set(r['participants']).issubset(ids))
            self.assertEqual(len(set(r['participants'])), len(r['participants']))
            self.assertTrue(r['preconditions'])
            self.assertTrue(r['transition'])
            self.assertTrue(r['result'])
            self.assertIn('rejection',r)
        self.assertEqual({s['id'] for s in CONTRACT['state_ownership']},
                         {s['id'] for s in json.loads((HERE / 'anchorforge-spec.json').read_text())['state']})

    def test_trace_corpus_covers_all_actions_and_important_rejections(self):
        used = {step['action'] for c in CASES for step in c['steps']}
        self.assertTrue(set(WhiteHoleCommandGuard.supported_actions).issubset(used))
        rejects = [step for c in CASES for step in c['steps'] if step['outcome'] == 'rejected']
        self.assertGreaterEqual(len(rejects), 8)
        self.assertEqual(len({c['id'] for c in CASES}),len(CASES))

    def test_external_purity_and_effect_attribution(self):
        effect_ids = {e['id'] for e in CONTRACT['runtime_effects']}
        # Current effect IDs may be more specific than compact declarations.
        effect_atoms = {'FS_READ','FS_WRITE','CLIPBOARD_READ','CLIPBOARD_WRITE'}
        used = {e for g in CONTRACT['gate_conditions'] for e in g['external_effects']}
        self.assertEqual(used,effect_atoms)
        self.assertEqual(len(effect_ids),4)
        effectful={'open','save','save-as','copy','cut','paste'}
        self.assertEqual({g['action'] for g in CONTRACT['gate_conditions'] if g['external_effects']},effectful)
        self.assertEqual(set.union(*(set(g['participants']) for g in CONTRACT['gate_conditions'])),
                         {a['id'] for a in CONTRACT['anchors']})
        self.assertIn('UNDETERMINED', CONTRACT['semantics']['unknowns'])
        self.assertIn('not an adopted KPP schema',CONTRACT['relation_to_kpp'])

    def test_all_32_declarative_scenarios_match_current_guard(self):
        for case in CASES:
            with self.subTest(case=case['id']), tempfile.TemporaryDirectory() as d:
                doc = NeutralDocument(case['initial_text'])
                history = NeutralEditHistory(doc)
                files = NeutralFileSession(doc, history)
                clipboard_value = [case.get('clipboard','')]
                def clip_read():
                    if case.get('fail_clipboard_read'):
                        raise OSError('injected clipboard read failure')
                    return clipboard_value[0]
                def clip_write(v):
                    if case.get('fail_clipboard_write'):
                        raise OSError('injected clipboard write failure')
                    clipboard_value[0] = v
                clip = NeutralClipboardSelection(doc, history, clip_read, clip_write)
                search = NeutralSearchReplace(doc, history)
                guard = WhiteHoleCommandGuard()
                alias = {}
                for k, value in case.get('files',{}).items():
                    path=os.path.join(d,k+'.txt')
                    alias['@'+k]=path
                    data=bytes.fromhex(value['hex']) if 'hex' in value else value['text'].encode('utf-8')
                    Path(path).write_bytes(data)
                for k in case.get('expected_files',{}):
                    alias.setdefault('@'+k,os.path.join(d,k+'.txt'))
                for step in case['steps']:
                    payload=step.get('payload')
                    if isinstance(payload,dict):
                        payload={k:alias.get(v,v) if isinstance(v,str) else v for k,v in payload.items()}
                    intent=BlackHoleEditorInput.receive(step['action'],payload)
                    if step['outcome']=='rejected':
                        before=(doc.snapshot(),history.snapshot(),files.snapshot())
                        with self.assertRaises(CommandRejected):
                            guard.execute(intent,doc,history,files,clip,search)
                        self.assertEqual((doc.snapshot(),history.snapshot(),files.snapshot()),before)
                        continue
                    result=guard.execute(intent,doc,history,files,clip,search)
                    if step['outcome']=='selection':
                        self.assertEqual([result.start,result.end],step['selection'])
                    elif step['outcome']=='match':
                        self.assertIsInstance(result,MatchRange)
                        self.assertEqual([result.start,result.end],step['match'])
                    elif step['outcome']=='none':
                        self.assertIsNone(result)
                    elif step['outcome']=='replace':
                        self.assertIsInstance(result,ReplaceResult)
                        self.assertEqual(result.count,step['count'])
                    else:
                        self.assertIsInstance(result,DocumentSnapshot)
                now=doc.snapshot(); hs=history.snapshot(); fs=files.snapshot()
                final=dict(text=now.text,revision=now.revision,dirty=now.dirty,undo_count=hs.undo_count,redo_count=hs.redo_count)
                if 'clipboard' in case['expected_final']:
                    final['clipboard']=clipboard_value[0]
                if 'path' in case['expected_final']:
                    final['path']=next((k for k,v in alias.items() if fs.path==v),None)
                self.assertEqual(final,case['expected_final'])
                for k,text in case.get('expected_files',{}).items():
                    self.assertEqual(Path(alias['@'+k]).read_text(encoding='utf-8'),text)


if __name__=='__main__':
    unittest.main()
