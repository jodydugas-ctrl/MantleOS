"""Language intent, optional Anchor binding and unchanged legacy identities."""
import copy
from pathlib import Path
import tempfile
import subprocess
import sys
import os
import unittest
from unittest.mock import patch

from mantleos import anchors, kitchen
from mantleos.kpp import core, graph, workshop, build
from mantleos.kpp.language import implementation_plan

RESOURCE = Path(core.__file__).parent/'resources'


def recipe(policy='required', languages=None, selected=None):
    value=core.read_json(RESOURCE/'recipes/notepad-demo.json')
    value.update(schema='kpp.recipe/4', tissue='python', delivery_mode='artifact',
                 ingredients=[], product_kind='conventional', capabilities={})
    value.pop('preview',None)
    value['implementation']={'components':[{'id':'app','policy':policy,'languages':languages or ['python']}]}
    if selected is not None:value['implementation']['components'][0].update(selected=selected,rationale='Explicit recipe preparation decision')
    return value


class LanguageTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name)

    def test_generic_workflow_never_binds_anchor_model(self):
        value=recipe();original=copy.deepcopy(value)
        with patch.object(anchors,'definition',side_effect=AssertionError('Anchor dependency')), patch.object(kitchen,'bind',side_effect=AssertionError('Binding dependency')):
            core.validate_recipe(value)
            state=workshop.begin(self.root/'ws',value,RESOURCE)
            derived=graph.functional_graph(value,state)
            self.assertIsNone(derived['anchor_binding'])
            self.assertTrue(all('application' not in n for n in derived['nodes'] if n['kind']=='anchor'))
            self.assertIn('Implementation choices',workshop.handoff(self.root/'ws'))
            self.assertEqual('none',build.step(self.root/'ws')['implementation']['anchor_binding'])
        self.assertEqual(original,value)

    def test_legacy_recipes_hashes_graph_and_workspace_unchanged(self):
        for path in (RESOURCE/'recipes').glob('*.json'):
            value=core.read_json(path)
            if value['schema']!='kpp.recipe/3':continue
            before=copy.deepcopy(value);pin=core.digest(value)
            core.validate_recipe(value);self.assertEqual(before,value);self.assertEqual(pin,core.digest(value))
            self.assertEqual('shared-neutral',implementation_plan(value)['anchor_binding'])
        value=core.read_json(RESOURCE/'recipes/notepad-demo.json')
        state=workshop.begin(self.root/'legacy',value,RESOURCE)
        self.assertEqual(value,workshop.load(self.root/'legacy')[0])
        self.assertEqual(kitchen.bind(value),graph.functional_graph(value,state)['anchor_binding'])

    def test_explicit_binding_and_definition_immutability(self):
        value=recipe();value['anchor_binding']='shared-neutral'
        core.validate_recipe(value)
        bound=kitchen.bind(value);self.assertFalse(bound['authorized'])
        self.assertEqual('VALID',kitchen.inspect_binding(bound)['result'])
        for field in ('type','definition','singularity'):
            changed=copy.deepcopy(value);changed['anchors'][0][field]='invented'
            with self.subTest(field=field),self.assertRaises(core.KPPError):core.validate_recipe(changed)
        value.pop('anchor_binding')
        with self.assertRaises(ValueError):kitchen.bind(value)
        value['anchors'][0]['type']='Neutral'
        with self.assertRaises(core.KPPError):core.validate_recipe(value)

    def test_unresolved_preparation_is_read_only_and_cannot_publish(self):
        for policy in ('preferred','recommend'):
            value=recipe(policy);value['tissue']='unspecified';before=copy.deepcopy(value)
            self.assertFalse(implementation_plan(value)['ready']);self.assertEqual(before,value)
            with self.assertRaisesRegex(core.KPPError,'Resolve implementation'):workshop.begin(self.root/policy,value,RESOURCE)
            self.assertFalse((self.root/policy).exists())

    def test_required_choice_cannot_be_overridden(self):
        value=recipe();component=value['implementation']['components'][0]
        component['selected']='rust'
        with self.assertRaisesRegex(core.KPPError,'conflicts'):core.validate_recipe(value)
        component['selected']='python';core.validate_recipe(value)

    def test_preferred_override_requires_rationale(self):
        value=recipe('preferred',selected='python');item=value['implementation']['components'][0]
        item['languages']=['rust']
        self.assertTrue(implementation_plan(value)['components'][0]['outside_preferences'])
        item.pop('rationale')
        with self.assertRaisesRegex(core.KPPError,'rationale'):core.validate_recipe(value)

    def test_multi_language_and_rust_declarations_never_execute(self):
        value=recipe();value['tissue']='mixed'
        value['implementation']['components'].append({'id':'worker','policy':'required','languages':['rust']})
        report=implementation_plan(value)
        self.assertTrue(report['ready']);self.assertEqual('NONE',report['execution'])
        self.assertEqual('NOT_PROVIDED',report['components'][1]['execution_support'])
        self.assertTrue(all(c['verification']=='NOT_RUN' for c in report['components']))
        value['implementation']['components']=value['implementation']['components'][1:];value['tissue']='unspecified'
        core.validate_recipe(value)

    def test_malformed_duplicate_and_misplaced_choices_rejected(self):
        cases=[]
        value=recipe();value['implementation']['components']*=2;cases.append(value)
        value=recipe();value['implementation']['components'][0]['languages']=['python','python'];cases.append(value)
        value=recipe();value['implementation']['components'][0]['policy']='automatic';cases.append(value)
        value=recipe();value['implementation']['components'][0]['compiler']='rustc';cases.append(value)
        value=recipe();value['implementation']['components'][0]['profile']='invented';cases.append(value)
        value=recipe();value['anchor_binding']='alternate-model';cases.append(value)
        value=recipe();value['implementation_language']='rust';cases.append(value)
        value=recipe();value['schema']='kpp.recipe/3';cases.append(value)
        for index,value in enumerate(cases):
            with self.subTest(index=index),self.assertRaises(core.KPPError):core.validate_recipe(value)

    def test_tissue_preview_and_profile_consistency(self):
        value=recipe();value['tissue']='javascript'
        with self.assertRaisesRegex(core.KPPError,'tissue conflicts'):core.validate_recipe(value)
        value=core.read_json(RESOURCE/'recipes/notepad-organs.json');value['schema']='kpp.recipe/4'
        value['implementation']={'components':[{'id':'app','policy':'required','languages':['python']}]}
        value['tissue']='python'
        with self.assertRaisesRegex(core.KPPError,'Progressive-web'):core.validate_recipe(value)
        value=recipe();value['tissue']='anchor';value['implementation']['components'][0].update(languages=['anchor'],profile='EMIT_TEXT/0.2')
        self.assertEqual('QUALIFIED_PROFILES_ONLY',implementation_plan(value)['components'][0]['execution_support'])
        value['implementation']['components'][0]['profile']='UNKNOWN/9'
        with self.assertRaisesRegex(core.KPPError,'Unsupported Anchor'):core.validate_recipe(value)

    def test_cli_reports_language_choices_and_refuses_unbound_bind(self):
        value=recipe();path=self.root/'recipe.json';core.write_json(path,value)
        env={**os.environ,'PYTHONPATH':str(RESOURCE.parents[2])}
        command=[sys.executable,'-m','mantleos','kpp']
        result=subprocess.run(command+['language-plan','--recipe',str(path)],capture_output=True,env=env,timeout=30)
        self.assertEqual(0,result.returncode,result.stderr.decode(errors='replace'))
        self.assertIn(b'NOT_RUN',result.stdout)
        result=subprocess.run(command+['bind','--recipe',str(path)],capture_output=True,env=env,timeout=30)
        self.assertNotEqual(0,result.returncode)

    def test_decision_changes_invalidate_recipe_identity_and_acceptance(self):
        value=recipe();ws=self.root/'ws';workshop.begin(ws,value,RESOURCE)
        changed=copy.deepcopy(value);changed['implementation']['components'][0]['rationale']='Revised rationale'
        self.assertNotEqual(core.digest(value),core.digest(changed))
        core.write_json(ws/'recipe.json',changed)
        with self.assertRaisesRegex(core.KPPError,'recipe changed'):workshop.load(ws)


if __name__=='__main__':unittest.main()
