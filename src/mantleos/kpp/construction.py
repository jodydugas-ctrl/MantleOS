"""Recipe-selected construction techniques; no execution or approval."""
from .core import KPPError

def construction_plan(recipe):
    declared = recipe.get('construction')
    if 'construction' not in recipe:
        return {'techniques': ['chase'], 'basis': 'legacy-default', 'ordering': 'chase'}
    if recipe.get('schema') != 'kpp.recipe/4':
        raise KPPError('construction requires kpp.recipe/4; legacy recipes are not migrated')
    if not isinstance(declared, dict) or set(declared) != {'techniques'}:
        raise KPPError('construction must contain only techniques: [] or ["chase"]')
    choices = declared['techniques']
    if not isinstance(choices, list) or choices not in ([], ['chase']):
        raise KPPError('construction.techniques supports [] or ["chase"]; duplicates and unsupported techniques are refused')
    return {'techniques': list(choices), 'basis': 'recipe-selected',
            'ordering': 'chase' if choices else 'requirements'}
