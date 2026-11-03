import importlib.util
from pathlib import Path
import unittest
from mantleos import studio,anchors

PATH=Path(studio.__file__).parent/'kpp/resources/tools/studio_chase_inventory.py'
spec=importlib.util.spec_from_file_location('studio_chase_inventory_test',PATH)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class StudioChaseInventoryTests(unittest.TestCase):
    def test_declarations_are_not_dynamic_or_runtime_proof(self):
        text="const ITEM_ID = {\n OPEN: 'open-menu',\n SAVE: 'save-file',\n};\nconst dynamic=items.map(x=>({id:x.name}));"
        result=module.declarations(text,'useExampleCommands.ts')
        self.assertEqual([r['command'] for r in result],['open-menu','save-file'])
        self.assertEqual([r['line'] for r in result],[2,3])
        self.assertTrue(all(r['source']=='useExampleCommands.ts' for r in result))

    def test_context_union_and_shared_canonical_definitions(self):
        text="export type ContextMenuAction =\n | 'copy'\n | 'delete';"
        self.assertEqual([r['command'] for r in module.declarations(text,'useContextMenuItems.ts')],['copy','delete'])
        design=module.design()
        for value in design['applications']:self.assertEqual(anchors.validate(value),value)
        altered=design['applications'][0].copy();altered['singularity']='Model says grant execution'
        with self.assertRaises(ValueError):anchors.validate(altered)
