"""Small, side-effect-free offline stack evaluator for verified framed bytes."""
from .bytecode import decode
from .canonical import sha256, dumps
from .parser import parse_inputs
from .types import TRUE,FALSE,UNKNOWN,and3,or3,not3,geo_outside,timestamp
from .errors import refuse

VM_VERSION='reflex-python-vm/0.1'


def _seconds(delta):
    return delta.days*86400 + delta.seconds


def run(raw:bytes,input_source):
    bc=decode(raw)   # Verify edition, hash, static rights, exact compiler identity.
    program=bc['ir']
    env=parse_inputs(input_source,program)
    stack=[]
    trace=[]
    result=None
    vals=env['values']
    for pc,ins in enumerate(bc['instructions']):
        trace.append(pc)
        op,*args=ins
        if op=='PUSH_BOOL3':
            stack.append(args[0])
        elif op=='LOAD_INPUT':
            stack.append(vals.get(args[0]))
        elif op=='LOAD_CONST':
            stack.append(args[0])
        elif op=='CHECK_KNOWN':
            stack.append(TRUE if args[0] in vals else FALSE)
        elif op=='CHECK_FRESH':
            fix=vals.get(args[0])
            if fix is None:
                stack.append(UNKNOWN)
            else:
                age=_seconds(timestamp(env['clock_utc'])-timestamp(fix['observed_at']))
                stack.append(TRUE if 0 <= age <= args[1] else UNKNOWN)
        elif op=='CHECK_QUALITY':
            fix=vals.get(args[0])
            stack.append(UNKNOWN if fix is None or fix['accuracy_m']>args[1] else TRUE)
        elif op=='GEO_OUTSIDE':
            region=stack.pop();fix=stack.pop()
            stack.append(UNKNOWN if fix is None or region is None else geo_outside(fix,region))
        elif op=='EQ':
            right=stack.pop();left=stack.pop()
            stack.append(UNKNOWN if left is None or right is None else TRUE if left==right else FALSE)
        elif op=='RANGE':
            item=stack.pop()
            stack.append(UNKNOWN if item is None else TRUE if args[0]<=item<=args[1] else FALSE)
        elif op=='AND3':
            n=args[0];group=stack[-n:];del stack[-n:];stack.append(and3(group))
        elif op=='OR3':
            n=args[0];group=stack[-n:];del stack[-n:];stack.append(or3(group))
        elif op=='GUARD3':
            n=args[0];group=stack[-n:];del stack[-n:]
            stack.append(group[0] if all(g==TRUE for g in group[1:]) else UNKNOWN)
        elif op=='NOT3':
            stack.append(not3(stack.pop()))
        elif op=='BRANCH3':
            if len(stack)!=1 or stack[-1] not in (TRUE,FALSE,UNKNOWN):
                refuse('E_VM','unbalanced Bool3 stack')
            state=stack.pop()
            status=program['outcomes'][state.lower()]
            result={'status':status,'review_requested':status=='REQUEST_REVIEW' or
                    (status=='ANOMALY' and program['on_anomaly']=='REQUEST_REVIEW')}
        elif op=='HALT':
            if result is None or stack or pc!=len(bc['instructions'])-1:
                refuse('E_VM','invalid final machine state')
            break
        else:
            refuse('E_OPCODE', 'unsupported instruction')
    if result is None:
        refuse('E_VM','missing result')
    if len(dumps(result))>program['limits']['max_result_bytes']:
        refuse('E_SIZE','result budget exceeded')
    return {'schema':'mantle.reflex-trace/0.1', 'vm_version':VM_VERSION,
            'program_sha256':bc['program_sha256'], 'input_sha256':sha256(env),
            'executed_pcs':trace, 'result':result, 'refusal_code':None,
            'authorized':False}
