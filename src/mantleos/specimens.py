"""Fresh example construction. Imported history and runtimes are never inherited."""
from pathlib import Path
import hashlib
import os
import shutil
import tempfile
import uuid

from . import birth, cartridge, compiled, lifecycle, primer, vault_auto, vault_store
from .transactions import body_lock, write_json


def founding_material(source):
    source = Path(source)
    from . import kernel
    format = 'chroma' if source.read_bytes()[:8] == b'\x89PNG\r\n\x1a\n' else 'cartridge'
    with tempfile.TemporaryDirectory(prefix='mantle-founding-') as td:
        root = Path(td) / 'source'
        kernel.verify_restored_output(source, root, format=format)
        cartridge.verify(root)
        primer.verify_lock(root)
        return (compiled.read_json(root / 'BIRTH.json'),
                {name: (root / 'PRIMER' / name).read_bytes() for name in ('PERSONA.md', 'COMMANDMENTS.md')},
                {'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                 'format': format, 'executed': False})


def fresh(output, *, name='Example Engram', identity=None, expression='engram',
          founding=None, parent=None, mission=None):
    """Construct, verify, and publish a new instance; founding is operator-selected data."""
    if expression not in {'engram', 'bio-agent', 'appai'}:
        raise ValueError('Unsupported expression')
    identity = identity or 'example-' + uuid.uuid4().hex[:16]
    if founding:
        original, raw_primer, evidence = founding
        kwargs = dict(persona_name=original['primer']['persona_name'],
                      persona=raw_primer['PERSONA.md'].decode('utf-8').replace('\r\n', '\n'),
                      commandments=raw_primer['COMMANDMENTS.md'].decode('utf-8').replace('\r\n', '\n'))
    else:
        raw_primer, evidence = None, {'source': 'synthetic'}
        kwargs = dict(persona_name=name, persona=f'{name}. Preserve evidence, uncertainty, and host authority.')
    definition = birth.make_birth(bio_id=identity, name=name,
                                  description='Fresh ' + expression + '; no inherited experience.', **kwargs)
    destination = lifecycle._destination(output, parent)
    stage = destination.parent / ('.' + destination.name + '.fresh-' + uuid.uuid4().hex)
    with body_lock(destination):
        try:
            lifecycle.create(definition, stage, parent=parent, inherit_memory=False, portable=False)
            if raw_primer:
                for filename, data in raw_primer.items():
                    (stage / 'PRIMER' / filename).write_bytes(data)
                primer.create_lock(stage)
            descriptor = {'schema': 'mantle.expression/1', 'type': expression,
                          'birth': 'fresh', 'inherited_experience': False, 'source': evidence}
            if mission is not None:
                descriptor['mission'] = mission['id']
                write_json(stage / 'MISSION.json', mission)
            write_json(stage / 'EXPRESSION.json', descriptor)
            identity_binding = vault_auto.mounted_identity(stage)
            anchor = vault_store.initialize(stage / 'ARCHIVE.rvcar', identity_binding)
            write_json(stage / 'VAULT-REF.json', {'schema': 'raven.vault-binding/1',
                       'file_name': 'ARCHIVE.rvcar', 'location': 'embedded',
                       'identity': identity_binding, 'root_sha256': anchor['sha256']})
            lifecycle.finalize(stage)
            os.rename(stage, destination)
            return {'result': 'CREATED', 'body': str(destination), 'identity': identity,
                    'expression': expression, 'records': 0, 'primer_sha256': primer.load_primer(destination)['sha256']}
        finally:
            if stage.exists():
                shutil.rmtree(stage)


def representative(parent, output, mission_id, *, context=None, policy_id=None):
    parent = Path(parent)
    compiled.load(parent)
    descriptor = compiled.read_json(parent / 'EXPRESSION.json')
    if descriptor['type'] != 'appai' or descriptor.get('mission'):
        raise PermissionError('Only a resident AppAI can create representatives')
    source = (compiled.read_json(parent / 'BIRTH.json'),
              {n: (parent / 'PRIMER' / n).read_bytes() for n in ('PERSONA.md', 'COMMANDMENTS.md')},
              {'parent_identity': compiled.read_json(parent / 'BIRTH.json')['id'],
               'parent_primer_sha256': primer.load_primer(parent)['sha256']})
    mission = {'schema': 'mantle.representative-mission/1', 'id': mission_id,
               'parent': source[2]['parent_identity'], 'policy_id': policy_id,
               'purpose': 'Read-only specimen inspection', 'context': context or {},
               'authority_carried': False, 'recursive_delegation': False}
    return fresh(output, name='Representative', identity='rep-' + mission_id,
                 founding=source, parent=parent, mission=mission)
