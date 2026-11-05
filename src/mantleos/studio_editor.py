"""Explicit owner selection of verified local presentation source.

Configuration stays in the existing Studio controller database. It contains no
provider credentials, founding material, model context, or acceptance records.
"""
from pathlib import Path
from contextlib import contextmanager
import os
import subprocess
import uuid

from . import json_contract as c
from .transactions import body_lock

SCHEMA = 'studio.editor-route/1'
KEY = 'editor_config'
FIELDS = {'schema', 'revision', 'package_root', 'editor_profile', 'catalog_root',
          'catalog_profile', 'installation_sha256', 'inspection', 'sha256'}
INSPECTION_FIELDS = {'schema', 'reference', 'editor_source_digest', 'catalog_source_digest',
                     'sha256', 'files', 'asset_bytes', 'nodes', 'credential_types',
                     'version_entries', 'authority', 'workflow_execution'}


def _absolute(value):
    # Preserve link components for the Node verifier; resolve() would hide them.
    result = os.path.abspath(os.fspath(value))
    c.text(result, maximum=32768)
    return result


def inspect_source(*, node, package_root, editor_profile, catalog_root, catalog_profile):
    script = Path(__file__).parent/'kpp/resources/examples/anchor-studio/editor-installation.cjs'
    result = subprocess.run([os.fspath(node), str(script), '--package', _absolute(package_root),
        '--editor-profile', _absolute(editor_profile), '--catalog', _absolute(catalog_root),
        '--catalog-profile', _absolute(catalog_profile)], capture_output=True, timeout=120)
    c.require(result.returncode == 0 and len(result.stdout) <= 65536, 'Editor installation rejected')
    try:
        value = c.loads(result.stdout.decode('utf8'))
    except (ValueError, UnicodeError) as error:
        raise ValueError('Invalid editor inspection') from error
    return _inspection(value)


def _hash(value):
    c.require(type(value) is str and len(value) == 64 and all(ch in '0123456789abcdef' for ch in value),
              'Invalid editor source binding')
    return value


def _inspection(value):
    c.shape(value, INSPECTION_FIELDS)
    c.require(value['schema'] == 'studio.editor-installation/1'
              and value['reference'] == 'n8n@2.46.4' and value['authority'] == 'NONE'
              and value['workflow_execution'] == 'NOT_GRANTED_BY_INSTALLATION', 'Invalid editor inspection')
    for key in ('editor_source_digest', 'catalog_source_digest', 'sha256'):
        _hash(value[key])
    identity = {key: value[key] for key in ('schema', 'reference', 'editor_source_digest', 'catalog_source_digest')}
    c.require(c.digest(identity) == value['sha256'], 'Editor installation binding changed')
    for key, limit in (('files', 2048), ('asset_bytes', 64*1024*1024), ('nodes', 10000),
                       ('credential_types', 10000), ('version_entries', 10000)):
        c.require(type(value[key]) is int and 0 <= value[key] <= limit, 'Invalid editor inspection counts')
    return value


def _validate(value):
    options = {'manual_execution', 'credential_editor'} & value.keys() if type(value) is dict else set()
    c.shape(value, FIELDS | options)
    c.require(all(value[key] is True for key in options), 'Invalid editor capability selection')
    c.require(value['schema'] == SCHEMA, 'Unsupported editor configuration')
    try:
        revision = uuid.UUID(value['revision'])
    except (ValueError, TypeError, AttributeError) as error:
        raise ValueError('Invalid editor revision') from error
    c.require(str(revision) == value['revision'] and revision.version == 4, 'Invalid editor revision')
    for key in ('package_root', 'editor_profile', 'catalog_root', 'catalog_profile'):
        c.text(value[key], maximum=32768)
        c.require(os.path.isabs(value[key]), 'Editor configuration requires absolute paths')
    _hash(value['installation_sha256'])
    _inspection(value['inspection'])
    c.require(value['inspection']['sha256'] == value['installation_sha256'], 'Editor inspection changed')
    c.require(c.digest({k: v for k, v in value.items() if k != 'sha256'}) == value['sha256'], 'Editor configuration changed')
    return value


def from_database(db):
    row = db.execute('SELECT value FROM settings WHERE key=?', (KEY,)).fetchone()
    return None if row is None else _validate(c.loads(row[0]))


def private_config(nest):
    """Trusted foreground-controller pipe only; never a presentation endpoint."""
    from .studio import database
    with database(nest) as db:
        return from_database(db)


def public_status(nest):
    value = private_config(nest)
    return {'enabled': False} if value is None else {
        'enabled': True, 'revision': value['revision'], 'installation': value['inspection'],
        'scope': 'BUILDING_NOT_ACCEPTED', 'context': 'RESIDENT_MEMORY',
        **({'manual_execution': 'PURE_NODE_RED'} if value.get('manual_execution') else {}),
        **({'credential_editor': 'WINDOWS_OWNER_LOCAL'} if value.get('credential_editor') else {})}


@contextmanager
def _writer(nest, reviewed):
    from .studio import database, _setting
    from .limbs import worker_lease
    if reviewed is not True:
        raise PermissionError('Explicit owner review required')
    with worker_lease(nest, 'controller'), body_lock(Path(nest)), database(nest) as db:
        c.require(_setting(db, 'phase') == 'STASIS', 'Editor source selection requires stopped Studio in stasis')
        c.require(not db.execute("SELECT 1 FROM mind WHERE phase='AWAITING_MIND' LIMIT 1").fetchone(),
                  'Recover pending cognition before selecting editor source')
        yield db


def configure(nest, *, node, package_root, editor_profile, catalog_root, catalog_profile,
              manual_execution=False, credential_editor=False, reviewed=False):
    import time
    c.require(type(manual_execution) is bool, 'Manual execution selection requires a boolean')
    c.require(type(credential_editor) is bool, 'Credential editor selection requires a boolean')
    with _writer(nest, reviewed) as db:
        inspection = _inspection(inspect_source(node=node, package_root=package_root, editor_profile=editor_profile,
                                                catalog_root=catalog_root, catalog_profile=catalog_profile))
        from .studio_inventory import EditorInventory
        EditorInventory(nest).initialize(reviewed=True)
        value = {'schema': SCHEMA, 'revision': str(uuid.uuid4()),
                 'package_root': _absolute(package_root), 'editor_profile': _absolute(editor_profile),
                 'catalog_root': _absolute(catalog_root), 'catalog_profile': _absolute(catalog_profile),
                 'installation_sha256': inspection['sha256'], 'inspection': inspection}
        if manual_execution:
            value['manual_execution'] = True
        if credential_editor:
            from .studio import _setting
            from .studio_credentials import CredentialStore
            CredentialStore(nest, _setting(db, 'identity')).initialize(reviewed=True)
            value['credential_editor'] = True
        value['sha256'] = c.digest(value)
        db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', (KEY, c.canonical(value)))
        db.execute('INSERT INTO events(id,kind,value,at) VALUES (?,?,?,?)',
                   ('editor-'+uuid.uuid4().hex, 'editor.source.reviewed',
                    c.canonical({'revision': value['revision'], 'installation_sha256': inspection['sha256'],
                                 **{key: True for key in ('manual_execution', 'credential_editor') if key in value}}), time.time()))
    return {'enabled': True, 'revision': value['revision'], 'installation': inspection,
            'scope': 'BUILDING_NOT_ACCEPTED',
            'authority': 'Pure manual Node-RED execution' if manual_execution else 'No workflow effects or Baker acceptance granted'}


def disable(nest, *, reviewed=False):
    """Withdraw the optional presentation without deleting source or memory."""
    import time
    with _writer(nest, reviewed) as db:
        current=from_database(db)
        if current is not None:
            db.execute('DELETE FROM settings WHERE key=?', (KEY,))
            db.execute('INSERT INTO events(id,kind,value,at) VALUES (?,?,?,?)',
                       ('editor-'+uuid.uuid4().hex, 'editor.source.withdrawn',
                        c.canonical({'configuration_sha256':current['sha256']}),time.time()))
    return {'enabled':False}
