"""Synthetic pixel/PNG oracles, capture provenance, freshness and separate review."""
import binascii
import copy
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

from mantleos.kpp.core import KPPError, read_json
from mantleos.kpp import png
from mantleos.kpp.workshop import begin, inspection, accept, finish, install_module, load
from mantleos.kpp.conformance import record_capture, compare_captures, read_evidence, summary
from mantleos.kpp.graph import functional_graph
from mantleos.kpp.portability import export_preview, import_preview

ROOT=Path(__import__('mantleos.kpp', fromlist=['x']).__file__).parent/'resources'
RECIPE=read_json(ROOT/'recipes/progressive-calculator.json')


def chunk(kind,data):
    return struct.pack('>I',len(data))+kind+data+struct.pack('>I',binascii.crc32(kind+data)&0xffffffff)


class PNGOracles(unittest.TestCase):
    def test_rgb_and_rgba_filters_match_independent_pixel_oracle(self):
        # Encoder-side construction from explicit pixels, independent of KPP's decoder/encoder.
        for channels in (3,4):
            rows=[bytes([10,20,30,40,50,60] if channels==3 else [10,20,30,200,40,50,60,255]),
                  bytes([90,80,70,60,50,40] if channels==3 else [90,80,70,100,60,50,40,220])]
            for mode in range(5):
                encoded=bytearray();prior=bytes(len(rows[0]))
                for row in rows:
                    encoded.append(mode)
                    for index,value in enumerate(row):
                        a=row[index-channels] if index>=channels else 0;b=prior[index];c=prior[index-channels] if index>=channels else 0
                        if mode==0:predict=0
                        elif mode==1:predict=a
                        elif mode==2:predict=b
                        elif mode==3:predict=(a+b)//2
                        else:
                            distances=[abs((a+b-c)-candidate) for candidate in (a,b,c)]
                            predict=(a,b,c)[distances.index(min(distances))]
                        encoded.append((value-predict)%256)
                    prior=row
                color=2 if channels==3 else 6
                blob=png.SIGNATURE+chunk(b'IHDR',struct.pack('>IIBBBBB',2,2,8,color,0,0,0))+chunk(b'IDAT',zlib.compress(encoded))+chunk(b'IEND',b'')
                expected=b''.join(bytes((*row[index:index+3],255)) for row in rows for index in range(0,len(row),3)) if channels==3 else b''.join(rows)
                with self.subTest(channels=channels,mode=mode):self.assertEqual(png.decode(blob),(2,2,expected))

    def test_crc_truncation_tail_and_unsupported_profiles_refused(self):
        valid=png.encode(1,1,bytes([1,2,3,255]))
        damaged=bytearray(valid);damaged[20]^=1
        for blob in (bytes(damaged),valid[:-1],valid+b'junk',b'not a PNG'):
            with self.subTest(blob=blob[:20]),self.assertRaises(KPPError):png.decode(blob)
        for color,depth,interlace in ((3,8,0),(6,16,0),(6,8,1)):
            blob=png.SIGNATURE+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,depth,color,0,0,interlace))+chunk(b'IDAT',zlib.compress(b'\0\1\2\3\xff'))+chunk(b'IEND',b'')
            with self.assertRaisesRegex(KPPError,'Unsupported PNG profile'):png.decode(blob)

    def test_animation_transparency_and_oversized_decoded_stream_refused(self):
        header=png.SIGNATURE+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,6,0,0,0))
        for extra in (chunk(b'acTL',struct.pack('>II',1,0)),chunk(b'tRNS',b'\0\0')):
            with self.assertRaises(KPPError):png.decode(header+extra+chunk(b'IDAT',zlib.compress(b'\0\1\2\3\xff'))+chunk(b'IEND',b''))
        with self.assertRaisesRegex(KPPError,'decoded size'):png.decode(header+chunk(b'IDAT',zlib.compress(b'\0'*100000))+chunk(b'IEND',b''))


class GUIConformance(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);self.ws=self.root/'workspace';begin(self.ws,RECIPE,ROOT)
        self.left=self.root/'reference.png';self.right=self.root/'candidate.png'
        self.pixels=bytes([40,50,60,255]*4)
        self.left.write_bytes(png.encode(2,2,self.pixels));self.right.write_bytes(png.encode(2,2,self.pixels))

    def record(self,surface='reference',capture=None,mode='normal',state='empty-calculator',method='screenshot',**kwargs):
        return record_capture(self.ws,capture or (self.left if surface=='reference' else self.right),surface,method,'synthetic-observer',mode,state,**kwargs)

    def test_identical_pixels_do_not_accept_or_claim_behavioral_parity(self):
        reference=self.record();candidate=self.record('candidate')
        result=compare_captures(self.ws,reference['id'],candidate['id'],'synthetic-review')
        self.assertEqual(result['metrics']['changed_pixels'],0)
        self.assertEqual(result['visual_conformance'],'PIXEL_MEASURED_REVIEW_REQUIRED')
        self.assertEqual(result['behavioral_conformance'],'NOT_ESTABLISHED')
        self.assertEqual(inspection(self.ws)['accepted'],0)
        with self.assertRaises(KPPError):finish(self.ws)

    def test_stale_parent_review_cannot_authorize_dependent_acceptance(self):
        recipe=copy.deepcopy(RECIPE)
        recipe['anchors'][1]['depends']=[recipe['anchors'][0]['id']]
        ws=self.root/'dependent';begin(ws,recipe,ROOT)
        evidence=record_capture(ws,self.left,'candidate','screenshot','synthetic observer','normal','empty')
        accept(ws,recipe['anchors'][0]['id'],'synthetic review','test-baker',kind='gui-reviewed',evidence_id=evidence['id'])
        image=ws/evidence['capture']['path'];image.write_bytes(b'changed')
        with self.assertRaisesRegex(KPPError,'current evidence'):
            accept(ws,recipe['anchors'][1]['id'],'synthetic dependent review','test-baker')

    def test_fixed_changed_pixel_metrics_and_reviewable_difference(self):
        changed=bytearray(self.pixels);changed[0]+=8;self.right.write_bytes(png.encode(2,2,bytes(changed)))
        reference=self.record();candidate=self.record('candidate')
        result=compare_captures(self.ws,reference['id'],candidate['id'],'synthetic-review')
        self.assertEqual(result['metrics'],{'pixels':4,'changed_pixels':1,'changed_fraction':.25,'mean_absolute_rgba_error':.5,'maximum_channel_error':8})
        _,_,heat=png.read(self.ws/result['difference']['path'])
        self.assertEqual(heat[:4],bytes([8,0,0,255]))
        self.assertEqual(heat[4:8],bytes([0,0,0,255]))

    def test_viewport_mode_and_state_mismatch_refused(self):
        reference=self.record()
        self.right.write_bytes(png.encode(1,1,bytes([40,50,60,255])))
        for kwargs in ({},{'mode':'different'},{'state':'different'}):
            candidate=self.record('candidate',**kwargs)
            with self.assertRaisesRegex(KPPError,'matching target'):compare_captures(self.ws,reference['id'],candidate['id'],'review')

    def test_wrong_surface_and_incomplete_runtime_observation_refused(self):
        reference=self.record();another=self.record()
        with self.assertRaisesRegex(KPPError,'reference and candidate'):compare_captures(self.ws,reference['id'],another['id'],'review')
        with self.assertRaisesRegex(KPPError,'actual action'):self.record('candidate',method='runtime')

    def test_manual_runtime_is_labeled_and_failed_result_cannot_be_accepted(self):
        result=self.record('candidate',method='runtime',action='press Calculate',expected='5',observed='wrong')
        self.assertEqual(result['evidence_kind'],'MANUAL_RUNTIME_OBSERVATION')
        self.assertFalse(result['interaction']['matches'])
        with self.assertRaisesRegex(KPPError,'failed recorded'):accept(self.ws,'usable-surface','review','test-baker',kind='gui-reviewed',evidence_id=result['id'])

    def test_explicit_review_is_source_bound_and_appears_in_one_graph(self):
        reference=self.record();candidate=self.record('candidate')
        comparison=compare_captures(self.ws,reference['id'],candidate['id'],'synthetic-review')
        accept(self.ws,'usable-surface','Synthetic visible surface review only','test-baker',kind='gui-reviewed',evidence_id=comparison['id'])
        self.assertEqual(inspection(self.ws)['accepted'],1)
        recipe,state=load(self.ws);graph=functional_graph(recipe,state)
        self.assertEqual(len([e for e in graph['edges'] if e['kind']=='baker-reviewed-gui-evidence']),1)
        self.assertEqual(len([n for n in graph['nodes'] if n['kind']=='gui-evidence-reference']),3)

    def test_source_change_stales_observations_and_review(self):
        observation=self.record('candidate')
        accept(self.ws,'usable-surface','Synthetic check','test-baker',kind='gui-reviewed',evidence_id=observation['id'])
        install_module(self.ws,'square',ROOT/'previews/calculator/square.js')
        with self.assertRaisesRegex(KPPError,'stale'):read_evidence(self.ws,observation['id'])
        self.assertEqual(inspection(self.ws)['accepted'],0)
        self.assertEqual(len(summary(self.ws)['stale']),1)

    def test_pinned_reference_survives_candidate_increment(self):
        reference=self.record()
        install_module(self.ws,'square',ROOT/'previews/calculator/square.js')
        self.assertEqual(read_evidence(self.ws,reference['id'])['surface'],'reference')
        candidate=self.record('candidate')
        self.assertEqual(compare_captures(self.ws,reference['id'],candidate['id'],'review')['metrics']['changed_pixels'],0)

    def test_changed_capture_invalidates_review_without_overwriting_memory(self):
        observation=self.record('candidate')
        accept(self.ws,'usable-surface','Synthetic check','test-baker',kind='gui-reviewed',evidence_id=observation['id'])
        image=self.ws/observation['capture']['path'];image.write_bytes(b'changed')
        self.assertEqual(inspection(self.ws)['accepted'],0)
        self.assertEqual(len(read_json(self.ws/'state.json')['gui_evidence']),1)
        with self.assertRaisesRegex(KPPError,'capture'):read_evidence(self.ws,observation['id'])

    def test_unknown_inventory_entry_and_actorless_observation_refused(self):
        with self.assertRaisesRegex(KPPError,'pinned inventory'):self.record(entries=['missing'])
        with self.assertRaisesRegex(KPPError,'actor'):record_capture(self.ws,self.left,'reference','screenshot','','normal','state')

    def test_portable_preview_retains_captures_without_transfer_of_current_evidence(self):
        reference=self.record();candidate=self.record('candidate')
        compare_captures(self.ws,reference['id'],candidate['id'],'review')
        bundle=self.root/'preview.zip';out=self.root/'restored'
        export_preview(self.ws,bundle);import_preview(bundle,out)
        self.assertEqual(inspection(out)['accepted'],0)
        self.assertEqual(len(summary(out)['stale']),3)
        self.assertEqual((out/reference['capture']['path']).read_bytes(),self.left.read_bytes())


if __name__=='__main__':unittest.main()
