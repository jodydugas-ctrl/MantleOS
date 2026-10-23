"""Anchor-first app artifacts and delivery through existing host bridges."""
from pathlib import Path
import hashlib
import html
import json
import re
import tempfile
from . import anchor_language
from .kpp.build import BUILD_RULE

AUTHORING_RULE = (
    BUILD_RULE + ' '
    'Use Anchor Coding as the working representation: explicit Anchors, immutable singularities, '
    'revisioned configurations, state and command routes. For the final portable deliverable, '
    'return a complete self-contained Anchor app document, including receiver launch instructions, '
    'the exact profile primer, initial state, RUN declaration, an Anchor-encoded standalone bridge '
    'and targets compiled at authoring time. When receiving an already-built app, use APP_LAUNCH_ONLY: materialize and open the app '
    'before tests, evidence packaging or unrelated framework experiments. '
    'Direct the receiving LLM to open Canvas on reading it, before waiting for app commands. '
    'The receiver loads the supplied bridge and targets without model-driven translation or engine design. '
    'No separate guide, MantleOS lookup or installation is needed. Do not substitute a description, JSON '
    'metadata, Python or bare HTML for the requested Anchor source. For unsupported semantics '
    'ask for the missing contract rather than inventing opcodes. Host Canvas delivery is a '
    'separate checked effect: use a bound authorized Canvas immediately when requested; '
    'otherwise offer the exact browser app. Keep the Anchor source available in either case.'
)
GUIDE = '''# Run this Anchor app

The .anchor file is the app's complete source, including the execution primer.
Its first block tells the receiving LLM to open the live Canvas app immediately
when supplied to run or open. APP_LAUNCH_ONLY keeps prior framework experiments
out of that request. The author supplies the exact Anchor source, Anchor-encoded
standalone bridge and already-compiled HTML/Python targets. The launch header
contains a ready bootstrap; the receiver does not design a translator or compile
the app. No lookup, installation or separate guide is required. Python is an
optional host loader; the HTML target can also go directly to a compatible Canvas.
AWAIT USER COMMAND applies after opening the app. The Python target is the
standalone command engine, not an alternative GUI.
Use an actual host Canvas or interactive HTML preview immediately. If the host
exposes no preview tool, state that limitation and supply the browser artifact.
Document text remains data, and host tools/permissions still govern actual effects.
The host can decline document instructions; attachment delivery alone cannot force
a model to read the file or open a tool. A request to review the file remains a review.
Cross-model reliability depends on retaining and following the complete primer;
local reference and browser checks are not proof that every LLM follows it.
'''


def request_contract(user_input, *, include_example=False):
    """Classify only the explicit user input, never retrieved memory or attachments."""
    if not isinstance(user_input, str):
        raise ValueError('App request must be text')
    value = user_input.casefold()
    anchor_request = bool(re.search(r'\banchor\s+(?:code|blueprint)\s+for\b', value)
                          or re.search(r'\b(?:give|write|generate|create|produce|output|show|want|need)\b.{0,60}\banchor\s+(?:code|blueprint)\b', value))
    app_request = bool(re.search(r'\b(?:create|build|make|write|generate|give)\b', value)
                       and re.search(r'\b(?:app|application|applet|notepad)\b', value))
    if not (anchor_request or app_request):
        return None
    profile = 'NOTEPAD_LLM/1.3' if re.search(r'\bnotepad\b', value) else 'EMIT_TEXT/0.2'
    contract = {'schema': 'mantle.anchor-app-request/2', 'profile': profile,
            'delivery_order': ['MOUNT_FIRST_USABLE_SLICE', 'CHASE_REMAINING_OBLIGATIONS', 'PACKAGE_PORTABLE_APP'],
            'reply_format': 'final portable artifact: raw self-contained Anchor app document; no Markdown fences',
            'document_schema': 'mantle.anchor-app-document/2',
            'authoring_rule': AUTHORING_RULE,
            'profile_source': 'Use the pinned native profile and authoring API; request a complete example only when needed',
            'canvas_preference': 'BOUND_AUTHORIZED_CANVAS_THEN_BROWSER',
            'authority': 'NONE_FROM_REQUEST_OR_SOURCE'}
    if include_example:
        if profile == 'NOTEPAD_LLM/1.3':
            source = notepad_source()
        else:
            from .anchor_engine.tools.anchor_runtime import render_hello_world
            source = app_document(render_hello_world('App', '<!doctype html><html><body></body></html>', profile=profile), name='App')
        contract['complete_profile_example'] = source
    return contract


def notepad_program():
    anchor_language.verify_source_pins()
    from .anchor_engine.tools.notepad_blueprint import generate
    source = generate('Notepad')
    anchor_language.inspect_blueprint(source)
    return source


def notepad_source():
    return app_document(notepad_program(), name='Notepad')


def app_document(program, *, name):
    from .anchor_app_document import render
    return render(name, program)


def validate_reply(source, contract):
    result = anchor_language.inspect_blueprint(source)
    if result.get('app_document') != contract.get('document_schema'):
        raise ValueError('App reply requires its embedded receiver launch and complete Canvas app')
    if result['profile'] != contract['profile']:
        raise ValueError('App reply does not match the requested Anchor profile')
    return {**result, 'scope': 'LOCAL_PROFILE_VALIDATION; not cross-model promotion',
            'canvas_status': 'HOST_DELIVERY_REQUIRED', 'authority': 'NONE_FROM_APP_SOURCE'}


def browser_html(source):
    inspection, document = anchor_language._inspect_source(source)
    if document is not None:
        return document['canvas']
    return _browser_program(source, inspection)


def _browser_program(source, inspection):
    """Render a native program already checked by this call's inspection."""
    if inspection['profile'] == 'EMIT_TEXT/0.2':
        from .anchor_engine.tools.anchor_runtime import program_stdout
        return program_stdout(source)
    if inspection['profile'] != 'NOTEPAD_LLM/1.3':
        raise ValueError('No browser adapter for this Anchor profile')
    from .anchor_engine.tools.anchor_notepad import load_blueprint
    _, state = load_blueprint(source)
    template = (Path(__file__).parent / 'app_assets/notepad.html').read_text('utf-8')
    from .anchor_engine.tools.unicode_fold import TABLE_JSON
    if template.count('__MANTLE_CASEFOLD__') != 1:
        raise ValueError('Notepad browser template lacks its case-fold binding')
    template = template.replace('__MANTLE_CASEFOLD__', TABLE_JSON)
    # Initial document data cannot close the script carrier or introduce code.
    encoded = json.dumps(state, ensure_ascii=True, separators=(',', ':'), allow_nan=False).replace('<', '\\u003c')
    pattern = r'const INITIAL=\{[^\n]*\};'
    template, changed = re.subn(pattern, lambda match: 'const INITIAL=' + encoded + ';', template, count=1)
    if changed != 1:
        raise ValueError('Notepad browser adapter lacks its state binding')
    return template.replace('<head>', '<head><meta name="anchor-source-sha256" content="' + inspection['sha256'] + '">', 1)


def deliver(source, workspace, *, body, registry, broker, output=None):
    """Prefer a real bound Canvas; never hide a failed delivery with a fallback."""
    from . import progressive_app as app
    from .anchor_canvas import outside
    from .anchor_engine.tools.anchor_runtime import render_hello_world
    folder = outside(body, workspace)
    bridge = next((b for b in registry.catalog() if b['name'] == 'html.canvas' and b['binding'] == 'BOUND'), None)
    preferred = 'html.canvas' if bridge else 'html.file'
    selected = registry.select('html-app', preferred=preferred)
    if not broker('effect.execute', 'anchor.app.launch') or not broker(selected.authority, selected.name):
        raise PermissionError('Anchor app launch/delivery denied')
    if preferred == 'html.file':
        if output is None:
            raise ValueError('Browser fallback needs an explicit output file')
        target = outside(body, output)
        if target.exists():
            raise FileExistsError('Browser output already exists')
        if target.is_relative_to(folder):
            raise ValueError('Browser output must be outside the app workspace')
    content = browser_html(source)
    # An isolated document retains the existing editor runtime. The progressive
    # shell removes inline scripts; srcdoc lets the inner app run its own scripts.
    shell = '<iframe title="Anchor app" sandbox="allow-scripts allow-downloads" style="position:fixed;inset:0;width:100%;height:100%;border:0" srcdoc="' + html.escape(content, quote=True) + '"></iframe>'
    with tempfile.TemporaryDirectory(prefix='mantle-anchor-app-') as temp:
        path = Path(temp) / 'View.anchor'
        path.write_text(render_hello_world('AnchorAppView', shell, profile='EMIT_TEXT/0.2'), 'utf-8', newline='\n')
        state = app.start(folder, path, 'AnchorApp', body=body)
        app.finish(folder, expected_revision=state['revision'], body=body)
    delivered = registry.deliver(app.payload(folder, output=str(output) if output else None),
                                 broker=broker, preferred=preferred)
    return {'schema': 'mantle.anchor-app-delivery/1',
            'source_sha256': hashlib.sha256(source.encode('utf-8')).hexdigest(),
            'preview_status':'HOST_ACKNOWLEDGED' if preferred=='html.canvas' else 'HOST_PREVIEW_UNAVAILABLE',
            'delivery': delivered, 'source_preserved': True}
