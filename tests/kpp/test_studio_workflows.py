"""Operational state boundaries; source/runtime parity remains a separate gate."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from mantleos.studio_workflows import Conflict, MAX_BYTES, WorkflowStore, document, serve


def workflow():
    return {'name': 'Invoice routing', 'nodes': [
        {'id': '1-input', 'name': 'Input', 'type': 'n8n-nodes-base.manualTrigger', 'position': [0, 0], 'parameters': {}},
        {'id': '2-if', 'name': 'If', 'type': 'n8n-nodes-base.if', 'typeVersion': 2.3, 'position': [240, 0], 'parameters': {'conditions': {'value': '={{ $json.total }}'}}},
    ], 'connections': {'Input': {'main': [[{'node': 'If', 'type': 'main', 'index': 0}]]}},
        'pinData': {'Input': [{'json': {'total': 42}}]}, 'settings': {'executionOrder': 'v1'}}


class WorkflowTests(unittest.TestCase):
    def create(self, store, value=None, request_id='request-create'):
        return store.mutate({'action': 'create', 'request_id': request_id, 'value': value or workflow()}, owner=True)

    def mutate(self, store, action, current, **extra):
        return store.mutate({'action': action, 'request_id': 'request-'+action+'-'+current['revision'],
                             'id': current['id'], 'revision': current['revision'], **extra}, owner=True)

    def execution_request(self, saved):
        return {'request_id': 'manual-run', 'workflow_id': saved['id'],
                'version_id': saved['versionId'], 'revision': saved['revision'],
                'trigger': 'Input', 'destination': 'If'}

    def test_execution_retains_exact_saved_version_and_committed_observation(self):
        with tempfile.TemporaryDirectory() as td:
            store = WorkflowStore(td)
            saved = self.create(store)
            request = self.execution_request(saved)
            with self.assertRaises(PermissionError):
                store.execution_start(request, source_pin='1'*64)
            with self.assertRaises(ValueError):
                store.execution_start({**request, 'nodes': []}, owner=True, source_pin='1'*64)
            self.assertEqual(store.execution_list(workflow_id=saved['id']), {'data': [], 'count': 0})
            run = store.execution_start(request, owner=True, source_pin='1'*64)
            self.assertEqual(run['status'], 'running')
            self.assertEqual(run['workflowData']['nodes'], saved['nodes'])
            self.assertEqual(run['selection'], {'trigger': 'Input', 'destination': 'If'})
            newer = self.mutate(store, 'update', saved, value={**saved, 'name': 'Edited'})
            replay = WorkflowStore(td).execution_start(request, owner=True, source_pin='1'*64)
            self.assertEqual(replay['id'], run['id'])
            self.assertNotIn('claim', replay)
            with self.assertRaises(Conflict):
                store.execution_start({**request, 'request_id': 'stale-start'}, owner=True, source_pin='1'*64)
            with self.assertRaises(Conflict):
                store.execution_start({**request, 'destination': None}, owner=True, source_pin='1'*64)

            observation = {'resultData': {'runData': {'If': [{'data': {'main': [[], [{'json': {'total': 42}}]]}}]}}}
            finish = {'claim': run['claim'], 'status': 'success', 'result': observation,
                      'source_pin': '1'*64, 'owner': True}
            for override in ({'claim': 'forged'}, {'source_pin': '2'*64}, {'owner': False}):
                with self.subTest(override=override), self.assertRaises(PermissionError):
                    store.execution_finish(run['id'], **{**finish, **override})
            done = store.execution_finish(run['id'], **finish)
            reopened = WorkflowStore(td)
            self.assertEqual(reopened.execution_finish(run['id'], **finish), done)
            self.assertEqual(reopened.execution_get(run['id']), done)
            self.assertEqual(done['workflowVersionId'], saved['versionId'])
            self.assertEqual(done['workflowData']['name'], saved['name'])
            self.assertEqual(done['data'], observation)
            self.assertEqual(reopened.get(saved['id']), newer)
            self.assertNotIn('claim', done)
            with self.assertRaises(Conflict):
                reopened.execution_finish(run['id'], **{**finish, 'result': {}})

    def test_execution_claim_is_single_use_and_deletion_drops_history(self):
        with tempfile.TemporaryDirectory() as td:
            store = WorkflowStore(td)
            saved = self.create(store)
            request = self.execution_request(saved)

            def start(_):
                return WorkflowStore(td).execution_start(request, owner=True, source_pin='1'*64)

            with ThreadPoolExecutor(max_workers=4) as pool:
                runs = list(pool.map(start, range(4)))
            claims = [run for run in runs if 'claim' in run]
            self.assertEqual(len(claims), 1)
            run, = claims
            self.assertEqual({item['id'] for item in runs}, {run['id']})
            archived = self.mutate(store, 'archive', saved)
            with self.assertRaises(Conflict):
                self.mutate(store, 'delete', archived)
            store.execution_finish(run['id'], claim=run['claim'], status='canceled',
                                   result={'stop': 'confirmed'}, owner=True, source_pin='1'*64)
            self.assertEqual(store.execution_list(workflow_id=saved['id'])['data'][0]['status'], 'canceled')
            self.mutate(store, 'delete', archived)
            with self.assertRaises(KeyError):
                store.execution_get(run['id'])
            with closing(sqlite3.connect(store.path)) as db:
                self.assertEqual(db.execute('SELECT version,claim,result FROM workflow_executions').fetchall(),
                                 [(None, None, None)])
            other = self.create(store, request_id='other-workflow')
            with self.assertRaises(Conflict):
                store.execution_start(self.execution_request(other), owner=True, source_pin='1'*64)

    def test_execution_worker_requires_trusted_source_and_checks_observation_integrity(self):
        with tempfile.TemporaryDirectory() as td:
            store = WorkflowStore(td)
            saved = self.create(store)
            packet = {'id': 'local-op', 'op': 'execution_start', 'args': self.execution_request(saved)}

            def call(value, **options):
                output = io.StringIO()
                serve(store, io.BytesIO((json.dumps(value)+'\n').encode()), output, **options)
                return json.loads(output.getvalue())

            self.assertFalse(call(packet)['ok'])
            result = call(packet, execution_source='1'*64)
            self.assertTrue(result['ok'])
            run = result['result']
            committed = call({'id': 'local-op', 'op': 'execution_finish', 'args': {
                'run_id': run['id'], 'claim': run['claim'], 'status': 'error', 'result': {'code': 'FIXTURE_ERROR'},
            }}, execution_source='1'*64)
            self.assertTrue(committed['ok'])
            with closing(sqlite3.connect(store.path)) as db, db:
                db.execute("UPDATE workflow_executions SET status='canceled' WHERE id=?", (run['id'],))
            with self.assertRaisesRegex(ValueError, 'result integrity'):
                store.execution_get(run['id'])
            with closing(sqlite3.connect(store.path)) as db, db:
                db.execute("UPDATE workflow_executions SET status='error',result='{}' WHERE id=?", (run['id'],))
            with self.assertRaisesRegex(ValueError, 'result integrity'):
                store.execution_get(run['id'])

    def test_execution_history_filters_preserve_current_set_and_paging_across_new_runs(self):
        with tempfile.TemporaryDirectory() as td:
            store = WorkflowStore(td)
            old = self.create(store)

            def reserve(saved, key, time, outcome=None):
                payload = {**self.execution_request(saved), 'request_id': key}
                with patch('mantleos.studio_workflows._now', return_value=time):
                    run = store.execution_start(payload, owner=True, source_pin='1'*64)
                    if outcome:
                        store.execution_finish(run['id'], owner=True, source_pin='1'*64,
                                               claim=run['claim'], status=outcome, result={'resultData': {}})
                return run['id']

            first_time = '2026-01-01T14:00:00.000000+00:00'
            canceled = reserve(old, 'old-run', first_time, 'canceled')
            new = self.mutate(store, 'update', old, value={**old, 'name': 'New workflow name'})
            successful = reserve(new, 'new-run', '2026-01-01T14:00:01.000000+00:00', 'success')
            running = reserve(new, 'current-run', '2026-01-01T14:00:02.000000+00:00')
            scope = {'workflowId': old['id']}
            first = store.execution_page(query=scope, limit=1)
            self.assertEqual([row['id'] for row in first['data']], [running, successful])
            self.assertEqual(first['count'], 2)
            self.assertTrue(first['next_cursor'])
            reserve(new, 'inserted-run', '2026-01-01T14:00:03.000000+00:00', 'success')
            second = store.execution_page(query=scope, limit=1, cursor=first['next_cursor'])
            self.assertEqual([row['id'] for row in second['data']], [canceled])
            self.assertEqual(second['data'][0]['workflowName'], 'New workflow name')
            self.assertNotIn('data', second['data'][0])
            self.assertEqual(second['count'], 3)
            self.assertEqual(store.execution_page(query=scope, limit=1,
                             cursor=second['next_cursor'])['data'], [])
            filtered = store.execution_page(query={**scope, 'workflowVersionId': old['versionId'],
                'startedAfter': '2026-01-01T10:00:00-04:00', 'startedBefore': '2026-01-01T14:00:00Z',
                'status': ['canceled'], 'mode': 'manual'})
            self.assertEqual([row['id'] for row in filtered['data']], [canceled])
            self.assertEqual(store.execution_page(query={'status': ['new', 'waiting']})['count'], 0)
            self.assertEqual(store.execution_page(query={'mode': 'trigger'})['count'], 0)
            self.assertEqual([item['versionId'] for item in store.execution_versions(old['id'])],
                             [new['versionId'], old['versionId']])
            for kwargs in ({'cursor': 'bad cursor'}, {'query': {'startedAfter': '2026-01-01'}},
                           {'query': {'status': 'success'}}, {'query': {'annotationTags': ['unknown']}}):
                with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                    store.execution_page(**{'query': scope, **kwargs})

    def test_read_only_empty_store_creates_no_state(self):
        with tempfile.TemporaryDirectory() as td:
            directory = Path(td)/'not-created'
            self.assertEqual(WorkflowStore(directory).list(), {'data': [], 'count': 0})
            with self.assertRaises(KeyError):
                WorkflowStore(directory).get('missing')
            self.assertFalse(directory.exists())

    def test_health_is_read_only_and_refuses_unrelated_storage(self):
        with tempfile.TemporaryDirectory() as td:
            directory=Path(td)/'new-store';store=WorkflowStore(directory)
            self.assertEqual(store.health(),{'status':'ok','workflow_execution':'UNAVAILABLE'})
            self.assertFalse(directory.exists())
            self.create(store)
            with closing(sqlite3.connect(store.path)) as db,db:db.execute('PRAGMA application_id=12345')
            with self.assertRaisesRegex(ValueError,'Unsupported workflow store'):store.health()

    def test_editor_allocated_id_survives_restart_and_replay(self):
        with tempfile.TemporaryDirectory() as td:
            store=WorkflowStore(td)
            request={'action':'create','request_id':'draft-first-save',
                     'id':'3FoW8HN8RzM9UgQR','value':{**workflow(),'id':'imported-id-is-data'}}
            created=store.mutate(request,owner=True)
            self.assertEqual(created['id'],request['id'])
            self.assertEqual(WorkflowStore(td).get(request['id']),created)
            self.assertEqual(WorkflowStore(td).mutate(request,owner=True),created)
            with self.assertRaises(Conflict):
                store.mutate({**request,'id':'different-id'},owner=True)
            with self.assertRaises(Conflict):
                store.mutate({**request,'request_id':'other-save'},owner=True)
            # Legacy creation still allocates a fresh identity, even if imported
            # document data has the same ID as a current workflow.
            legacy=self.create(store,{**workflow(),'id':request['id']})
            self.assertNotEqual(legacy['id'],request['id'])

    def test_requested_id_never_resurrects_removed_workflow(self):
        with tempfile.TemporaryDirectory() as td:
            store=WorkflowStore(td)
            request={'action':'create','request_id':'draft-save','id':'explicit-id','value':workflow()}
            created=store.mutate(request,owner=True)
            archived=self.mutate(store,'archive',created)
            self.mutate(store,'delete',archived)
            with self.assertRaises(KeyError):store.mutate(request,owner=True)
            with self.assertRaises(Conflict):
                store.mutate({**request,'request_id':'attempt-rebirth'},owner=True)
            with self.assertRaises(KeyError):store.get(request['id'])
            for bad in ('../escape','',None,True,'a'*129):
                with self.subTest(bad=bad),self.assertRaises(ValueError):
                    store.mutate({**request,'id':bad,'request_id':'invalid-id'},owner=True)

    def test_competing_first_saves_cannot_replace_requested_identity(self):
        with tempfile.TemporaryDirectory() as td:
            self.create(WorkflowStore(td))  # Initialize before competing writers.
            def save(name):
                try:
                    return WorkflowStore(td).mutate({'action':'create','request_id':'create-'+name,
                        'id':'same-editor-draft','value':{**workflow(),'name':name}},owner=True)
                except Conflict:
                    return None
            with ThreadPoolExecutor(max_workers=2) as pool:
                results=list(pool.map(save,['Alice','Bob']))
            self.assertEqual(sum(x is not None for x in results),1)
            self.assertEqual(len(WorkflowStore(td).history('same-editor-draft')),1)

    def test_save_reload_replay_history_and_restoration_are_durable(self):
        with tempfile.TemporaryDirectory() as td:
            store = WorkflowStore(td)
            first = self.create(store)
            self.assertFalse(first['active'])
            self.assertEqual(self.create(WorkflowStore(td)), first)
            self.assertEqual(len(store.history(first['id'])), 1)
            changed = self.mutate(store, 'update', first, value={**first, 'name': 'Renamed', 'customField': {'retained': True}})
            self.assertNotEqual(first['versionId'], changed['versionId'])
            self.assertEqual(WorkflowStore(td).get(first['id']), changed)
            restored = self.mutate(store, 'restore', changed, versionId=first['versionId'])
            self.assertEqual(restored['name'], first['name'])
            self.assertNotEqual(restored['versionId'], first['versionId'])
            self.assertEqual(len(store.history(first['id'])), 3)

    def test_archive_duplicate_delete_preserve_source_and_cancel_has_no_effect(self):
        with tempfile.TemporaryDirectory() as td:
            store = WorkflowStore(td); first = self.create(store)
            duplicate = self.mutate(store, 'duplicate', first, name='Independent copy')
            self.assertNotEqual(first['id'], duplicate['id'])
            self.assertEqual(store.get(first['id']), first)
            self.assertEqual(store.list(search='COPY')['count'], 1)
            with self.assertRaisesRegex(ValueError, 'Archive'):
                self.mutate(store, 'delete', first)
            self.assertEqual(store.get(first['id']), first)
            archived = self.mutate(store, 'archive', first)
            self.assertEqual(store.list()['count'], 1)
            self.assertEqual(store.list(archived=True)['count'], 1)
            with self.assertRaisesRegex(ValueError, 'Unarchive'):
                self.mutate(store, 'update', archived, value=first)
            reopened = self.mutate(store, 'unarchive', archived)
            self.assertNotEqual(reopened['versionId'], first['versionId'])
            self.assertEqual(reopened['nodes'], first['nodes'])
            with self.assertRaisesRegex(ValueError, 'already'):
                self.mutate(store, 'unarchive', reopened)
            archived = self.mutate(store, 'archive', reopened)
            request = {'action': 'delete', 'id': first['id'], 'revision': archived['revision'], 'request_id': 'delete-final'}
            result = store.mutate(request, owner=True)
            self.assertEqual(store.mutate(request, owner=True), result)
            with self.assertRaises(KeyError): store.get(first['id'])
            self.assertEqual(store.list(archived=None)['count'], 1)
            with self.assertRaises(KeyError):self.create(store)
            with closing(sqlite3.connect(store.path)) as db:
                self.assertEqual(db.execute('SELECT count(*) FROM versions WHERE workflow=?',(first['id'],)).fetchone()[0],0)
                for raw, in db.execute('SELECT reply FROM requests'):
                    reply=json.loads(raw)
                    if reply.get('id')==first['id']:
                        self.assertNotIn('nodes',reply)

    def test_owner_authority_rechecked_before_replay_and_inputs_cannot_grant_it(self):
        with tempfile.TemporaryDirectory() as td:
            store = WorkflowStore(td)
            request = {'action': 'create', 'request_id': 'owner-request', 'value': workflow()}
            with self.assertRaises(PermissionError): store.mutate(request)
            self.assertFalse(store.path.exists())
            result = store.mutate(request, owner=True)
            with self.assertRaises(PermissionError): store.mutate(request, owner=False)
            with self.assertRaises(ValueError): store.mutate({**request, 'owner': True}, owner=True)
            with self.assertRaises(Conflict): store.mutate({**request, 'value': {**workflow(), 'name': 'Changed replay'}}, owner=True)
            self.assertEqual(store.get(result['id']), result)

    def test_competing_edits_have_one_winner_without_overwriting_losing_draft(self):
        with tempfile.TemporaryDirectory() as td:
            first = self.create(WorkflowStore(td))
            def save(name):
                try:
                    return WorkflowStore(td).mutate({'action': 'update', 'request_id': 'save-'+name,
                        'id': first['id'], 'revision': first['revision'], 'value': {**workflow(), 'name': name}}, owner=True)
                except Conflict:
                    return None
            with ThreadPoolExecutor(max_workers=2) as pool:
                outcomes = list(pool.map(save, ['Alice', 'Bob']))
            self.assertEqual(sum(x is not None for x in outcomes), 1)
            self.assertEqual(len(WorkflowStore(td).history(first['id'])), 2)

    def test_graph_errors_and_raw_credentials_fail_without_partial_writes(self):
        invalid = []
        bad = workflow();bad['nodes'][1]['id'] = bad['nodes'][0]['id'];invalid.append(bad)
        bad = workflow();bad['nodes'][1]['name'] = 'Input';invalid.append(bad)
        bad = workflow();bad['connections']['Input']['main'][0][0]['node'] = 'missing';invalid.append(bad)
        bad = workflow();bad['nodes'][0]['position'][0] = float('inf');invalid.append(bad)
        bad = workflow();bad['nodes'][0]['credentials'] = {'http': {'password': 'not-a-reference'}};invalid.append(bad)
        bad = workflow();bad['pinData']['missing'] = [];invalid.append(bad)
        with tempfile.TemporaryDirectory() as td:
            store = WorkflowStore(td)
            for index, value in enumerate(invalid):
                with self.subTest(index=index), self.assertRaises(ValueError):
                    self.create(store, value, 'invalid-'+str(index))
            self.assertEqual(store.list()['count'], 0)

    def test_unknown_node_data_and_ai_ports_survive_but_import_cannot_activate(self):
        with tempfile.TemporaryDirectory() as td:
            value = workflow()
            value['nodes'][0]['type'] = 'unknown.vendor.node'
            value['nodes'][0]['parameters'] = {'nested': [{'future': True}]}
            value['connections'] = {'Input': {'ai_languageModel': [[{'node': 'If', 'type': 'ai_languageModel', 'index': 2}]]}}
            result = self.create(WorkflowStore(td), value)
            self.assertEqual(result['nodes'], value['nodes'])
            self.assertEqual(result['connections'], value['connections'])
            with self.assertRaisesRegex(ValueError, 'activate'):
                self.create(WorkflowStore(td), {**value, 'active': True}, 'activate-import')
            with self.assertRaisesRegex(ValueError, 'deployment'):
                WorkflowStore(td).mutate({'action': 'publish', 'request_id': 'fake-publish'}, owner=True)

    def test_corrupted_retained_version_is_not_presented_as_valid_history(self):
        with tempfile.TemporaryDirectory() as td:
            store = WorkflowStore(td); first = self.create(store)
            changed = self.mutate(store, 'update', first, value={**workflow(), 'name': 'Second'})
            with closing(sqlite3.connect(store.path)) as db, db:
                db.execute('UPDATE versions SET content=? WHERE id=?', ('{}', first['versionId']))
            self.assertEqual(store.get(changed['id']), changed)
            with self.assertRaisesRegex(ValueError, 'integrity'): store.history(first['id'])

    def test_trusted_pipe_large_document_roundtrip_and_malformed_operation(self):
        with tempfile.TemporaryDirectory() as td:
            value = workflow();value['nodes'][0]['notes'] = 'large public fixture '*60000
            request = {'id': 'rpc-create', 'op': 'mutate', 'args': {'action': 'create', 'request_id': 'large-draft', 'value': value}}
            data = (json.dumps(request)+'\n'+json.dumps({'id': 'rpc-denied', 'op': 'execute-code', 'args': {}})+'\n').encode()
            output = io.StringIO()
            self.assertEqual(serve(WorkflowStore(td), io.BytesIO(data), output), 0)
            replies = [json.loads(line) for line in output.getvalue().splitlines()]
            self.assertTrue(replies[0]['ok']);self.assertFalse(replies[1]['ok'])
            self.assertEqual(replies[0]['result']['nodes'][0]['notes'], value['nodes'][0]['notes'])

    def test_interrupted_commit_rolls_back_head_version_and_replay_binding(self):
        with tempfile.TemporaryDirectory() as td:
            store = WorkflowStore(td); first = self.create(store)
            request = {'action': 'update', 'request_id': 'interrupted-save', 'id': first['id'],
                       'revision': first['revision'], 'value': {**workflow(), 'name': 'After recovery'}}
            code = '''import json, os, sqlite3, sys
from mantleos.studio_workflows import WorkflowStore
original = sqlite3.connect
class CrashConnection(sqlite3.Connection):
    def commit(self): os._exit(79)
sqlite3.connect = lambda *a, **kw: original(*a, factory=CrashConnection, **kw)
WorkflowStore(sys.argv[1]).mutate(json.loads(sys.stdin.read()), owner=True)
'''
            child = subprocess.run([sys.executable, '-c', code, td], input=json.dumps(request), capture_output=True, text=True, timeout=30)
            self.assertEqual(child.returncode, 79, child.stderr)
            self.assertEqual(WorkflowStore(td).get(first['id']), first)
            self.assertEqual(len(store.history(first['id'])), 1)
            saved = WorkflowStore(td).mutate(request, owner=True)
            self.assertEqual(saved['name'], 'After recovery')
            self.assertEqual(len(store.history(first['id'])), 2)

    def test_maximum_document_has_room_for_the_host_envelope_and_replay(self):
        with tempfile.TemporaryDirectory() as td:
            value=workflow();value['nodes'][0]['notes']=''
            size=len(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())
            # document() adds these defaults, so account for them before filling
            # the independent data limit; the host envelope has its own budget.
            value.setdefault('pinData',{});value.setdefault('settings',{})
            size=len(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())
            value['nodes'][0]['notes']='x'*(MAX_BYTES-size)
            self.assertEqual(len(json.dumps(value,sort_keys=True,separators=(',',':')).encode()),MAX_BYTES)
            result=self.create(WorkflowStore(td),value)
            self.assertEqual(self.create(WorkflowStore(td),value),result)
            self.assertEqual(WorkflowStore(td).get(result['id']),result)


if __name__ == '__main__':
    unittest.main()
