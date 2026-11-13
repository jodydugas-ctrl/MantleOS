"""Build the complete readable Notepad handoff from explicitly maintained sources."""
import argparse
from pathlib import Path
from .anchor_handoff import pack, read
from .anchor_engine.tools.anchor_runtime import render_hello_world

ROOT = Path(__file__).resolve().parent


def build():
    resources = ROOT / 'kpp/resources'
    example = resources / 'examples/notepad-fidelity9'
    files = {'notepad/' + p.relative_to(example).as_posix(): p.read_bytes()
             for p in sorted(example.rglob('*'))
             if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo')}
    files['START-HERE.md'] = (resources / 'docs/ANCHOR-HANDOFF.md').read_bytes()
    receiver = (ROOT / 'anchor_handoff.py').read_bytes()
    files['receiver.py'] = receiver
    files['receiver.anchor'] = render_hello_world('HandoffReceiver', receiver.decode('utf-8'), profile='EMIT_TEXT/0.2').encode('utf-8')
    for p in sorted((ROOT / 'notices').rglob('*')):
        if p.is_file():
            files['notices/' + p.relative_to(ROOT / 'notices').as_posix()] = p.read_bytes()
    return pack(files, metadata={'purpose': 'Notepad Fidelity 9 development and portable execution',
                                'entrypoint': 'START-HERE.md', 'model_accuracy': 'UNMEASURED',
                                'baker_acceptance': 'NOT_GRANTED'})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    raw = build()
    with args.output.open('xb') as stream:
        stream.write(raw)
    manifest, files = read(args.output)
    print(f'{len(files)} verified payloads; {len(raw)} bytes; {manifest["schema"]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
