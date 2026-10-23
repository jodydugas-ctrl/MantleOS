"""Standalone app loader: verify and materialize targets compiled by the author.

This module is also carried verbatim by pinned EMIT_TEXT in an app document.
It imports no MantleOS implementation and never interprets app data as code.
"""
from pathlib import Path
import argparse
import hashlib
import json

MAX_BYTES = 1_048_576

def require(condition, message):
    if not condition:
        raise ValueError(message)

def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, 'Duplicate contract key')
        result[key] = value
    return result

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def load(raw):
    require(isinstance(raw, bytes) and len(raw) <= MAX_BYTES, 'Invalid app bytes')
    require(raw.startswith(b'ANCHOR APPLICATION: '), 'Not an Anchor app')
    header, marker, data = raw.partition(b'BEGIN APP CONTRACT\n')
    require(marker and b'\nBEGIN RECEIVER LAUNCH\n' in header
            and header.endswith(b'END RECEIVER LAUNCH\n\n'), 'Missing launch envelope')
    line, marker, data = data.partition(b'\nEND APP CONTRACT\n\nBEGIN BRIDGE PROGRAM\n')
    require(marker and len(line) <= 4096, 'Missing bridge contract')
    contract = json.loads(line, object_pairs_hook=pairs)
    keys = {'schema','name','profile','entrypoint','canvas','program_bytes','canvas_bytes',
            'program_sha256','canvas_sha256','authority','bridge_bytes','bridge_sha256',
            'python_bytes','python_sha256','scope','compilation'}
    require(isinstance(contract, dict) and set(contract) == keys, 'Invalid app contract')
    require(contract['schema'] == 'mantle.anchor-app-document/2'
        and contract['entrypoint'] == 'READ_AND_OPEN_APP' and contract['scope'] == 'APP_LAUNCH_ONLY'
        and contract['compilation'] == 'AUTHORING_TIME' and contract['canvas'] == 'HTML_APP_THEN_BROWSER'
        and contract['authority'] == 'HOST_PERMISSIONS_ONLY'
        and contract['profile'] in ('NOTEPAD_LLM/1.3','EMIT_TEXT/0.2'), 'Unsupported bridge contract')
    payloads = {}
    for name, ending in (
        ('bridge', b'\nEND BRIDGE PROGRAM\n\nBEGIN ANCHOR PROGRAM\n'),
        ('program', b'\nEND ANCHOR PROGRAM\n\nBEGIN CANVAS APP\n'),
        ('canvas', b'\nEND CANVAS APP\n\nBEGIN PYTHON TARGET\n'),
        ('python', b'\nEND PYTHON TARGET\nEND ANCHOR APPLICATION\n')):
        length = contract[name + '_bytes']
        require(type(length) is int and 0 < length <= MAX_BYTES, 'Invalid section size')
        payload, data = data[:length], data[length:]
        require(data.startswith(ending), 'Truncated or malformed section')
        data = data[len(ending):]
        require(digest(payload) == contract[name + '_sha256'], 'Payload digest mismatch: ' + name)
        payload.decode('utf-8')
        payloads[name] = payload
    require(not data, 'Unexpected trailing data')
    return contract, payloads

def materialize(raw, output, target='html'):
    """Check all sections before creating one new file; no target code is executed."""
    require(target in ('html','python'), 'Unsupported target; an author adapter is required')
    contract, payloads = load(raw)
    path = Path(output).resolve()
    require(path.suffix.lower() == ('.html' if target == 'html' else '.py'), 'Target extension mismatch')
    payload = payloads['canvas' if target == 'html' else 'python']
    with path.open('xb') as stream:
        stream.write(payload)
    return {'schema':'mantle.anchor-app-materialization/1','result':'MATERIALIZED',
        'target':target,'output':str(path),'bytes':len(payload),'sha256':digest(payload),
        'anchor_sha256':digest(raw),'profile':contract['profile'],
        'compilation':'AUTHORING_TIME','runtime_compilations':0,'model_calls':0,
        'scope':'DECLARED_PAYLOAD_INTEGRITY_ONLY; not native semantics or LLM qualification',
        'presentation':'HOST_OPEN_REQUIRED' if target == 'html' else 'COMMAND_ENGINE_READY',
        'effect_claim':'FILE_CREATED; no app execution or Canvas mount claim'}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('anchor', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--target', choices=('html','python'), default='html')
    args = parser.parse_args()
    print(json.dumps(materialize(args.anchor.read_bytes(), args.output, args.target)))

if __name__ == '__main__':
    main()
