"""Bounded, untrusted Capability Chase state outside the portable Body.

Reference text and receipts are evidence, never permission. No function here
executes source, installs dependencies, or patches the live runtime.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import copy
import math
import os
from pathlib import Path
import re
import tempfile
import time
from urllib.parse import urlsplit
import uuid
from .common import ScanError, canonical, outside, read_json, sha

INPUT_LIMIT = 1024 * 1024
STATE_LIMIT = 8 * INPUT_LIMIT
COLLECTIONS = ('targets', 'challenges', 'observations', 'proposals', 'receipt_links', 'reviews')
ID = re.compile(r'[a-z][a-z0-9-]{2,63}\Z')
HASH = re.compile(r'[0-9a-f]{64}\Z')
PROTECTED = {'birth.json', 'primer', 'cartridge.json', 'systems.json', 'compiled.json',
             'manifest.json', 'engram.jsonl', 'engram.md', 'bio-software.json',
             'cell.json', 'body-state.json', 'source-pins.json'}


def exact(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys.split()):
        raise ScanError('Unknown or missing Chase record fields')


def text(value, maximum=1500, minimum=1):
    if not isinstance(value, str) or not value.strip() or not minimum <= len(value) <= maximum:
        raise ScanError('Invalid bounded Chase text')
    return value


def identifier(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ScanError('Invalid stable Chase identifier')
    return value


def hash_value(value, nullable=False):
    if nullable and value is None:
        return value
    if not isinstance(value, str) or not HASH.fullmatch(value):
        raise ScanError('Expected lowercase SHA-256')
    return value


def url(value, nullable=False):
    if nullable and value is None:
        return value
    text(value, 2048)
    parsed = urlsplit(value)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or any(c.isspace() for c in value):
        raise ScanError('Expected an HTTPS reference URL without credentials')
    return value


def utc(value):
    text(value, 64)
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ScanError('Expected UTC ISO-8601 timestamp') from exc
    if result.tzinfo is None or result.utcoffset().total_seconds() != 0:
        raise ScanError('Expected UTC timestamp')
    return result


def bounded(value, limit=INPUT_LIMIT):
    try:
        encoded = canonical(value).encode('utf-8')
    except (TypeError, ValueError, RecursionError) as exc:
        raise ScanError('Invalid finite JSON data') from exc
    if len(encoded) > limit:
        raise ScanError('Chase JSON budget exceeded')
    return copy.deepcopy(value)


def revision(value):
    if type(value) is not int or value < 0:
        raise ScanError('Expected nonnegative integer revision')


def _path(workspace, body=None):
    path = Path(workspace).absolute()
    for part in (path, *path.parents):
        if part.is_symlink() or (hasattr(part, 'is_junction') and part.is_junction()):
            raise ScanError('Chase workspace cannot traverse symlinks or junctions')
    if body is not None:
        outside(path, body)
    folder = path / 'chase-v2'
    for part in (folder, folder / 'state.json', folder / '.write.lock'):
        if part.is_symlink() or (hasattr(part, 'is_junction') and part.is_junction()):
            raise ScanError('Chase state cannot traverse symlinks or junctions')
    return folder


def empty():
    return {'schema': 'mantle.chase.state/2', 'revision': 0, **{key: [] for key in COLLECTIONS}}


def _catalog(value):
    value = bounded(value)
    exact(value, 'schema catalog_id catalog_version targets')
    if value['schema'] != 'mantle.chase.catalog/2':
        raise ScanError('Unsupported Chase catalog schema')
    text(value['catalog_id'], 128)
    if type(value['catalog_version']) is not int or value['catalog_version'] < 1:
        raise ScanError('Invalid catalog version')
    if not isinstance(value['targets'], list) or not 1 <= len(value['targets']) <= 32:
        raise ScanError('Catalog needs 1..32 targets')
    target_ids, challenge_ids = set(), set()
    for target in value['targets']:
        exact(target, 'target_id name reference_url reference_kind capabilities')
        identifier(target['target_id']); text(target['name'], 100); url(target['reference_url'])
        if target['reference_kind'] != 'OFFICIAL_DOCS_UNPINNED' or target['target_id'] in target_ids:
            raise ScanError('Invalid or duplicate reference target')
        target_ids.add(target['target_id'])
        if not isinstance(target['capabilities'], list) or not 1 <= len(target['capabilities']) <= 16:
            raise ScanError('Target needs 1..16 challenges')
        for challenge in target['capabilities']:
            exact(challenge, 'challenge_id title scope evaluation')
            identifier(challenge['challenge_id']); text(challenge['title'], 120); text(challenge['scope'], 1500, 10)
            if challenge['challenge_id'] in challenge_ids:
                raise ScanError('Duplicate challenge identifier')
            challenge_ids.add(challenge['challenge_id'])
            evaluation = challenge['evaluation']
            exact(evaluation, 'fixture oracle metric comparator threshold sample_size environment expected_result')
            for key, maximum, minimum in (('fixture',128,1), ('oracle',1500,8), ('metric',128,1),
                                          ('environment',1000,1), ('expected_result',1000,5)):
                text(evaluation[key], maximum, minimum)
            number = evaluation['threshold']
            if type(number) not in (int, float) or not math.isfinite(number) or number < 0:
                raise ScanError('Invalid evaluation threshold')
            if evaluation['comparator'] not in ('>=', '<=', '==') or type(evaluation['sample_size']) is not int or not 1 <= evaluation['sample_size'] <= 10000:
                raise ScanError('Invalid evaluation comparator/sample size')
    return value


def _observation(value):
    value = bounded(value)
    exact(value, 'schema observation_id kind source_url source_digest environment statement evidence_grade observed_at artifact_sha256 notes')
    if value['schema'] != 'mantle.chase.observation/2' or value['kind'] not in ('LOCAL_TEST', 'REFERENCE_DOC'):
        raise ScanError('Invalid observation schema/kind')
    text(value['observation_id'], 128); text(value['environment'],1000); text(value['statement'])
    url(value['source_url'], True); hash_value(value['source_digest'], True); hash_value(value['artifact_sha256'], True); utc(value['observed_at'])
    if not isinstance(value['notes'], str) or len(value['notes']) > 1500 or value['evidence_grade'] not in ('UNVERIFIED', 'STATIC_CLAIM', 'MEASURED_LOCAL'):
        raise ScanError('Invalid observation grade/notes')
    if value['evidence_grade'] == 'MEASURED_LOCAL' and (value['kind'] != 'LOCAL_TEST' or value['artifact_sha256'] is None):
        raise ScanError('Local measurement needs a local test artifact')
    return value


def list_catalog(workspace, *, body=None):
    path = _path(workspace, body) / 'state.json'
    if not path.exists():
        return empty()
    state = read_json(path, STATE_LIMIT)
    exact(state, 'schema revision ' + ' '.join(COLLECTIONS))
    if state['schema'] != 'mantle.chase.state/2':
        raise ScanError('Invalid Chase state schema')
    revision(state['revision'])
    if any(not isinstance(state[key], list) or len(state[key]) > 4096 for key in COLLECTIONS):
        raise ScanError('Invalid Chase collection/budget')
    # Revalidate seeds and observations on every read, including persisted status.
    if state['targets']:
        first = state['targets'][0]
        catalog = {'schema':'mantle.chase.catalog/2', 'catalog_id':first['catalog_id'],
                   'catalog_version':first['catalog_version'], 'targets':[]}
        for target in state['targets']:
            exact(target, 'target_id name reference_url reference_kind capabilities catalog_id catalog_version')
            if target['catalog_id'] != first['catalog_id'] or target['catalog_version'] != first['catalog_version']:
                raise ScanError('Conflicting stored catalog identities')
            catalog['targets'].append({k:v for k,v in target.items() if k not in ('catalog_id','catalog_version')})
        _catalog(catalog)
        expected = _seed_state(catalog)['challenges']
        if state['challenges'] != expected:
            raise ScanError('Stored challenge identity/status changed')
    elif state['challenges']:
        raise ScanError('Challenges need seeded targets')
    known = {c['challenge_id'] for c in state['challenges']}
    seen = set()
    for item in state['observations']:
        if item.get('challenge_id') not in known or item.get('observation_id') in seen:
            raise ScanError('Unknown/duplicate stored observation')
        _observation({k:v for k,v in item.items() if k != 'challenge_id'})
        seen.add(item['observation_id'])
    from .chase_pipeline import validate_state
    validate_state(state)
    return state


@contextmanager
def transaction(workspace, expected_revision=None, *, body=None, timeout=1):
    if expected_revision is not None:
        revision(expected_revision)
    folder = _path(workspace, body)
    folder.mkdir(parents=True, exist_ok=True)
    lock = folder / '.write.lock'
    token = uuid.uuid4().hex.encode('ascii')
    deadline = time.monotonic() + timeout
    while True:
        _path(workspace, body)
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise ScanError('Chase writer lock busy; stale locks require operator inspection')
            time.sleep(0.025)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(token); stream.flush(); os.fsync(stream.fileno())
    try:
        state = list_catalog(workspace, body=body)
        if expected_revision is not None and state['revision'] != expected_revision:
            raise ScanError('Stale Chase revision')
        before = canonical(state)
        yield state
        if canonical(state) != before:
            from .chase_pipeline import validate_state
            validate_state(state)
            state['revision'] += 1
            encoded = canonical(bounded(state, STATE_LIMIT)) + '\n'
            if len(encoded.encode('utf-8')) > STATE_LIMIT:
                raise ScanError('Chase serialized state budget exceeded')
            handle, name = tempfile.mkstemp(prefix='.state-', dir=folder)
            try:
                with os.fdopen(handle, 'w', encoding='utf-8', newline='\n') as stream:
                    stream.write(encoded); stream.flush(); os.fsync(stream.fileno())
                _path(workspace, body)
                os.replace(name, folder / 'state.json')
                if os.name != 'nt':
                    fd = os.open(folder, os.O_RDONLY)
                    try: os.fsync(fd)
                    finally: os.close(fd)
            finally:
                if os.path.exists(name): os.unlink(name)
    finally:
        if lock.is_symlink() or lock.read_bytes() != token:
            raise ScanError('Chase writer lock ownership changed')
        lock.unlink()


def _seed_state(catalog):
    state = empty()
    for target in catalog['targets']:
        state['targets'].append({**target, 'catalog_id':catalog['catalog_id'], 'catalog_version':catalog['catalog_version']})
        for challenge in target['capabilities']:
            state['challenges'].append({**challenge, 'target_id':target['target_id'], 'status':'UNVERIFIED_REFERENCE'})
    return state


def seed_catalog(workspace, catalog, *, body=None):
    seed = _seed_state(_catalog(catalog))
    with transaction(workspace, body=body) as state:
        if state['targets'] and (state['targets'] != seed['targets'] or state['challenges'] != seed['challenges']):
            raise ScanError('Reseed conflict; existing immutable catalog differs')
        state['targets'], state['challenges'] = seed['targets'], seed['challenges']
    return state


def challenge(state, challenge_id):
    item = next((c for c in state['challenges'] if c['challenge_id'] == challenge_id), None)
    if item is None: raise ScanError('Unknown Chase challenge')
    return item


def record_observation(workspace, challenge_id, observation, expected_revision, *, body=None):
    item = _observation(observation)
    revision(expected_revision)
    with transaction(workspace, expected_revision, body=body) as state:
        challenge(state, challenge_id)
        if any(o['observation_id'] == item['observation_id'] for o in state['observations']):
            raise ScanError('Duplicate observation identifier')
        state['observations'].append({**item, 'challenge_id':challenge_id})
    return state


def build_scorecard(workspace, *, challenge_ids=None, body=None):
    state = list_catalog(workspace, body=body)
    if challenge_ids is not None and (not isinstance(challenge_ids,list) or len(challenge_ids) > 512 or len(set(challenge_ids)) != len(challenge_ids)):
        raise ScanError('Invalid scorecard selection')
    for key in challenge_ids or []: challenge(state, key)
    rows = []
    for item in state['challenges']:
        if challenge_ids is not None and item['challenge_id'] not in challenge_ids: continue
        row = {'challenge_id':item['challenge_id'], 'title':item['title'], 'scope':item['scope'],
                     'test_state':'UNVERIFIED_REFERENCE', 'evidence_grade':'UNVERIFIED',
                     'local_metrics':None, 'reference_status':'UNVERSIONED_UNVERIFIED', 'gap_status':'UNKNOWN',
                     'observations':[o['observation_id'] for o in state['observations'] if o['challenge_id'] == item['challenge_id']],
                     'blocking_missing_evidence':['Matched fixture, independent oracle and environment measurements',
                                                  'Separately pinned and measured external reference'],
                     'evaluation':item['evaluation']}
        links = [r for r in state['receipt_links'] if r['kind'] == 'EXPERIMENT' and r['challenge_id'] == item['challenge_id']]
        if links:
            link = links[-1]
            path = Path(link['receipt_path'])
            if path.is_file() and not path.is_symlink() and sha(path.read_bytes()) == link['receipt_sha256']:
                row.update(test_state=link['test_state'], evidence_grade='MEASURED_LOCAL',
                           local_metrics={item['evaluation']['metric']:link['local_result']['value']},
                           blocking_missing_evidence=['Separately pinned and measured external reference'],
                           receipt_sha256=link['receipt_sha256'])
            else:
                row['blocking_missing_evidence'].append('Linked experiment receipt missing or changed')
        comparisons = [r for r in state['receipt_links'] if r['kind'] == 'COMPARISON' and r['challenge_id'] == item['challenge_id']]
        if comparisons and row['test_state'] == 'LOCAL_CAPABILITY_DEMONSTRATED':
            comparison = comparisons[-1]
            path = Path(comparison['receipt_path'])
            if (path.is_file() and not path.is_symlink() and sha(path.read_bytes()) == comparison['receipt_sha256']
                    and comparison['local_receipt_sha256'] == row['receipt_sha256']):
                row.update(test_state='COMPARATIVE_RESULT_VERIFIED',reference_status='PINNED_AND_TESTED',
                           gap_status='NO_GAP_WITHIN_DECLARED_CHECK_SCOPE',blocking_missing_evidence=[])
        rows.append(row)
    return {'schema':'mantle.chase.scorecard/2', 'revision':state['revision'], 'challenges':rows, 'promotion_authority':False}
