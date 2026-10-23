import copy, json, tempfile, unittest
from pathlib import Path
from mantleos.continuity import *

IDENTITY={'birth_sha256':'a'*64,'primer_sha256':'b'*64,'cartridge_id':'raven-test'}
def rec(seq,prev,message):
    r={'schema':'mantle.engram-record/1','seq':seq,'id':f'mock-{seq}',
       'type':'turn','source':'cloud-test','body':{'message':message},'prev_sha256':prev}
    r['sha256']=hash_object(r);return r

class TestProtocol(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=LocalCASStore(self.tmp.name);self.store.cas_head(None,make_head(IDENTITY))
    def test_two_turns_and_cold_restore(self):
        a=rec(1,ZERO,'hello'); h=commit(self.store,a)
        b=rec(2,a['sha256'],'second');h=commit(self.store,b)
        restored=recover(h,{m['blob_id']:self.store.get_blob(m['blob_id']) for m in h['segments']})
        self.assertEqual(restored,[a,b]);self.assertEqual(h['ledger_head'],b['sha256'])
    def test_identity_rejected(self):
        a=rec(1,ZERO,'x');seg=encode_segment(a,IDENTITY,ZERO)
        with self.assertRaisesRegex(ValueError,'identity'):decode_segment(seg,{**IDENTITY,'cartridge_id':'other'},ZERO,1)
    def test_tampering_is_rejected(self):
        a=rec(1,ZERO,'x');h=commit(self.store,a)
        blobs={m['blob_id']:self.store.get_blob(m['blob_id']) for m in h['segments']}
        blobs[h['segments'][0]['blob_id']]['payload_b64']='AAAA'
        with self.assertRaises(ValueError):recover(h,blobs)
    def test_missing_segment(self):
        a=rec(1,ZERO,'x');h=commit(self.store,a)
        with self.assertRaisesRegex(ValueError,'Missing'): recover(h,{})
    def test_duplicate_replay_refused(self):
        a=rec(1,ZERO,'x');commit(self.store,a)
        with self.assertRaises(ValueError):commit(self.store,a)
    def test_stale_head_conflict(self):
        old=self.store.load_head();a=rec(1,ZERO,'x');commit(self.store,a)
        with self.assertRaises(Conflict):self.store.cas_head(old['sha256'],old)
    def test_segment_uploaded_but_no_head_update(self):
        a=rec(1,ZERO,'x');seg=encode_segment(a,IDENTITY,ZERO)
        self.store.put_blob('orphan',seg)
        self.assertEqual(recover(self.store.load_head(),{}),[])
    def test_no_head_update_without_verified_readback(self):
        a=rec(1,ZERO,'x');seg=encode_segment(a,IDENTITY,ZERO)
        bad=copy.deepcopy(seg);bad['payload_b64']='AAAA'
        with self.assertRaises(ValueError):advance_head(self.store.load_head(),seg,'x',blob_readback=bad)
        self.assertEqual(self.store.load_head()['seq'],0)
    def test_head_tampering(self):
        head=self.store.load_head();head['seq']=5
        with self.assertRaisesRegex(ValueError,'Tampered HEAD'):verify_head(head)
    def test_docs_codec(self):
        a=rec(1,ZERO,'Zażółć Raven ♥ \n');seg=encode_segment(a,IDENTITY,ZERO)
        self.assertEqual(from_document(as_document(seg)+'\n'),seg)
    def test_manifest_wrong_order(self):
        a=rec(1,ZERO,'x');h=commit(self.store,a);h['segments'][0]['seq']=2;h['sha256']=hash_object(h)
        with self.assertRaisesRegex(ValueError,'sequence'):verify_head(h)

if __name__=='__main__':unittest.main(verbosity=2)
