"""Apply KPP recipe/3 attributes to the shared immutable Anchor model.

This is an interoperability binding, not a second scheduler or approval system.
The original recipe remains intact in attributes. No import activates a bake.
"""
from . import anchors, json_contract as contract


def bind(recipe):
    contract.require(type(recipe) is dict and recipe.get('schema') in ('kpp.recipe/3', 'kpp.recipe/4'),
                     'Unsupported KPP recipe version')
    contract.require(recipe.get('schema') == 'kpp.recipe/3' or recipe.get('anchor_binding', 'none') == 'shared-neutral',
                     'Recipe must explicitly select anchor_binding shared-neutral')
    contract.identifier(recipe.get('id'))
    contract.text(recipe.get('goal'))
    obligations = recipe.get('anchors')
    contract.require(type(obligations) is list and bool(obligations), 'KPP recipe needs obligations')
    ids = set()
    for item in obligations:
        contract.require(type(item) is dict, 'Invalid KPP obligation')
        contract.identifier(item.get('id'))
        contract.require(item['id'] not in ids, 'Duplicate KPP obligation')
        ids.add(item['id'])
        contract.text(item.get('statement'))
        contract.text(item.get('test'))
        contract.require(type(item.get('required')) is bool, 'KPP required flag must be boolean')
        contract.require(type(item.get('depth')) is int and 1 <= item['depth'] <= 32, 'Invalid Fidelity depth')
        contract.require(type(item.get('depends', [])) is list, 'Invalid KPP dependency list')
    edges = {item['id']: item.get('depends', []) for item in obligations}
    visited = set()

    def visit(identifier, active):
        contract.require(identifier in ids and identifier not in active, 'Unknown or cyclic KPP dependency')
        if identifier in visited:
            return
        for other in edges[identifier]:
            visit(other, active | {identifier})
        visited.add(identifier)

    for identifier in ids:
        visit(identifier, set())
    preserve = recipe.get('transformation', {}).get('preserve', [])
    for prop in preserve:
        contract.require(any(item['required'] and prop in item.get('preserves', []) for item in obligations),
                         'Preserved property has no mandatory Anchor application')
    root = anchors.application(recipe['id'], attributes={'protocol': 'KPP', 'recipe': recipe})
    applications = [anchors.application(item['id'], attributes={
        'protocol': 'KPP', 'recipe_sha256': contract.digest(recipe), 'obligation': item,
    }) for item in obligations]
    return {'schema': 'mantle.kpp-binding/1', 'method': root, 'applications': applications,
            'scope': 'Shared Anchor binding; full KPP workspace validation/acceptance stays in KPP',
            'authorized': False}


def inspect_binding(value):
    """Rebind from retained recipe and reject detached or altered projections."""
    contract.require(type(value) is dict and value.get('schema') == 'mantle.kpp-binding/1',
                     'Unsupported KPP binding version')
    method = anchors.validate(value['method'])
    contract.require(method['definition'] == 'Neutral', 'KPP uses the shared Neutral Anchor')
    expected = bind(method['attributes']['recipe'])
    contract.require(value == expected, 'KPP attributes or references changed')
    return {'result': 'VALID', 'recipe': method['id'], 'applications': len(value['applications']),
            'anchor_types': ['Neutral'], 'authorized': False}
