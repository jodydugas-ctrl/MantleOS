"""Saved-node grants and the checked boundary use only synthetic credentials."""
from copy import deepcopy
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import tempfile
from threading import Thread
import unittest
from unittest.mock import patch

from mantleos.studio import controller_pin, database, initialize_heart, _setting
from mantleos.studio_credential_use import CredentialUse, checked_http_node
from mantleos.studio_credentials import CredentialStore
from mantleos.studio_workflows import WorkflowStore


def graph(credential='credential-test'):
    return {'name': 'Synthetic checked HTTP', 'nodes': [{
        'id': 'request', 'name': 'Request', 'position': [0, 0],
        'type': 'n8n-nodes-base.httpRequest', 'typeVersion': 4.5,
        'credentials': {'httpBasicAuth': {'id': credential}},
        'parameters': {'authentication': 'genericCredentialType', 'genericAuthType': 'httpBasicAuth',
                       'url': 'http://127.0.0.1:19999/checked'},
    }]}


class CredentialUseTests(unittest.TestCase):
    def test_checked_profile_refuses_other_destinations_and_effects(self):
        value = {**graph(), 'id': 'workflow', 'versionId': 'version'}
        self.assertEqual(checked_http_node(value, 'request')['method'], 'GET')
        changes = [
            {'url': 'http://localhost:19999/checked'},
            {'url': 'http://127.0.0.1:19999/../checked'},
            {'url': 'http://127.0.0.1:19999/checked?x=1'},
            {'url': 'http://127.0.0.1:19999@outside.invalid/checked'},
            {'url': 'http://169.254.169.254:19999/checked'},
            {'method': 'POST'}, {'options': {'redirect': {'followRedirects': True}}},
        ]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                modified = deepcopy(value)
                modified['nodes'][0]['parameters'].update(change)
                checked_http_node(modified, 'request')

    @unittest.skipUnless(os.name == 'nt', 'Windows DPAPI grant qualification')
    def test_grant_is_sealed_and_invalidates_on_version_revision_expiry_or_revocation(self):
        with tempfile.TemporaryDirectory() as directory:
            nest = Path(directory)/'nest'
            initialize_heart(nest, b'Synthetic')
            with database(nest) as db:
                identity = _setting(db, 'identity')
                db.execute("UPDATE settings SET value=? WHERE key='phase'", (json.dumps('ACTIVE'),))
            vault = CredentialStore(nest, identity)
            vault.initialize(reviewed=True)
            credential = {'name': 'Synthetic Basic Auth', 'type': 'httpBasicAuth',
                          'data': {'user': 'synthetic', 'password': 'synthetic-password'}}
            saved_credential = vault.save(credential, reviewed=True)
            store = WorkflowStore(nest/'operational-workflows')
            value = graph(saved_credential['id'])
            saved = store.mutate({'action': 'create', 'request_id': 'create-workflow', 'value': value}, owner=True)
            authority = CredentialUse(nest)
            args = (saved['id'], 'request', saved['versionId'])
            config = {'credential_editor': True, 'manual_execution': True, 'sha256': 'a'*64}
            with self.assertRaises(PermissionError):
                authority.grant(*args[:2], reviewed=True)
            with patch('mantleos.studio_editor.from_database', return_value=config):
                with self.assertRaises(PermissionError):
                    authority.grant(*args[:2])
                with self.assertRaises(PermissionError):
                    authority.check(*args, now=100)
                grant = authority.grant(*args[:2], ttl=10, now=100, reviewed=True)
                self.assertEqual(authority.check(*args, now=109), grant)
                self.assertNotIn('synthetic-password', json.dumps(grant))
                with self.assertRaises(PermissionError):
                    authority.check(*args, now=110)
                self.assertEqual(authority.revoke(grant['id'], reviewed=True)['status'], 'REVOKED')
                with self.assertRaises(PermissionError):
                    authority.check(*args, now=109)
                authority.grant(*args[:2], now=100, reviewed=True)
                vault.save(credential, identifier=saved_credential['id'],
                           revision=saved_credential['revision'], reviewed=True)
                with self.assertRaisesRegex(PermissionError, 'Credential revision changed'):
                    authority.check(*args, now=109)
                authority.grant(*args[:2], now=100, reviewed=True)
                with database(nest) as db:
                    db.execute("UPDATE credential_use_grants SET seal=x'00'")
                with self.assertRaisesRegex(PermissionError, 'grant verification failed'):
                    authority.check(*args, now=109)
                authority.grant(*args[:2], now=100, reviewed=True)
                store.mutate({'action': 'update', 'request_id': 'change-workflow', 'id': saved['id'],
                              'revision': saved['revision'], 'value': {**value, 'name': 'Edited'}}, owner=True)
                with self.assertRaisesRegex(PermissionError, 'Saved workflow version changed'):
                    authority.check(*args, now=109)

    @unittest.skipUnless(os.name == 'nt', 'Windows DPAPI and loopback checked effect')
    def test_checked_effect_requires_live_claim_and_grant_and_sends_once(self):
        hits = []
        expected = 'Basic '+base64.b64encode(b'synthetic:fixture-checked-secret').decode()

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                valid = self.path == '/checked' and self.headers.get('Authorization') == expected
                hits.append(valid)
                payload = b'{"accepted":true,"value":42}' if valid else b'{}'
                self.send_response(200 if valid else 401)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *_):
                pass

        with tempfile.TemporaryDirectory() as directory, ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
            nest = Path(directory)/'nest'
            initialize_heart(nest, b'Synthetic')
            with database(nest) as db:
                identity = _setting(db, 'identity')
                db.execute("UPDATE settings SET value=? WHERE key='phase'", (json.dumps('ACTIVE'),))
            vault = CredentialStore(nest, identity)
            vault.initialize(reviewed=True)
            credential = vault.save({'name': 'Synthetic', 'type': 'httpBasicAuth',
                                     'data': {'user': 'synthetic', 'password': 'fixture-checked-secret'}}, reviewed=True)
            value = graph(credential['id'])
            value['nodes'][0]['parameters']['url'] = f'http://127.0.0.1:{server.server_port}/checked'
            value['nodes'].insert(0, {'id': 'manual', 'name': 'Manual', 'position': [0, 0],
                                      'type': 'n8n-nodes-base.manualTrigger', 'typeVersion': 1})
            value['connections'] = {'Manual': {'main': [[{'node': 'Request', 'type': 'main', 'index': 0}]]}}
            store = WorkflowStore(nest/'operational-workflows')
            saved = store.mutate({'action': 'create', 'request_id': 'create-workflow', 'value': value}, owner=True)
            run = store.execution_start({'request_id': 'attempt', 'workflow_id': saved['id'],
                                         'version_id': saved['versionId'], 'revision': saved['revision'],
                                         'trigger': 'Manual', 'destination': None},
                                        source_pin=controller_pin(), owner=True)
            config = {'credential_editor': True, 'manual_execution': True, 'sha256': 'a'*64}
            authority = CredentialUse(nest)
            serving = Thread(target=server.serve_forever, daemon=True)
            serving.start()
            try:
                with patch('mantleos.studio_editor.from_database', return_value=config):
                    kwargs = {'claim': run['claim'], 'configuration': config['sha256']}
                    with self.assertRaises(PermissionError):
                        authority.observe(run['id'], 'request', **kwargs)
                    authority.grant(saved['id'], 'request', reviewed=True)
                    with self.assertRaises(PermissionError):
                        authority.observe(run['id'], 'request', **{**kwargs, 'claim': 'forged'})
                    self.assertEqual(hits, [])
                    checked = authority.observe(run['id'], 'request', **kwargs)
                    self.assertEqual(checked['stage'], 'VERIFIED')
                    self.assertEqual(checked['json'], {'accepted': True, 'value': 42})
                    with self.assertRaisesRegex(PermissionError, 'already recorded'):
                        authority.observe(run['id'], 'request', **kwargs)
                    self.assertEqual(hits, [True])
                with database(nest) as db:
                    stage, digest = db.execute('SELECT stage,result_sha256 FROM credential_effect_attempts').fetchone()
                    self.assertEqual(stage, 'VERIFIED')
                    self.assertRegex(digest, r'^[a-f0-9]{64}$')
            finally:
                server.shutdown()
                serving.join()
