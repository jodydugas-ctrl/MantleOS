"""Matched fresh-process Canvas preparation timings; host rendering is separate.

Run with --baseline-src <saved src> --candidate-src src --output <new.json>.
No model, remote service, persistent cache, or fabricated rendering receipt.
"""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time


def sha(data):
    return hashlib.sha256(data).hexdigest()


def worker(source):
    sys.path.insert(0, str(Path(source).resolve()))
    from mantleos import anchor_apps, anchor_app_bridge, anchor_language
    from mantleos.app_bridges import default_registry
    from mantleos.anchor_engine.tools.anchor_runtime import render_hello_world
    results = {}
    for name, build in (
        ('notepad', anchor_apps.notepad_source),
        ('large-html', lambda: anchor_apps.app_document(render_hello_world('Large',
            '<!doctype html><title>Synthetic</title><button id="ready">Ready</button>' +
            '<!-- synthetic app content -->' * 6000, profile='EMIT_TEXT/0.2'), name='Large'))):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            times = {}
            def measure(stage, action):
                before = time.perf_counter()
                value = action()
                times[stage] = time.perf_counter() - before
                return value
            app = measure('author', build)
            if name == 'notepad':
                request = measure('request_context', lambda: anchor_apps.request_contract('Build a Notepad app'))
            html = measure('browser_prepare', lambda: anchor_apps.browser_html(app))
            run = measure('native_launch', lambda: anchor_language.execute_blueprint(app))
            assert run['stdout'] == html and run['effect_claim'] == 'NONE'
            measure('portable_materialize', lambda: anchor_app_bridge.materialize(
                app.encode('utf-8'), folder / 'received.html'))
            assert (folder / 'received.html').read_bytes() == html.encode('utf-8')
            measure('file_delivery', lambda: anchor_apps.deliver(app, folder / 'workspace',
                body=folder / 'body', registry=default_registry(folder / 'body'),
                broker=lambda *_: True, output=folder / 'preview.html'))
            results[name] = {'seconds': times, 'app_sha256': sha(app.encode()),
                'html_sha256': sha(html.encode()), 'delivery_sha256': sha((folder / 'preview.html').read_bytes())}
            if name == 'notepad':
                results[name]['request_context_bytes'] = len(json.dumps(request).encode('utf-8'))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker')
    parser.add_argument('--baseline-src', type=Path)
    parser.add_argument('--candidate-src', type=Path, default=Path('src'))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--pairs', type=int, default=7)
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(worker(args.worker)))
        return
    if not args.baseline_src or not args.output or args.pairs < 3:
        parser.error('Provide baseline-src, a new output path and at least three pairs')
    sources = {'baseline': args.baseline_src.resolve(), 'candidate': args.candidate_src.resolve()}
    records = []
    for pair in range(-1, args.pairs):  # one discarded warmup pair
        record = {}
        order = ('baseline', 'candidate') if pair % 2 else ('candidate', 'baseline')
        for kind in order:
            before = time.perf_counter()
            run = subprocess.run([sys.executable, '-I', '-S', str(Path(__file__).resolve()),
                                  '--worker', str(sources[kind])], check=True, capture_output=True, text=True)
            record[kind] = {'process_seconds': time.perf_counter() - before,
                            'apps': json.loads(run.stdout)}
        if pair >= 0:
            records.append(record)
    for record in records:
        for app in record['baseline']['apps']:
            for field in ('app_sha256', 'html_sha256', 'delivery_sha256'):
                assert record['baseline']['apps'][app][field] == record['candidate']['apps'][app][field], (app, field)
    summary = {}
    for app in records[0]['baseline']['apps']:
        summary[app] = {}
        for stage in records[0]['baseline']['apps'][app]['seconds']:
            medians = {kind: statistics.median(row[kind]['apps'][app]['seconds'][stage] for row in records)
                       for kind in sources}
            summary[app][stage] = {**medians, 'reduction_percent': 100 * (1 - medians['candidate'] / medians['baseline'])}
    value = {'schema': 'mantle.canvas-preparation-benchmark/1', 'python': sys.version,
        'scope': 'Fresh local Python processes; preparation and file delivery, not host Canvas/model latency',
        'pairs': records, 'summary': summary, 'exact_output_parity': True,
        'request_context_bytes': {kind: records[0][kind]['apps']['notepad']['request_context_bytes'] for kind in sources},
        'source_files': {kind: {str(path.relative_to(source)): sha(path.read_bytes())
            for path in sorted((source / 'mantleos').rglob('*'))
            if path.is_file() and '__pycache__' not in path.parts and path.suffix not in ('.pyc', '.pyo')}
            for kind, source in sources.items()},
        'harness_sha256': sha(Path(__file__).read_bytes())}
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
