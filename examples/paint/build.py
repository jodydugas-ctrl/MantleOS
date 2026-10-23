"""Bake a complete offline Paint app and verified portable Anchor thought."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from mantleos import anchor_app_bridge, anchor_app_document, anchor_apps, anchor_language, kitchen, kernel
from mantleos.anchor_engine.tools.anchor_runtime import render_hello_world


def build(output):
    source = Path(__file__).resolve().parent
    destination = Path(output).resolve()
    if destination.is_relative_to(source):
        raise ValueError('Build outside the source specimen')
    destination.mkdir(parents=True, exist_ok=False)
    inputs = {name: (source / name).read_bytes() for name in ('index.html', 'style.css', 'raster.js', 'paint.js', 'recipe.json')}
    html = inputs['index.html'].decode('utf-8')
    html = html.replace('<link rel="stylesheet" href="style.css">', '<style>\n' + inputs['style.css'].decode('utf-8') + '\n</style>')
    for name in ('raster.js', 'paint.js'):
        text = inputs[name].decode('utf-8')
        if '</script' in text.lower():
            raise ValueError('Embedded source must not terminate its script block')
        html = html.replace(f'<script src="{name}"></script>', '<script>\n' + text + '\n</script>')
    if '<script src=' in html or '<link rel="stylesheet"' in html:
        raise ValueError('App still has external source dependencies')
    raw = html.encode('utf-8')
    (destination / 'Mantle-Paint.html').write_bytes(raw)
    recipe = json.loads(inputs['recipe.json'])
    binding = kitchen.bind(recipe)
    kitchen.inspect_binding(binding)
    (destination / 'recipe.json').write_bytes(inputs['recipe.json'])
    (destination / 'anchor-binding.json').write_text(json.dumps(binding, indent=2) + '\n', encoding='utf-8')
    # One native SCAN, with explicit coverage gaps for unqualified HTML/CSS.
    scan = kernel.scan('scan.snapshot', {'source': str(source), 'workspace': str(destination / 'scan')}, permit=True)
    if scan['stage'] != 'VERIFIED':
        raise ValueError('Native source scan failed')
    thought = anchor_apps.app_document(render_hello_world('MantlePaint', html), name='MantlePaint')
    anchor_language.inspect_blueprint(thought)
    anchor = destination / 'Mantle-Paint.anchor'
    anchor.write_bytes(thought.encode('utf-8'))
    guest = destination / 'receiver'
    guest.mkdir()
    packet = {'anchor_path': str(anchor), 'output_path': str(guest / 'paint.html'),
              'target': 'html', 'bootstrap': anchor_app_document.BOOTSTRAP}
    loader = 'import json\npacket=json.loads(input())\nexec(packet.pop("bootstrap"),packet)\n'
    subprocess.run([sys.executable, '-I', '-S', '-c', loader], input=json.dumps(packet),
                   text=True, cwd=guest, capture_output=True, check=True)
    if (guest / 'paint.html').read_bytes() != raw:
        raise ValueError('Isolated receiver changed the HTML')
    anchor_app_bridge.materialize(anchor.read_bytes(), guest / 'paint.py', 'python')
    emitted = subprocess.check_output([sys.executable, '-I', '-S', str(guest / 'paint.py')], cwd=guest)
    if emitted != raw:
        raise ValueError('Standalone Python target changed the UTF-8 payload')
    # Receiving a thought materializes it; these checks never launch an image or
    # accept a Recipe, native-parity claim, or imported instruction as authority.
    changed = anchor.read_bytes().replace(b'const MAX_PIXELS = 2000000', b'const MAX_PIXELS = 3000000', 1)
    if changed == anchor.read_bytes():
        raise ValueError('Tamper fixture did not change its specimen')
    try:
        anchor_app_bridge.load(changed)
    except ValueError:
        pass
    else:
        raise ValueError('Changed app content was accepted')
    report = {'schema': 'mantle.paint-build/1', 'result': 'PASS', 'expression': 'bio-software',
              'chase_target': 'Windows XP Paint', 'mind_required': False,
              'source_sha256': {name: hashlib.sha256(data).hexdigest() for name, data in inputs.items()},
              'html_sha256': hashlib.sha256(raw).hexdigest(), 'anchor_sha256': hashlib.sha256(anchor.read_bytes()).hexdigest(),
              'html_bytes': len(raw), 'anchor_bytes': anchor.stat().st_size,
              'isolated_receiver_html_equal': True, 'isolated_python_utf8_equal': True,
              'changed_thought_rejected': True, 'scan_graph_digest': scan['observation']['result']['report']['graph_digest'],
              'kpp_binding': 'VALID; shared immutable Neutral Anchor attributes', 'baker_acceptance': 'NOT_GRANTED',
              'native_xp_parity': 'NOT_RUN; native executable not supplied', 'network_calls': 0, 'model_calls': 0}
    (destination / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    print(json.dumps(build(parser.parse_args().output), indent=2))
