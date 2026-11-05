"""Controller configuration boundaries, not complete resident/browser evidence."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from mantleos import studio, studio_editor as editor
from mantleos import json_contract as c
from mantleos.limbs import worker_lease


class EditorConfigurationTests(unittest.TestCase):
    def fixture(self, root):
        nest = Path(root)/'synthetic-controller'
        nest.mkdir()
        with closing(sqlite3.connect(nest/'studio.sqlite')) as db, db:
            db.execute('CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT NOT NULL)')
            db.execute('CREATE TABLE mind(id TEXT PRIMARY KEY,user TEXT,phase TEXT,frame TEXT,reply TEXT)')
            db.execute('CREATE TABLE events(id TEXT PRIMARY KEY,kind TEXT,value TEXT,at REAL)')
            db.executemany('INSERT INTO settings VALUES (?,?)',
                           [('controller_pin', json.dumps(studio.controller_pin())), ('phase', '"STASIS"')])
        return nest

    def inspection(self):
        identity={'schema':'studio.editor-installation/1','reference':'n8n@2.46.4',
                  'editor_source_digest':'a'*64,'catalog_source_digest':'b'*64}
        return {**identity,'sha256':c.digest(identity),'authority':'NONE',
                'workflow_execution':'NOT_GRANTED_BY_INSTALLATION','nodes':1,
                'files':5,'asset_bytes':100,'credential_types':0,'version_entries':1}

    def configure(self, nest, reviewed=True):
        return editor.configure(nest, node='not-executed-in-fixture', package_root=nest/'package',
            editor_profile=nest/'assets.json', catalog_root=nest/'catalog', catalog_profile=nest/'catalog.json',
            reviewed=reviewed)

    def test_opt_out_is_read_only_and_configuration_has_no_public_paths(self):
        with tempfile.TemporaryDirectory() as td:
            nest = self.fixture(td)
            self.assertEqual(editor.public_status(nest), {'enabled': False})
            with patch.object(editor, 'inspect_source', return_value=self.inspection()) as verifier:
                with self.assertRaises(PermissionError):
                    self.configure(nest, reviewed=False)
                verifier.assert_not_called()
                configured = self.configure(nest)
            self.assertTrue(configured['enabled'])
            private = editor.private_config(nest)
            self.assertEqual(private['package_root'], str(nest/'package'))
            public = editor.public_status(nest)
            self.assertNotIn(str(nest), json.dumps(public))
            self.assertEqual(public['installation']['authority'], 'NONE')
            self.assertEqual(public['context'], 'RESIDENT_MEMORY')
            with closing(sqlite3.connect(nest/'studio.sqlite')) as db:
                self.assertEqual(db.execute('SELECT count(*) FROM events').fetchone()[0], 1)

    def test_active_controller_and_pending_cognition_refuse_reconfiguration(self):
        with tempfile.TemporaryDirectory() as td:
            nest = self.fixture(td)
            with patch.object(editor, 'inspect_source', return_value=self.inspection()) as verifier:
                with worker_lease(nest, 'controller'):
                    with self.assertRaises((ValueError, OSError)):
                        self.configure(nest)
                with closing(sqlite3.connect(nest/'studio.sqlite')) as db, db:
                    db.execute("INSERT INTO mind VALUES ('pending','synthetic','AWAITING_MIND','{}',NULL)")
                with self.assertRaisesRegex(ValueError, 'pending cognition'):
                    self.configure(nest)
                verifier.assert_not_called()

    def test_stasis_is_required_and_changed_configuration_fails_explicitly(self):
        with tempfile.TemporaryDirectory() as td:
            nest = self.fixture(td)
            with closing(sqlite3.connect(nest/'studio.sqlite')) as db, db:
                db.execute("UPDATE settings SET value='\"ACTIVE\"' WHERE key='phase'")
            with patch.object(editor, 'inspect_source', return_value=self.inspection()):
                with self.assertRaisesRegex(ValueError, 'stasis'):
                    self.configure(nest)
                with closing(sqlite3.connect(nest/'studio.sqlite')) as db, db:
                    db.execute("UPDATE settings SET value='\"STASIS\"' WHERE key='phase'")
                self.configure(nest)
            with closing(sqlite3.connect(nest/'studio.sqlite')) as db, db:
                value=json.loads(db.execute('SELECT value FROM settings WHERE key=?',(editor.KEY,)).fetchone()[0])
                value['package_root']=str(nest/'substituted')
                db.execute('UPDATE settings SET value=? WHERE key=?',(json.dumps(value),editor.KEY))
            with self.assertRaisesRegex(ValueError, 'configuration changed'):
                editor.public_status(nest)

    def test_failed_inspection_preserves_prior_selection_and_withdrawal_is_reviewed(self):
        with tempfile.TemporaryDirectory() as td:
            nest=self.fixture(td)
            with patch.object(editor,'inspect_source',return_value=self.inspection()):self.configure(nest)
            original=editor.private_config(nest)
            bad=self.inspection();bad['nodes']=True
            with patch.object(editor,'inspect_source',return_value=bad):
                with self.assertRaisesRegex(ValueError,'counts'):self.configure(nest)
            self.assertEqual(editor.private_config(nest),original)
            with self.assertRaises(PermissionError):editor.disable(nest)
            with worker_lease(nest,'controller'):
                with self.assertRaises((ValueError,OSError)):editor.disable(nest,reviewed=True)
            self.assertEqual(editor.disable(nest,reviewed=True),{'enabled':False})
            self.assertEqual(editor.public_status(nest),{'enabled':False})
            with closing(sqlite3.connect(nest/'studio.sqlite')) as db:
                self.assertEqual(db.execute('SELECT kind FROM events ORDER BY rowid').fetchall(),
                                 [('editor.source.reviewed',),('editor.source.withdrawn',)])

    def test_rehashed_invalid_inspections_do_not_become_valid_configuration(self):
        with tempfile.TemporaryDirectory() as td:
            nest=self.fixture(td)
            with patch.object(editor,'inspect_source',return_value=self.inspection()):self.configure(nest)
            original=editor.private_config(nest)
            for field,value in [('reference','unreviewed'),('authority','APPROVED'),
                                ('editor_source_digest','0'*64),('files',999999)]:
                changed=c.loads(c.canonical(original));changed['inspection'][field]=value
                changed['sha256']=c.digest({k:v for k,v in changed.items() if k!='sha256'})
                with self.assertRaises(ValueError):editor._validate(changed)


if __name__ == '__main__':
    unittest.main()
