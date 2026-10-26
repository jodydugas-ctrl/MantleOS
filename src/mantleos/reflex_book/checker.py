"""Strict field/type/right/budget verification for the anomaly-basic dialect."""
import re
from .errors import refuse

IDENT = re.compile(r'^[a-z][a-z0-9_]{0,47}$')
PID = re.compile(r'^[a-z][a-z0-9_-]{0,47}(?:\.[a-z][a-z0-9_-]{0,47})+$')
BOOK = {'id': 'reflex', 'edition': '0.1', 'dialect': 'anomaly-basic'}
LIMIT_CAPS = {'max_nodes': 256, 'max_input_bytes': 65536,
              'max_instructions': 512, 'max_result_bytes': 2048}
TYPES = {'Int', 'GeoFix', 'Region'}
OUTCOMES = {'NORMAL', 'ANOMALY', 'UNKNOWN', 'REQUEST_REVIEW'}


def exact(value, keys, context):
    if type(value) is not dict or set(value) != set(keys):
        refuse('E_SHAPE', f'{context} fields must be exactly {sorted(keys)}')


def natural(value, low, high, label):
    if type(value) is not int or not low <= value <= high:
        refuse('E_LIMIT', f'{label} outside [{low},{high}]')


def require_type(inputs, name, expected):
    if type(name) is not str or name not in inputs:
        refuse('E_INPUT_REF', f'undeclared input {name!r}')
    if inputs[name] != expected:
        refuse('E_TYPE', f'input {name} must be {expected}')
    return name


def _ref(value, inputs, expected, used):
    exact(value, {'input'}, 'input expression')
    name = require_type(inputs, value['input'], expected)
    used.add(name)
    return name


def _operand(node, inputs, used):
    if type(node) is not dict:
        refuse('E_SHAPE', 'Int operand must be an object')
    exact(node, {'input'} if 'input' in node else {'const'}, 'Int operand')
    if 'input' in node:
        return _ref(node, inputs, 'Int', used)
    exact(node['const'], {'type','value'}, 'Int constant')
    if node['const']['type'] != 'Int' or type(node['const']['value']) is not int or not -(2**31) <= node['const']['value'] < 2**31:
        refuse('E_TYPE', 'only bounded Int constants allowed')
    return None


def validate(program):
    # Revalidate direct Python API callers, not just JSON-parser callers.
    # Import locally to keep the canonical codec independent of checking.
    from .canonical import dumps, MAX_SOURCE_BYTES
    if len(dumps(program)) > MAX_SOURCE_BYTES:
        refuse('E_SIZE', 'canonical program exceeds source byte budget')
    exact(program, {'schema','book','id','inputs','preconditions','predicate','outcomes','on_anomaly','capabilities','limits'}, 'program')
    if program['schema'] != 'mantle.reflex-ir/0.1':
        refuse('E_EDITION', 'unsupported IR schema')
    if program['book'] != BOOK:
        refuse('E_EDITION', 'unsupported Book/edition/dialect')
    if type(program['id']) is not str or not PID.fullmatch(program['id']):
        refuse('E_ID', 'invalid program id')
    inputs = program['inputs']
    if type(inputs) is not dict or not 1 <= len(inputs) <= 32:
        refuse('E_SHAPE', 'inputs must define 1..32 entries')
    for name, kind in inputs.items():
        if type(name) is not str or not IDENT.fullmatch(name) or type(kind) is not str or kind not in TYPES:
            refuse('E_TYPE', 'unsupported input name or type')
    limits = program['limits']
    exact(limits, LIMIT_CAPS, 'limits')
    for name, ceiling in LIMIT_CAPS.items():
        natural(limits[name], 1, ceiling, name)
    preconds = program['preconditions']
    if type(preconds) is not list or len(preconds) > 32:
        refuse('E_SHAPE', 'preconditions must be a list of at most 32')
    seen, guarded, used = set(), {}, set()
    for p in preconds:
        if type(p) is not dict or 'op' not in p:
            refuse('E_SHAPE', 'invalid precondition')
        op = p['op']
        field = 'max_age_seconds' if op == 'fresh' else 'max_accuracy_m' if op == 'quality_at_least' else None
        if field is None:
            refuse('E_OPCODE', 'unsupported precondition')
        exact(p, {'op','input',field}, 'precondition')
        name = require_type(inputs, p['input'], 'GeoFix')
        used.add(name)
        natural(p[field], 1, 86400 if op == 'fresh' else 100000, field)
        if (op,name) in seen:
            refuse('E_DUPLICATE', 'duplicate precondition')
        seen.add((op,name))
        guarded.setdefault(name,set()).add(op)
    count = 0
    geo_used = set()

    def visit(node, depth=0):
        nonlocal count
        count += 1
        if depth > 32:
            refuse('E_DEPTH', 'predicate nesting too deep')
        if type(node) is not dict or 'op' not in node:
            refuse('E_SHAPE', 'predicate must have op')
        op = node['op']
        if op == 'literal':
            exact(node, {'op','value'}, op)
            if node['value'] not in ('TRUE','FALSE','UNKNOWN'):
                refuse('E_TYPE', 'Bool3 literal must be TRUE/FALSE/UNKNOWN')
        elif op == 'known':
            exact(node, {'op','input'}, op)
            if type(node['input']) is not str or node['input'] not in inputs:
                refuse('E_INPUT_REF', 'unknown input')
            used.add(node['input'])
        elif op == 'outside_region':
            exact(node, {'op','position','region'}, op)
            geo_used.add(_ref(node['position'],inputs,'GeoFix',used))
            _ref(node['region'],inputs,'Region',used)
        elif op == 'compare_eq':
            exact(node, {'op','left','right'}, op)
            _operand(node['left'],inputs,used)
            _operand(node['right'],inputs,used)
        elif op == 'compare_range':
            exact(node, {'op','input','min','max'}, op)
            _ref({'input':node['input']}, inputs,'Int',used)
            if type(node['min']) is not int or type(node['max']) is not int or not -(2**31)<=node['min']<=node['max']<2**31:
                refuse('E_RANGE', 'invalid Int range')
        elif op in ('and','or'):
            exact(node, {'op','args'}, op)
            if type(node['args']) is not list or not 2 <= len(node['args']) <= 16:
                refuse('E_SHAPE', 'and/or requires 2..16 arguments')
            for arg in node['args']:
                visit(arg, depth+1)
        elif op == 'not':
            exact(node, {'op','arg'}, op)
            visit(node['arg'],depth+1)
        else:
            refuse('E_OPCODE', f'unsupported predicate: {str(op)[:40]}')

    visit(program['predicate'])
    for name in geo_used:
        if guarded.get(name, set()) != {'fresh','quality_at_least'}:
            refuse('E_GUARD', f'outside_region requires fresh and quality guards on {name}')
    if count + len(preconds) > limits['max_nodes']:
        refuse('E_LIMIT', 'node budget exceeded')
    outcomes = program['outcomes']
    exact(outcomes, {'true','false','unknown'}, 'outcomes')
    if any(type(x) is not str or x not in OUTCOMES for x in outcomes.values()):
        refuse('E_TYPE', 'invalid outcome Result enum')
    if outcomes['unknown'] not in ('UNKNOWN','REQUEST_REVIEW'):
        refuse('E_AUTHORITY', 'UNKNOWN predicate cannot become NORMAL/ANOMALY')
    if type(program['on_anomaly']) is not str or program['on_anomaly'] not in ('NONE','REQUEST_REVIEW'):
        refuse('E_AUTHORITY', 'on_anomaly only declares NONE or REQUEST_REVIEW result flag')
    rights = program['capabilities']
    if type(rights) is not list or len(set(map(str, rights))) != len(rights) or any(type(r) is not str for r in rights):
        refuse('E_CAPABILITY', 'duplicate or invalid capability')
    if set(rights) != {'read:'+name for name in used}:
        refuse('E_CAPABILITY', 'capabilities must exactly match referenced read-only inputs')
    # A static budget must cover every possible enumerated result; otherwise
    # structurally accepted programs could fail only once a branch is reached.
    from .canonical import dumps
    statuses = set(outcomes.values())
    required_result_bytes = max(len(dumps({
        'status': status,
        'review_requested': status == 'REQUEST_REVIEW' or (
            status == 'ANOMALY' and program['on_anomaly'] == 'REQUEST_REVIEW')
    })) for status in statuses)
    if required_result_bytes > limits['max_result_bytes']:
        refuse('E_LIMIT', 'max_result_bytes cannot hold declared outcomes')
    return program
