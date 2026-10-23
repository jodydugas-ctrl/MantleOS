"""Scan an app, save an executable Anchor thought, receive it without MantleOS."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys

from mantleos import anchor_app_bridge, anchor_app_document, anchor_apps, anchor_language, kernel
from mantleos.anchor_engine.tools.anchor_runtime import render_hello_world


def run(output):
    root = Path(output).resolve()
    root.mkdir(parents=True, exist_ok=False)
    source = Path(__file__).parent
    html = (source / 'counter.html').read_text('utf-8')
    # SCAN provides source evidence; it does not synthesize an app from a scan.
    scan = kernel.scan('scan.inspect', {'source': str(source), 'workspace': str(root / 'scan')}, permit=True)
    if scan['stage'] != 'VERIFIED':
        raise ValueError('SCAN did not verify its result')
    thought = anchor_apps.app_document(render_hello_world('Counter', html), name='Counter')
    (root / 'Counter.anchor').write_text(thought, encoding='utf-8', newline='\n')
    anchor_language.inspect_blueprint(thought)
    # Materialization only; receiving-host launch remains separately authorized.
    guest = root / 'receiver'; guest.mkdir()
    namespace = {'anchor_path': str(root / 'Counter.anchor'),
                 'output_path': str(guest / 'counter.html'), 'target': 'html'}
    code = 'import json\nvalues=json.loads(input())\nexec(values.pop("bootstrap"), values)\n'
    packet = {**namespace, 'bootstrap': anchor_app_document.BOOTSTRAP}
    subprocess.run([sys.executable, '-I', '-S', '-c', code], input=json.dumps(packet),
                   text=True, check=True, cwd=guest, capture_output=True)
    if (guest / 'counter.html').read_bytes() != html.encode('utf-8'):
        raise ValueError('Received app differs from authored payload')
    anchor_app_bridge.materialize(thought.encode(), guest / 'counter.py', 'python')
    received = subprocess.check_output([sys.executable, '-I', '-S', str(guest / 'counter.py')], cwd=guest)
    if received != html.encode('utf-8'):
        raise ValueError('Standalone target differs from authored payload')
    # A second actual executable profile, with deterministic editing on the receiver.
    notepad = anchor_apps.notepad_source()
    (root / 'Notepad.anchor').write_text(notepad, encoding='utf-8', newline='\n')
    anchor_app_bridge.materialize(notepad.encode(), guest / 'notepad.py', 'python')
    commands = [{'op': 'INSERT', 'text': 'A portable thought.'}, {'op': 'UNDO'}]
    result = subprocess.run([sys.executable, '-I', '-S', str(guest / 'notepad.py')],
                            input=''.join(json.dumps(c) + '\n' for c in commands), text=True,
                            cwd=guest, check=True, capture_output=True)
    checkpoints = [json.loads(line) for line in result.stdout.splitlines()]
    if [r['state']['text'] for r in checkpoints] != ['A portable thought.', '']:
        raise ValueError('Standalone Notepad edit/undo failed')
    report = {'result': 'PASS', 'scan': scan['stage'], 'created_app': 'Counter.anchor',
              'app_sha256': hashlib.sha256(thought.encode()).hexdigest(),
              'receiver_requires_mantleos': False, 'receiver_python_html_equal': True,
              'notepad_edit_undo': 'PASS', 'model_calls': 0,
              'cross_llm_execution': 'HOST_DEPENDENT; not tested against a model provider',
              'browser_ui': 'Generated; interactive behavior checked separately'}
    (root / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    print(json.dumps(run(parser.parse_args().output), indent=2))
