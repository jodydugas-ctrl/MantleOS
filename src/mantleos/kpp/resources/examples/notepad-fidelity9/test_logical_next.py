"""Fidelity-9 follow-on: independent logical interpreter and browser shell.

No app implementation is imported as an oracle. The frozen scenario corpus
supplies expected results and the existing 218 tests independently exercise
and compare the actual Notepad implementation.
"""
from copy import deepcopy
from pathlib import Path
from threading import Thread
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import json
import time
import unittest

from logical_engine import LogicalMachine
from logical_shell import Handler, LocalHost

HERE=Path(__file__).resolve().parent
CONTRACT=json.loads((HERE/'LOGICAL-CONTRACT.json').read_text('utf-8'))
ECONOMY=json.loads((HERE/'GATE-ECONOMY.json').read_text('utf-8'))
CASES=json.loads((HERE/'LOGICAL-TRACE-CORPUS.json').read_text('utf-8'))['cases']


def do_case(case):
    files={}
    aliases={}
    for k, value in case.get('files',{}).items():
        name='/virtual/'+k+'.txt'
        aliases['@'+k]=name
        files[name]=bytes.fromhex(value['hex']) if 'hex' in value else value['text'].encode('utf-8')
    for k in case.get('expected_files',{}):
        aliases.setdefault('@'+k,'/virtual/'+k+'.txt')
    machine=LogicalMachine(case['initial_text'],clipboard=case.get('clipboard',''),files=files)
    if case.get('fail_clipboard_read'):machine.fail_effects.add('CLIPBOARD_READ')
    if case.get('fail_clipboard_write'):machine.fail_effects.add('CLIPBOARD_WRITE')
    records=[]
    for step in case['steps']:
        payload=deepcopy(step.get('payload'))
        if type(payload) is dict:
            payload={k:aliases.get(v,v) if type(v) is str else v for k,v in payload.items()}
        response=machine.send(step['action'],payload)
        records.append(response)
        if step['outcome']=='rejected':
            if response['outcome']!='REJECTED_BY_GATE':
                raise AssertionError(f"Expected rejected {step['action']} got {response['outcome']}")
        else:
            if response['outcome']!='PREDICTED_FROM_ANCHORS':
                raise AssertionError(f"Expected success {step['action']} got {response}")
            result=response['result']
            k=step['outcome']
            if result['kind'] != k:
                raise AssertionError(f"Expected {k} got {result}")
            if k=='selection' and result['selection']!=step['selection']:
                raise AssertionError(f"Expected selection {step['selection']} got {result}")
            if k=='match' and result['selection']!=step['match']:
                raise AssertionError(f"Expected match {step['match']} got {result}")
            if k=='replace' and result['count']!=step['count']:
                raise AssertionError(f"Expected replacement count {step['count']} got {result}")
    snap=machine.state()
    final={key:snap[key] for key in ('text','revision','dirty','undo_count','redo_count')}
    if 'clipboard' in case['expected_final']:
        final['clipboard']=snap['clipboard']
    if 'path' in case['expected_final']:
        final['path']=next((k for k,v in aliases.items() if snap['path']==v),None)
    if final!=case['expected_final']:
        raise AssertionError(f"Expected {case['expected_final']} got {final}")
    for k, value in case.get('expected_files',{}).items():
        if machine.files[aliases['@'+k]].decode('utf-8')!=value:
            raise AssertionError(f'Virtual file {k} not saved correctly')
    return machine, records


class TestLogicalInterpreter(unittest.TestCase):
    def test_all_32_source_independent_traces(self):
        self.assertEqual(len(CASES),32)
        for c in CASES:
            with self.subTest(c['id']):
                do_case(c)

    def test_replay_determinism(self):
        for c in CASES:
            with self.subTest(c['id']):
                first,rec1=do_case(c)
                second,rec2=do_case(c)
                self.assertEqual(first.logical_state(),second.logical_state())
                self.assertEqual(rec1,rec2)

    def test_gate_economy_preserves_every_clause_without_duplicate_families(self):
        m=LogicalMachine()
        self.assertEqual(m.economy['gate_family_count'],len(m.economy['gate_families']))
        self.assertEqual(m.economy['gate_family_count'],9)
        self.assertEqual(m.economy['source_condition_count'],19)
        all_clauses=[c for g in m.economy['gate_families'] for c in g['clauses']]
        self.assertEqual(set(all_clauses),{c['gate_id'] for c in CONTRACT['gate_conditions']})
        self.assertEqual(len(all_clauses),len(set(all_clauses)))
        self.assertEqual(len(set(g['id'] for g in m.economy['gate_families'])),9)
        self.assertTrue(all(m.gates_for.values()))
        self.assertEqual(set(m.clauses),set(CONTRACT['conformance']['expected_actions']))

    def test_gate_family_contract_cannot_lose_one_clause(self):
        from unittest.mock import patch
        from logical_engine import Rejected
        bad=deepcopy(ECONOMY)
        bad['gate_families'][1]['clauses'].pop()
        import logical_engine
        original_read=Path.read_text
        def fake_read(path, *args, **kwargs):
            if str(path).endswith('GATE-ECONOMY.json'):
                return json.dumps(bad)
            return original_read(path,*args,**kwargs)
        with patch.object(Path,'read_text',fake_read):
            with self.assertRaises(Rejected):logical_engine.LogicalMachine()

    def test_invalid_boolean_index_never_mutates(self):
        m=LogicalMachine('abc')
        before=m.logical_state()
        r=m.send('insert',{'offset':True,'text':'X'})
        self.assertEqual(r['outcome'],'REJECTED_BY_GATE')
        self.assertEqual(before,m.logical_state())

    def test_unavailable_effect_preserves_document_and_baseline(self):
        m=LogicalMachine('abc')
        m.fail_effects.add('FS_WRITE')
        before=m.logical_state()
        r=m.send('save-as',{'path':'/virtual/test.txt','overwrite':False})
        self.assertEqual(r['outcome'],'REJECTED_BY_GATE')
        self.assertEqual(m.logical_state(),before)

    def test_llm_packet_contains_truth_without_expected_answer_or_python_source(self):
        m=LogicalMachine('hello')
        m.send('insert',{'offset':5,'text':' world'})
        p=m.reasoning_prompt()
        self.assertIn('"action": "insert"',p)
        self.assertIn('"text": "hello"',p)
        self.assertIn('"gate_families":',p)
        self.assertNotIn('"text": "hello world"',p)
        self.assertNotIn('def _dispatch',p)
        self.assertNotIn('notepad_guard.py',p)

    def test_all_known_initial_state_included_for_history_prediction(self):
        m=LogicalMachine('a')
        m.send('edit','b');m.send('undo',None)
        m.send('redo',None)
        pkt=m.last_packet
        self.assertEqual(pkt['known_state_before']['text'],'a')
        self.assertEqual(pkt['known_state_before']['redo_stack'],[['a','b']])
        self.assertEqual(pkt['stimulus']['action'],'redo')

    def test_virtual_effect_distinguished_from_actual_host_effect(self):
        m=LogicalMachine('note')
        r=m.send('save-as',{'path':'/virtual/a.txt','overwrite':False})
        self.assertEqual(r['outcome'],'PREDICTED_FROM_ANCHORS')
        self.assertEqual(m.files['/virtual/a.txt'],b'note')
        self.assertEqual(r['trace']['effect_scope'],'VIRTUAL_IN_MEMORY_ONLY')
        self.assertIn('VIRTUAL_ONLY',m.reasoning_prompt())

    def test_independent_runner_imports_no_app_source(self):
        source=(HERE/'logical_engine.py').read_text('utf-8')
        self.assertNotIn('from notepad_',source)
        self.assertNotIn('import notepad_',source)
        self.assertNotIn('subprocess.',source)
        self.assertNotIn('eval(',source)
        self.assertNotIn('exec(',source)


class TestBrowserShell(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=LocalHost(('127.0.0.1',0),Handler)
        cls.url=f'http://127.0.0.1:{cls.server.server_port}'
        cls.thread=Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(self,path,body=None):
        init={'data':json.dumps(body).encode('utf-8'), 'headers':{'Content-Type':'application/json'},'method':'POST'} if body is not None else {}
        with urlopen(Request(self.url+path,**init),timeout=3) as r:
            return r.status, r.headers.get('Content-Type'), r.read().decode('utf-8')

    def test_shell_loads_all_static_resources_and_real_http_routes(self):
        for path,media in [('/','text/html'),('/shell.css','text/css'),('/shell.js','application/javascript')]:
            with self.subTest(path):
                status,ctype,contents=self.request(path)
                self.assertEqual(status,200)
                self.assertIn(media,ctype)
                self.assertGreater(len(contents),100)
        _,_,state=self.request('/api/state')
        self.assertEqual(json.loads(state)['gate_family_count'],9)

    def test_interactive_sequence_and_llm_packet_no_app_source(self):
        self.request('/api/reset',{})
        _,_,raw=self.request('/api/command',{'action':'edit','payload':'Hello'})
        self.assertEqual(json.loads(raw)['state']['text'],'Hello')
        _,_,raw=self.request('/api/command',{'action':'insert','payload':{'offset':5,'text':' World'}})
        r=json.loads(raw)
        self.assertEqual(r['state']['text'],'Hello World')
        self.assertEqual(r['trace']['action_clause'],'G-CMD-02')
        _,_,packet=self.request('/api/packet')
        p=json.loads(packet)['prompt']
        self.assertIn('"text": "Hello"',p)
        self.assertNotIn('"text": "Hello World"',p)
        _,_,raw=self.request('/api/command',{'action':'undo','payload':None})
        self.assertEqual(json.loads(raw)['state']['text'],'Hello')

    def test_open_seeded_browser_text_and_virtual_save(self):
        self.request('/api/reset',{})
        self.request('/api/seed-file',{'path':'/virtual/hello.txt','text':'Loaded 📝'})
        _,_,raw=self.request('/api/command',{'action':'open','payload':{'path':'/virtual/hello.txt','discard':False}})
        self.assertEqual(json.loads(raw)['state']['text'],'Loaded 📝')
        _,_,raw=self.request('/api/command',{'action':'save','payload':None})
        self.assertFalse(json.loads(raw)['state']['dirty'])

    def test_rejected_server_request_does_not_bypass_contract(self):
        self.request('/api/reset',{})
        _,_,raw=self.request('/api/command',{'action':'exec','payload':{'anything':'yes'}})
        self.assertEqual(json.loads(raw)['outcome'],'REJECTED_BY_GATE')
        self.assertEqual(json.loads(raw)['state']['text'],'Hello, Anchor!')
        with self.assertRaises(HTTPError):self.request('/api/seed-file',{'path':'../real.txt','text':'X'})


if __name__=='__main__':unittest.main()
