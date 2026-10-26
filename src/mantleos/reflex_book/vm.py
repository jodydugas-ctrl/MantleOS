"""Bounded evaluation with explicit preparation; handles carry no authority."""
from dataclasses import dataclass
from types import MappingProxyType
from .bytecode import decode
from .canonical import sha256, dumps
from .parser import parse_inputs
from .types import TRUE, FALSE, UNKNOWN, and3, or3, not3, geo_outside, timestamp
from .errors import refuse

VM_VERSION = 'reflex-python-vm/0.1'
_SEAL = object()


@dataclass(frozen=True, slots=True, init=False)
class PreparedProgram:
    """Process-local immutable verified structure, never an approval credential.

    Construct with prepare(). This protects normal API use, not a hostile Python
    host that can replace module globals or bypass Python object protections.
    """
    _program: object
    _instructions: tuple
    _program_sha256: str
    _seal: object


def prepare(raw):
    """Verify exact framed bytes and compile-check once. Does not execute."""
    bc = decode(raw)
    ir = bc['ir']
    program = MappingProxyType({
        'inputs': MappingProxyType(dict(ir['inputs'])),
        'limits': MappingProxyType(dict(ir['limits'])),
        'outcomes': MappingProxyType(dict(ir['outcomes'])),
        'on_anomaly': ir['on_anomaly'],
    })
    prepared = object.__new__(PreparedProgram)
    object.__setattr__(prepared, '_program', program)
    object.__setattr__(prepared, '_instructions', tuple(tuple(i) for i in bc['instructions']))
    object.__setattr__(prepared, '_program_sha256', bc['program_sha256'])
    object.__setattr__(prepared, '_seal', _SEAL)
    return prepared


def _seconds(delta):
    return delta.days * 86400 + delta.seconds


def run(raw: bytes, input_source):
    """Compatibility API: prepare untrusted bytes, then return the legacy trace."""
    return run_prepared(prepare(raw), input_source)


def run_prepared(prepared, input_source, *, explain=False):
    """Execute verified structure without parsing/compiling the program again.

    Every call still validates and snapshots its inputs. The host must separately
    enforce current approval, revocation, dependency and resource policies.
    explain=True opts into trace/0.2 with deterministic UNKNOWN reasons.
    """
    if (type(prepared) is not PreparedProgram
            or getattr(prepared, '_seal', None) is not _SEAL):
        refuse('E_VM', 'prepare() must produce the program handle')
    if type(explain) is not bool:
        refuse('E_TYPE', 'explain must be boolean')
    program = prepared._program
    env = parse_inputs(input_source, program)
    vals = env['values']
    stack, trace = [], []
    result = decision = None
    final_reasons = ()

    def reason(code, pc, name=None):
        return ((code, name, pc),) if explain else ()

    for pc, ins in enumerate(prepared._instructions):
        trace.append(pc)
        op, *args = ins
        if op == 'PUSH_BOOL3':
            stack.append((args[0], reason('EXPLICIT_UNKNOWN', pc) if args[0] == UNKNOWN else ()))
        elif op == 'LOAD_INPUT':
            name = args[0]
            stack.append((vals.get(name), reason('INPUT_MISSING', pc, name) if name not in vals else ()))
        elif op == 'LOAD_CONST':
            stack.append((args[0], ()))
        elif op == 'CHECK_KNOWN':
            stack.append((TRUE if args[0] in vals else FALSE, ()))
        elif op == 'CHECK_FRESH':
            name, limit = args
            fix = vals.get(name)
            code = None
            if fix is None:
                code = 'INPUT_MISSING'
            else:
                age = _seconds(timestamp(env['clock_utc']) - timestamp(fix['observed_at']))
                if age < 0:
                    code = 'OBSERVATION_FUTURE'
                elif age > limit:
                    code = 'OBSERVATION_STALE'
            stack.append((UNKNOWN if code else TRUE, reason(code, pc, name) if code else ()))
        elif op == 'CHECK_QUALITY':
            name, limit = args
            fix = vals.get(name)
            code = 'INPUT_MISSING' if fix is None else 'QUALITY_INADEQUATE' if fix['accuracy_m'] > limit else None
            stack.append((UNKNOWN if code else TRUE, reason(code, pc, name) if code else ()))
        elif op == 'GEO_OUTSIDE':
            region, rr = stack.pop()
            fix, fr = stack.pop()
            if fix is None or region is None:
                value, reasons = UNKNOWN, fr + rr
            else:
                value, reasons = geo_outside(fix, region), ()
                if value == UNKNOWN:
                    reasons = reason('GEOMETRY_UNSUPPORTED' if abs(fix['lat_e6']) > 55000000 else 'BOUNDARY_UNCERTAIN', pc)
            stack.append((value, reasons))
        elif op == 'EQ':
            right, rr = stack.pop()
            left, lr = stack.pop()
            value = UNKNOWN if left is None or right is None else TRUE if left == right else FALSE
            stack.append((value, lr + rr if value == UNKNOWN else ()))
        elif op == 'RANGE':
            value, reasons = stack.pop()
            stack.append((UNKNOWN if value is None else TRUE if args[0] <= value <= args[1] else FALSE,
                          reasons if value is None else ()))
        elif op in ('AND3', 'OR3', 'GUARD3'):
            n = args[0]
            group = stack[-n:]
            del stack[-n:]
            values = [item[0] for item in group]
            if op == 'GUARD3':
                failed = [item for item in group[1:] if item[0] != TRUE]
                value = UNKNOWN if failed else values[0]
                relevant = failed if failed else group[:1]
            else:
                value = and3(values) if op == 'AND3' else or3(values)
                relevant = [item for item in group if item[0] == UNKNOWN]
            reasons = tuple(r for _, rs in relevant for r in rs) if value == UNKNOWN else ()
            stack.append((value, reasons))
        elif op == 'NOT3':
            value, reasons = stack.pop()
            stack.append((not3(value), reasons))
        elif op == 'BRANCH3':
            if len(stack) != 1 or stack[-1][0] not in (TRUE, FALSE, UNKNOWN):
                refuse('E_VM', 'unbalanced Bool3 stack')
            decision, final_reasons = stack.pop()
            status = program['outcomes'][decision.lower()]
            result = {'status': status, 'review_requested': status == 'REQUEST_REVIEW' or
                      (status == 'ANOMALY' and program['on_anomaly'] == 'REQUEST_REVIEW')}
        elif op == 'HALT':
            if result is None or stack or pc != len(prepared._instructions) - 1:
                refuse('E_VM', 'invalid final machine state')
            break
        else:
            refuse('E_OPCODE', 'unsupported instruction')
    if result is None:
        refuse('E_VM', 'missing result')
    if len(dumps(result)) > program['limits']['max_result_bytes']:
        refuse('E_SIZE', 'result budget exceeded')
    report = {'schema': 'mantle.reflex-trace/0.1', 'vm_version': VM_VERSION,
              'program_sha256': prepared._program_sha256, 'input_sha256': sha256(env),
              'executed_pcs': trace, 'result': result, 'refusal_code': None, 'authorized': False}
    if explain:
        report.update(schema='mantle.reflex-trace/0.2-experimental', decision=decision,
                      reasons=[{'code': code, 'input': name, 'pc': pc}
                               for code, name, pc in dict.fromkeys(final_reasons)])
    return report
