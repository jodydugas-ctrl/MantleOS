"""Program composition over supported Anchor profiles, independent of CELL kernels."""
from copy import deepcopy
from pathlib import Path

from . import json_contract as contract
from .anchor_language import inspect_blueprint

PROGRAM_SCHEMA = 'mantle.program/1'
TISSUE_SCHEMA = 'mantle.tissue/2'
PROFILES = {'EMIT_TEXT/0.2', 'NOTEPAD_LLM/1.3'}


def program(identifier, profile, payload, *, dependencies=(), capabilities=()):
    value = dict(schema=PROGRAM_SCHEMA, id=identifier, profile=profile, payload=payload,
                 dependencies=list(dependencies), capabilities=list(capabilities))
    value['sha256'] = contract.digest(value)
    return validate_program(value)


def validate_program(value):
    contract.shape(value, {'schema', 'id', 'profile', 'payload', 'dependencies', 'capabilities', 'sha256'})
    contract.require(value['schema'] == PROGRAM_SCHEMA, 'Unsupported program version')
    contract.identifier(value['id'])
    name = value['id'].split('.')[0].upper()
    reserved = {'CON', 'PRN', 'AUX', 'NUL'} | {f'{kind}{n}' for kind in ('COM', 'LPT') for n in range(1, 10)}
    contract.require(name not in reserved and not value['id'].endswith('.'), 'Nonportable program id')
    contract.require(value['profile'] in PROFILES, 'Unsupported program semantic profile')
    contract.text(value['payload'], maximum=262144)
    for key in ('dependencies', 'capabilities'):
        items = value[key]
        contract.require(type(items) is list and len(items) <= 64, 'Invalid program requirements')
        for item in items:
            contract.identifier(item)
        contract.require(len(set(items)) == len(items), 'Duplicate program requirement')
    contract.require(not value['capabilities'], 'These Anchor profiles grant no external capabilities')
    contract.require(value['sha256'] == contract.digest({k: v for k, v in value.items() if k != 'sha256'}),
                     'Program digest mismatch')
    report = inspect_blueprint(value['payload'])
    contract.require(report['profile'] == value['profile'], 'Program profile mismatch')
    return deepcopy(value)


def tissue(identifier, programs):
    value = dict(schema=TISSUE_SCHEMA, id=identifier, programs=list(programs))
    value['sha256'] = contract.digest(value)
    return validate_tissue(value)


def validate_tissue(value):
    contract.shape(value, {'schema', 'id', 'programs', 'sha256'})
    contract.require(value['schema'] == TISSUE_SCHEMA, 'Unsupported tissue version')
    contract.identifier(value['id'])
    contract.require(type(value['programs']) is list and 1 <= len(value['programs']) <= 64, 'Invalid tissue size')
    contract.require(value['sha256'] == contract.digest({k: v for k, v in value.items() if k != 'sha256'}),
                     'Tissue digest mismatch')
    by_id = {}
    for item in value['programs']:
        checked = validate_program(item)
        contract.require(checked['id'].casefold() not in {k.casefold() for k in by_id}, 'Duplicate program id')
        by_id[checked['id']] = checked
    visited, active = set(), set()

    def visit(name):
        contract.require(name in by_id, 'Missing program dependency')
        contract.require(name not in active, 'Cyclic program dependencies')
        if name in visited:
            return
        active.add(name)
        for dependency in by_id[name]['dependencies']:
            visit(dependency)
        active.remove(name)
        visited.add(name)

    for name in by_id:
        visit(name)
    return deepcopy(value)


def write_programs(directory, value):
    from .transactions import write_json
    value = validate_tissue(value)
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    programs = []
    for item in value['programs']:
        source = item['id'] + '.anchor'
        (directory / source).write_text(item['payload'], encoding='utf-8', newline='\n')
        programs.append({'id': item['id'], 'profile': item['profile'], 'source': source})
    catalog = directory / 'PROGRAMS.json'
    write_json(catalog, {'schema': 'mantle.programs/1', 'programs': programs})
    return catalog


def verify_body(body):
    from .compiled import read_json, relative_file
    body = Path(body)
    value = validate_tissue(read_json(body / 'TISSUE.json'))
    catalog = read_json(body / 'PROGRAMS.json')['programs']
    by_id = {p['id']: p for p in catalog}
    contract.require(len(by_id) == len(catalog) and set(by_id) == {p['id'] for p in value['programs']},
                     'Tissue program membership mismatch')
    for item in value['programs']:
        actual = by_id[item['id']]
        contract.require(actual['profile'] == item['profile'], 'Tissue program profile mismatch')
        contract.require(relative_file(body, actual['source']).read_text('utf-8') == item['payload'],
                         'Tissue payload differs from executable source')
    return value
