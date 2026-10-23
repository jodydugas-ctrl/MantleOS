"""KPP 0.3: shared graph, preservation coverage and non-mutating Economy gate."""
import copy
import tempfile
import unittest
from pathlib import Path

from mantleos.kpp.core import KPPError, find_repo_root, read_json, validate_recipe, write_json, digest
from mantleos.kpp.graph import coverage, chase, functional_graph, load_scan
from mantleos.kpp.economy import evaluate
from mantleos.kpp.workshop import begin, load, accept, finish, install_module, inspection
from mantleos.kpp.scanner import scan
from mantleos.kpp.cli import main

ROOT = find_repo_root()
TRANS = read_json(ROOT/'recipes/portable-memory-bake.json')
NOTE = read_json(ROOT/'recipes/notepad-demo.json')


class GraphAndEconomy(unittest.TestCase):
    def test_preserved_property_must_appear_on_mandatory_anchor(self):
        r=copy.deepcopy(TRANS)
        del next(a for a in r['anchors'] if a['id']=='bounded-intent')['preserves']
        with self.assertRaisesRegex(KPPError, 'missing mandatory Anchor coverage'):
            validate_recipe(r)
        r=copy.deepcopy(TRANS)
        a=next(a for a in r['anchors'] if a['id']=='bounded-intent')
        a['required']=False
        with self.assertRaisesRegex(KPPError, 'Only mandatory'):
            validate_recipe(r)
        r=copy.deepcopy(TRANS)
        a=next(a for a in r['anchors'] if a['id']=='bounded-intent')
        a['preserves']=['unknown property']
        with self.assertRaises(KPPError):validate_recipe(r)

    def test_no_untracked_transformation_or_phantom_completion(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws=Path(tmp)/'ws'
            begin(ws,TRANS,ROOT)
            r,s=load(ws)
            audit=coverage(r,s)
            self.assertEqual(len(audit['preservation']),3)
            self.assertEqual(len(audit['unaccepted_properties']),3)
            with self.assertRaises(KPPError):finish(ws)
            for a in TRANS['anchors']:
                accept(ws,a['id'],'Observed manually (synthetic test evidence)', 'test-baker')
            r,s=load(ws)
            self.assertEqual(coverage(r,s)['unaccepted_properties'],[])
            rec=finish(ws)
            self.assertEqual(len(rec['coverage']['preservation']),3)
            self.assertEqual(rec['coverage']['attestation_kinds']['manual'],5)
            self.assertIn('not independent audit',rec['acceptance_type'])

    def test_graph_is_derived_and_not_mutating_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws=Path(tmp)/'ws'
            begin(ws,NOTE,ROOT)
            recipe,state=load(ws)
            original=(ws/'state.json').read_bytes()
            graph=functional_graph(recipe,state)
            self.assertEqual(graph['schema'],'kpp.functional-graph/1')
            self.assertTrue(any(e['kind']=='depends-on' for e in graph['edges']))
            self.assertEqual(graph['views']['chase'],chase(recipe,state))
            self.assertEqual(original,(ws/'state.json').read_bytes())
            accept(ws,'ui-surface','checked manually','baker')
            recipe,state=load(ws)
            graph2=functional_graph(recipe,state)
            self.assertEqual(next(n for n in graph2['nodes'] if n['id']=='anchor:ui-surface')['status'],'BAKER_ACCEPTED')
            install_module(ws,'edit',ROOT/'previews/notepad/edit.js')
            recipe,state=load(ws)
            graph3=functional_graph(recipe,state)
            self.assertEqual(next(n for n in graph3['nodes'] if n['id']=='anchor:ui-surface')['status'],'UNMET')

    def test_static_scan_is_not_claimed_as_runtime_proof(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'src';src.mkdir()
            (src/'sample.py').write_text('def a():\n    return b()\ndef b():\n    return 3\n',encoding='utf-8')
            scan_path=Path(tmp)/'scan.json'
            write_json(scan_path,scan(src,3))
            loaded=load_scan(scan_path)
            ws=Path(tmp)/'ws';begin(ws,NOTE,ROOT)
            recipe,state=load(ws)
            graph=functional_graph(recipe,state,loaded)
            self.assertTrue(any(e['basis']=='static-source-observation-not-runtime-proof' for e in graph['edges']))
            self.assertTrue(graph['scan']['limitations'])
            invalid=Path(tmp)/'invalid.json';write_json(invalid,{'schema':'other'})
            with self.assertRaises(KPPError):load_scan(invalid)

    def test_economy_gate_non_destructive(self):
        proposal={'schema':'kpp.economy-proposal/1','merges':[
            {'from':['open-file'],'into':'save-file',
             'coverage_rationale':'Share a file-action dispatcher while retaining separate effects',
             'comparison_tests':['Test open existing draft and UTF-8 saving against baseline']}]}
        result=evaluate(NOTE,proposal)
        self.assertEqual(result['decision'],'PROPOSAL_ONLY_REQUIRES_RECIPE_REVISION_AND_RETEST')
        self.assertEqual(result['proof_status'],'NOT_PROVEN')
        self.assertEqual(result['hypothetical_count'],5)
        self.assertEqual(len(NOTE['anchors']),6)
        bad=copy.deepcopy(proposal)
        bad['merges'][0]['comparison_tests']=[]
        self.assertEqual(evaluate(NOTE,bad)['decision'],'REJECTED_STRUCTURAL')

    def test_economy_preservation_cannot_be_deleted(self):
        proposal={'schema':'kpp.economy-proposal/1','merges':[{
            'from':['bounded-intent'],'into':'safe-bridge',
            'coverage_rationale':'simplify interface',
            'comparison_tests':['Old-vs-new intent operation test']}]}
        result=evaluate(TRANS,proposal)
        self.assertEqual(result['decision'],'REJECTED_STRUCTURAL')
        self.assertTrue(any('preservation' in msg.lower() for msg in result['blocking_gaps']))

    def test_cli_graph_coverage_economy(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws=Path(tmp)/'ws';begin(ws,NOTE,ROOT)
            prop=Path(tmp)/'eco.json'
            write_json(prop,{'schema':'kpp.economy-proposal/1','merges':[
                {'from':['open-file'],'into':'save-file','coverage_rationale':'one file organ',
                 'comparison_tests':['Separate open/save parity checks']}]})
            self.assertEqual(main(['coverage','--workspace',str(ws)]),0)
            outfile=Path(tmp)/'graph.json'
            self.assertEqual(main(['graph','--workspace',str(ws),'--out',str(outfile)]),0)
            self.assertTrue(outfile.is_file())
            self.assertEqual(main(['economy','--workspace',str(ws),'--proposal',str(prop)]),0)

if __name__ == '__main__': unittest.main()
