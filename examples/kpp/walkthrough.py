"""One Anchor model across KPP recipes, executable specimens, and kernel CELLs."""
from pathlib import Path
import argparse
import json

from mantleos import anchor_language, anchors, cells, kitchen, organism, lifecycle
from mantleos.transactions import write_json


def run(output):
    root = Path(output).resolve(); root.mkdir(parents=True, exist_ok=False)
    examples = Path(__file__).parent
    recipe = json.loads((examples / 'recipe.json').read_text('utf-8'))
    binding = kitchen.bind(recipe)
    kitchen.inspect_binding(binding)
    write_json(root / 'KPP-ANCHOR.json', binding)
    programs = {}
    for path in (examples / 'specimens').glob('*.anchor'):
        programs[path.name] = anchor_language.execute_blueprint(path.read_text('utf-8'))['effect_claim']
    # Source emission is data; the four emitted Python specimens are not run.
    pixel = cells.produce('chroma.rgb/1', [17, 34, 51])
    segment = cells.append_segment({'seq': 1, 'observation': 'Synthetic record'})
    write_json(root / 'CELLS.json', [pixel, segment])
    organism.create(root / 'body', identity='kpp-synthetic')
    result = lifecycle.run(root / 'body', 'greeting')
    if result['result']['stdout'] != 'Ready to remember.':
        raise ValueError('Deterministic Body greeting changed')
    report = {'result': 'PASS', 'anchor_types': list(anchors.TYPES),
              'kpp_anchor': binding['method']['type'], 'singularity_constant': True,
              'kpp_recipe_preserved': binding['method']['attributes']['recipe'] == recipe,
              'cell_units': ['RGB pixel', 'appended record'],
              'specimens': programs, 'body_result': result['result'],
              'kpp_workspace_acceptance': 'NOT_GRANTED', 'model_calls': 0}
    write_json(root / 'report.json', report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    print(json.dumps(run(parser.parse_args().output), indent=2))
