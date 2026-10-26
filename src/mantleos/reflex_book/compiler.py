"""Compile a validated, declarative AST into a bounded stack instruction stream."""
from .checker import validate
from .errors import refuse
from .canonical import sha256

BYTECODE_SCHEMA='mantle.reflex-bytecode/0.1'
VM_ABI='reflex-vm/0.1'


def instructions(program):
    code = []

    def emit(op,*args):
        code.append([op,*args])

    def operand(value):
        if 'input' in value:
            emit('LOAD_INPUT',value['input'])
        else:
            emit('LOAD_CONST',value['const']['value'])

    def predicate(node):
        op = node['op']
        if op == 'literal':
            emit('PUSH_BOOL3',node['value'])
        elif op == 'known':
            emit('CHECK_KNOWN',node['input'])
        elif op == 'outside_region':
            emit('LOAD_INPUT',node['position']['input'])
            emit('LOAD_INPUT',node['region']['input'])
            emit('GEO_OUTSIDE')
        elif op == 'compare_eq':
            operand(node['left']);operand(node['right']);emit('EQ')
        elif op == 'compare_range':
            emit('LOAD_INPUT',node['input']);emit('RANGE',node['min'],node['max'])
        elif op in ('and','or'):
            for item in node['args']:
                predicate(item)
            emit('AND3' if op == 'and' else 'OR3',len(node['args']))
        elif op == 'not':
            predicate(node['arg']);emit('NOT3')
        else:
            raise AssertionError('unsupported opcode passed static checker')

    predicate(program['predicate'])
    for pre in program['preconditions']:
        emit('CHECK_FRESH' if pre['op'] == 'fresh' else 'CHECK_QUALITY',
             pre['input'],pre.get('max_age_seconds',pre.get('max_accuracy_m')))
    if program['preconditions']:
        emit('GUARD3',len(program['preconditions'])+1)
    emit('BRANCH3')
    emit('HALT')
    return code


def compile_ir(program):
    validate(program)
    code = instructions(program)
    if len(code) > program['limits']['max_instructions']:
        refuse('E_LIMIT','instruction count exceeds program limit')
    return {'schema':BYTECODE_SCHEMA,'abi':VM_ABI,
            'program_sha256':sha256(program),'ir':program,'instructions':code}
