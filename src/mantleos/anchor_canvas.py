"""Native Anchor text emission and explicit host canvas handoff."""
from pathlib import Path
import hashlib
from . import anchor_language
from .anchor_engine.tools.anchor_runtime import render_hello_world

GUIDE = """# Native ANCHOR and canvas handoff

ANCHOR-CODE.json is language metadata, not an executable program.
Executable deliverables use .anchor and contain the exact execution primer,
Anchor lines, and RUN declaration. Never label JSON, Python or bare HTML as
executable ANCHOR. For a canvas app, encode the complete HTML app as literal
output of EMIT_TEXT/0.2. ANCHOR emits the app; the host canvas/browser runs it.

An execution-capable, authorized host can call mantleos.anchor_canvas.emit with
input_path, output, name and body to create a self-contained .anchor file and
adjacent guide. The CLI exposes it as anchor-code emit --input <html> --output
<outside.anchor> --name <App> --permit-effect.
Inspect and execute its output with the native interpreter:
    MantleOS.cmd anchor-code inspect MyApp.anchor
    MantleOS.cmd anchor-code run MyApp.anchor

The run command reports a JSON result containing stdout. An authorized host may
call mantleos.anchor_canvas.write_output, or use anchor-code run --output
<outside.html> --permit-effect, with that result, output and body to
write its exact UTF-8 text. Existing files are never overwritten; outputs must
be outside the Body. Neither helper grants its caller tool or release authority.
EMIT_TEXT/0.2 concatenates literal units without adding newlines or separators.
The current profile emits text; it does not define a native ANCHOR UI engine.

Chat/canvas handoff: the .anchor file itself contains receiver launch instructions,
the exact native program and complete Canvas app. The receiving LLM is directed
to create and open the Canvas immediately, with a browser fallback if unavailable.
It needs no separate guide, translation, interpreter, installation or lookup.
The user and current host still control tool availability and permissions.
Do not show ANCHOR source as HTML, rewrite its output, execute the derived Python,
or claim the app was mounted without an actual host rendering result.
If canvas is unavailable, deliver the emitted .html for a browser instead.
Rendering HTML/JavaScript is a separate host action subject to host permissions.
"""

def outside(body, output):
    path=Path(output).resolve()
    if path.is_relative_to(Path(body).resolve()):
        raise ValueError('Output must be outside the portable Body')
    return path

def emit(input_path, output, name, *, body):
    target=outside(body,output)
    if target.suffix.lower()!='.anchor':
        raise ValueError('Executable Anchor output must use .anchor')
    guide=target.with_suffix('.RUN.md')
    if target.exists() or guide.exists():
        raise ValueError('Output or handoff guide already exists')
    text=Path(input_path).read_bytes().decode('utf-8')
    source=render_hello_world(name,text,profile='EMIT_TEXT/0.2')
    from .anchor_apps import app_document
    source=app_document(source,name=name)
    anchor_language.inspect_blueprint(source)
    with target.open('x',encoding='utf-8',newline='\n') as f:f.write(source)
    with guide.open('x',encoding='utf-8',newline='\n') as f:f.write(GUIDE)
    return {'schema':'mantle.anchor-emission/1','profile':'EMIT_TEXT/0.2',
            'output':str(target),'guide':str(guide),
            'expected_stdout_sha256':hashlib.sha256(text.encode('utf-8')).hexdigest()}

def write_output(result,output,*,body):
    if result.get('profile') not in {'EMIT_TEXT/0.2'} or not isinstance(result.get('stdout'),str):
        raise ValueError('--output requires a text-emitting ANCHOR profile')
    target=outside(body,output)
    raw=result['stdout'].encode('utf-8')
    with target.open('xb') as f:f.write(raw)
    return {**result,'output':str(target),'stdout_sha256':hashlib.sha256(raw).hexdigest(),
            'canvas_status':'HOST_HANDOFF_REQUIRED'}
