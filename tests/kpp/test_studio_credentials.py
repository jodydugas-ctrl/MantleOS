"""Studio credential boundaries with synthetic data and the real Windows protector."""
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

from mantleos.studio_credentials import Conflict, CredentialStore, MASK


class CredentialTests(unittest.TestCase):
    def test_owner_gate_and_no_unprotected_platform_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            store = CredentialStore(directory, 'synthetic-nest')
            with self.assertRaises(PermissionError):
                store.initialize()
            self.assertFalse(store.path.exists())
            if os.name != 'nt':
                with self.assertRaisesRegex(ValueError, 'requires Windows DPAPI'):
                    store.initialize(reviewed=True)
                self.assertFalse(store.path.exists())

    @unittest.skipUnless(os.name == 'nt', 'Windows DPAPI credential qualification')
    def test_sealed_credentials_masked_edit_conflict_and_delete(self):
        with tempfile.TemporaryDirectory() as directory:
            identity = 'synthetic-nest'
            store = CredentialStore(directory, identity)
            store.initialize(reviewed=True)
            raw = 'synthetic-secret-body-never-exported'
            form = {'name': 'Synthetic Basic Auth', 'type': 'httpBasicAuth',
                    'data': {'user': 'demo', 'password': raw}}
            created = store.save(form, reviewed=True)
            identifier = created['id']
            reopened = CredentialStore(directory, identity)
            self.assertEqual(reopened.list(reviewed=True), [created])
            with self.assertRaises(PermissionError):
                reopened.get(identifier, include_data=True)
            with self.assertRaisesRegex(ValueError, 'identity changed'):
                CredentialStore(directory, 'other-nest').list(reviewed=True)
            masked = reopened.get(identifier, include_data=True, reviewed=True)['data']
            self.assertEqual(masked, {'user': 'demo', 'password': MASK})
            changed = reopened.save({**form, 'name': 'Renamed', 'data': masked},
                                    identifier=identifier, revision=created['revision'], reviewed=True)
            self.assertNotEqual(changed['revision'], created['revision'])
            with self.assertRaises(Conflict):
                reopened.save(form, identifier=identifier, revision=created['revision'], reviewed=True)
            with self.assertRaises(Conflict):
                reopened.remove(identifier, revision=created['revision'], reviewed=True)
            with self.assertRaisesRegex(ValueError, 'existing secret'):
                reopened.save({**form, 'data': masked}, reviewed=True)
            with closing(sqlite3.connect(store.path)) as db:
                db.row_factory = sqlite3.Row
                row = db.execute('SELECT * FROM credentials').fetchone()
                self.assertEqual(reopened._unseal(row)['password'], raw)
                self.assertNotIn(raw.encode(), Path(store.path).read_bytes())
                db.execute("UPDATE credentials SET name='forged'")
                db.commit()
            with self.assertRaisesRegex(ValueError, 'seal verification'):
                reopened.get(identifier, include_data=True, reviewed=True)
            with self.assertRaisesRegex(ValueError, 'seal verification'):
                reopened.remove(identifier, revision=changed['revision'], reviewed=True)
            with closing(sqlite3.connect(store.path)) as db:
                db.execute('UPDATE credentials SET name=?', (changed['name'],))
                db.commit()
            self.assertTrue(reopened.remove(identifier, revision=changed['revision'], reviewed=True))
            self.assertEqual(reopened.list(reviewed=True), [])
