"""Parse untrusted proposed programs or input fixtures, never Python code."""
from .canonical import loads, dumps
from .checker import validate, exact
from .types import timestamp, validate_value
from .errors import refuse


def parse_program(source):
    return validate(loads(source))


def parse_inputs(source, program):
    # Enforce the same bounded JSON data contract for direct in-memory API calls.
    # Without this, a caller could bypass duplicate/number/NFC/size checks by
    # passing a Python dict rather than a JSON byte string.
    inp = loads(source) if type(source) in (str, bytes) else loads(dumps(source))
    exact(inp, {'schema','clock_utc','values'}, 'input envelope')
    if inp['schema'] != 'mantle.reflex-input/0.1':
        refuse('E_EDITION', 'unsupported input envelope')
    timestamp(inp['clock_utc'])
    if type(inp['values']) is not dict:
        refuse('E_SHAPE', 'input values must be an object')
    if set(inp['values']) - set(program['inputs']):
        refuse('E_INPUT_REF', 'undeclared input provided')
    if len(dumps(inp)) > program['limits']['max_input_bytes']:
        refuse('E_SIZE', 'input budget exceeded')
    for name, value in inp['values'].items():
        validate_value(program['inputs'][name],value)
    return inp
