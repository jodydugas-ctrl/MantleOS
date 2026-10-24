"""Fresh Engrams with recipe-selected transport; imports never activate a carrier."""
import json
from pathlib import Path
import tempfile
import uuid
from .core import KPPError, validate_recipe
from .. import birth, lifecycle, cartridge, chromamem

CARRIERS = {'vcw-cartridge-memory': 'vcw', 'chroma-png-memory': 'chroma'}
PERSONA = Path(__file__).with_name('resources')/'personas/raven.md'

def selection(recipe):
    recipe = validate_recipe(recipe)
    chosen = [name for name in recipe['ingredients'] if name in CARRIERS]
    if len(chosen) != 1 or 'engram-continuity' not in recipe['ingredients']:
        raise KPPError('Engram recipe requires continuity and exactly one supported carrier')
    return CARRIERS[chosen[0]]

def fresh_body(output, *, persona=None, persona_name=None, identity=None):
    if persona is None:
        if persona_name is not None:
            raise KPPError('A custom persona name requires custom persona text')
        persona = PERSONA.read_text(encoding='utf-8')
        persona_name = 'Situated-Calibrating Raven'
    elif not isinstance(persona,str) or not persona.strip() or not isinstance(persona_name,str) or not persona_name.strip():
        raise KPPError('Supply nonempty custom persona text and name together')
    contract = birth.make_birth(bio_id=identity or 'e-'+uuid.uuid4().hex,
        name='Fresh Engram', description='Fresh Engram; no inherited memory or identity',
        persona_name=persona_name, persona=persona)
    return lifecycle.create(contract, output, portable=True)

def encode(body, output, encoding):
    output=Path(output)
    if encoding not in ('vcw','chroma'):
        raise KPPError('Unsupported Engram encoding')
    if output.suffix.lower() != ('.vcw' if encoding=='vcw' else '.png'):
        raise KPPError('Output extension does not match selected carrier')
    if output.exists(): raise KPPError('Output already exists')
    return cartridge.pack(body,output) if encoding=='vcw' else chromamem.export_body(body,output)

def create(recipe, output, *, persona=None, persona_name=None):
    encoding=selection(recipe)
    if Path(output).exists(): raise KPPError('Output already exists')
    with tempfile.TemporaryDirectory(prefix='kpp-fresh-engram-') as work:
        body=Path(work)/'body'
        fresh_body(body,persona=persona,persona_name=persona_name)
        result=encode(body,output,encoding)
        return {'result':'CREATED','encoding':encoding,'output':str(output),
                'identity':json.loads((body/'BIRTH.json').read_text(encoding='utf-8'))['id'],
                'verification':cartridge.verify(body),'carrier':result}
