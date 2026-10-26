"""Independent AST oracle for the prototype. Always supply an explicit clock."""
from .parser import parse_inputs
from .types import TRUE, FALSE, UNKNOWN, and3, or3, not3, geo_outside, timestamp
from .canonical import sha256, dumps


def _seconds(delta):
    return delta.days*86400 + delta.seconds


def precondition(pre, env):
    fix = env['values'].get(pre['input'])
    if fix is None:
        return UNKNOWN
    if pre['op'] == 'quality_at_least':
        return TRUE if fix['accuracy_m'] <= pre['max_accuracy_m'] else UNKNOWN
    age = _seconds(timestamp(env['clock_utc']) - timestamp(fix['observed_at']))
    return TRUE if 0 <= age <= pre['max_age_seconds'] else UNKNOWN


def evaluate_pred(node, vals):
    op = node['op']
    if op == 'literal':
        return node['value']
    if op == 'known':
        return TRUE if node['input'] in vals else FALSE
    if op == 'outside_region':
        fix, region = vals.get(node['position']['input']), vals.get(node['region']['input'])
        return geo_outside(fix, region) if fix is not None and region is not None else UNKNOWN
    if op == 'compare_eq':
        def get(operand):
            return vals.get(operand['input']) if 'input' in operand else operand['const']['value']
        l, r = get(node['left']), get(node['right'])
        return UNKNOWN if l is None or r is None else TRUE if l == r else FALSE
    if op == 'compare_range':
        value = vals.get(node['input'])
        return UNKNOWN if value is None else TRUE if node['min'] <= value <= node['max'] else FALSE
    if op == 'and':
        return and3(evaluate_pred(x, vals) for x in node['args'])
    if op == 'or':
        return or3(evaluate_pred(x, vals) for x in node['args'])
    if op == 'not':
        return not3(evaluate_pred(node['arg'], vals))
    raise AssertionError('static checker must refuse unsupported op')


def run(program, input_source):
    from .checker import validate
    program = validate(program)
    env = parse_inputs(input_source,program)
    pred = evaluate_pred(program['predicate'],env['values'])
    guards = [precondition(p,env) for p in program['preconditions']]
    decision = UNKNOWN if any(g != TRUE for g in guards) else pred
    status = program['outcomes'][decision.lower()]
    result = {'status':status,'review_requested':
              status == 'REQUEST_REVIEW' or (status == 'ANOMALY' and program['on_anomaly'] == 'REQUEST_REVIEW')}
    return result
