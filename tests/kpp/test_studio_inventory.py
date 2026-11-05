"""Descriptor inventory never provides secrets or usable credential grants."""
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from mantleos.studio_inventory import EditorInventory


class StudioInventoryTests(unittest.TestCase):
    def test_missing_store_is_unavailable_and_review_creates_real_empty_state(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);inventory=EditorInventory(root)
            with self.assertRaisesRegex(ValueError,'not initialized'):inventory.list('credentials')
            self.assertFalse(inventory.path.exists())
            with self.assertRaises(PermissionError):inventory.initialize()
            inventory.initialize(reviewed=True)
            self.assertEqual(inventory.list('credentials'),[])
            inventory.initialize(reviewed=True)
            self.assertEqual(EditorInventory(root).list('tags'),[])

    def test_actual_registered_metadata_survives_reload_without_authorizing_use(self):
        with tempfile.TemporaryDirectory() as td:
            inventory=EditorInventory(td)
            value={'id':'reference-1','name':'Synthetic credential metadata','type':'httpBasicAuth'}
            with self.assertRaises(PermissionError):inventory.register('credentials',value)
            first=inventory.register('credentials',value,reviewed=True)
            reopened=EditorInventory(td)
            self.assertEqual(reopened.list('credentials')[0]['name'],value['name'])
            with self.assertRaisesRegex(ValueError,'Stale'):
                reopened.register('credentials',{**value,'name':'stale update'},reviewed=True)
            reopened.register('credentials',{**value,'name':'Reviewed rename'},revision=first['revision'],reviewed=True)
            current=reopened.list('credentials')[0]
            self.assertEqual(current['name'],'Reviewed rename')
            self.assertNotIn('data',current);self.assertNotIn('usable',current)
            with closing(sqlite3.connect(inventory.path)) as db:
                self.assertEqual(db.execute('SELECT count(*) FROM versions').fetchone()[0],2)

    def test_secret_fields_forged_capabilities_corruption_and_unknown_collections_fail(self):
        with tempfile.TemporaryDirectory() as td:
            inventory=EditorInventory(td)
            value={'id':'reference-1','name':'Synthetic descriptor','type':'httpBasicAuth'}
            for extra in ({'data':{'password':'NEVER_STORE'}},{'usable':True},{'authority':'APPROVED'}):
                with self.assertRaises(ValueError):inventory.register('credentials',{**value,**extra},reviewed=True)
            self.assertFalse(inventory.path.exists())
            inventory.register('credentials',value,reviewed=True)
            with self.assertRaises(ValueError):inventory.list('provider-keys')
            with closing(sqlite3.connect(inventory.path)) as db,db:
                db.execute("UPDATE versions SET content=replace(content,'Synthetic','Forged')")
            with self.assertRaisesRegex(ValueError,'changed'):inventory.list('credentials')


if __name__=='__main__':unittest.main()
