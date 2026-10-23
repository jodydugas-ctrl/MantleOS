"""Source-pinned synthetic augmentation, actual effects, and concurrent history."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import unittest
from mantleos import augmentation, engram, organism
from mantleos.augmentation_host import Notebook

class AugmentationTests(unittest.TestCase):
    def test_complete_demo_and_retained_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'demo';result=augmentation.demonstrate(root)
            self.assertEqual(result['result'],'PASS')
            self.assertEqual(result['acceptance'],'NOT_GRANTED')
            self.assertEqual({r['operation'] for r in result['connections']},{'edit','read','save'})
            for name,pin in result['source_pins'].items():
                self.assertEqual(augmentation.hashlib.sha256((root/'retained-source'/name).read_bytes()).hexdigest(),pin)
            with self.assertRaises(ValueError):augmentation.demonstrate(root)

    def test_concurrent_connections_retain_all_history_and_edits(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);body=root/'body';organism.create(body)
            host=Notebook(body,root/'draft.txt');adapter=augmentation.Adapter(host,allowed=('edit',))
            prefix=(body/'ENGRAM.jsonl').read_bytes()
            with ThreadPoolExecutor(max_workers=3) as pool:
                results=list(pool.map(lambda i:adapter.motor({'operation':'edit','arguments':{'text':str(i)}}),range(3)))
            self.assertTrue(all(r['stage']=='VERIFIED' for r in results))
            self.assertEqual(sorted(host.read()['text']),list('012'))
            self.assertTrue((body/'ENGRAM.jsonl').read_bytes().startswith(prefix))
            records=engram.read(body/'ENGRAM.jsonl')
            self.assertEqual(sum(r['type']=='host-action-evidence' for r in records),3)
            self.assertEqual(sum(r['type']=='host-observation' for r in records),3)

    def test_source_discovery_and_proposals_grant_no_actions(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);body=root/'body';organism.create(body)
            host=Notebook(body,root/'draft.txt');adapter=augmentation.Adapter(host)
            for op,args in [('read',{}),('edit',{'text':'forbidden'}),('save',{})]:
                self.assertEqual(adapter.motor({'operation':op,'arguments':args})['stage'],'FAILED')
            self.assertEqual(host.read()['text'],'');self.assertFalse(host.destination.exists())
            with self.assertRaises(ValueError):adapter.motor({'operation':'save','arguments':{},'approved':True})
            with self.assertRaises(ValueError):augmentation.Adapter(host,allowed=('terminal',))

    def test_observation_and_save_failures_preserve_native_draft(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);body=root/'body';organism.create(body)
            host=Notebook(body,root/'draft.txt');adapter=augmentation.Adapter(host,allowed=('save',))
            with patch('mantleos.augmentation.lifecycle.admit', side_effect=OSError('observation unavailable')):
                result=adapter.user('edit',text='keep')
            self.assertEqual(result['observation'],'UNAVAILABLE:OSError')
            self.assertEqual(host.read()['text'],'keep')
            with patch('mantleos.augmentation_host.atomic_bytes',side_effect=OSError('disk unavailable')):
                self.assertEqual(adapter.motor({'operation':'save','arguments':{}})['stage'],'UNKNOWN')
            host.edit(' typing');self.assertEqual(host.read()['text'],'keep typing')

    def test_interrupted_publication_recovers_prior_draft_and_continues(self):
        from mantleos import transactions,lifecycle
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);body=root/'body';organism.create(body)
            host=Notebook(body,root/'draft.txt');host.edit('retained')
            prefix=(body/'ENGRAM.jsonl').read_bytes()
            stage=transactions.stage_body(body)
            engram.append(stage/'ENGRAM.jsonl','test','synthetic',{'attempt':'interrupted'})
            lifecycle.finalize(stage)
            with transactions.body_lock(body),self.assertRaises(RuntimeError):
                transactions.publish_body(stage,body,interrupt='after-backup')
            with self.assertRaises(ValueError):host.read()
            transactions.recover(body)
            self.assertEqual(host.read()['text'],'retained')
            host.edit(' again')
            self.assertEqual(host.read()['text'],'retained again')
            self.assertTrue((body/'ENGRAM.jsonl').read_bytes().startswith(prefix))
