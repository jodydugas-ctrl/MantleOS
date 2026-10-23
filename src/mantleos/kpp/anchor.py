"""KPP ports to the one MantleOS Anchor interpreter and source definitions."""
import hashlib
import json
from pathlib import Path

from ..anchor_engine.tools.anchor_runtime import PRIMER_PATHS, program_stdout
from ..anchor_language import inspect_blueprint, execute_blueprint
from .core import KPPError

PROFILE = 'EMIT_TEXT/0.2'
MAX_SOURCE = MAX_OUTPUT = 1_048_576
PRIMER = PRIMER_PATHS[PROFILE].read_text(encoding='utf-8').rstrip('\n')


def interpret(source):
    """Exact shared literal profile; no separate KPP grammar or opcodes."""
    try:
        return program_stdout(source)
    except (ValueError, TypeError, UnicodeError) as error:
        raise KPPError(str(error)) from error


def _source(path):
    with Path(path).open('rb') as stream:
        blob = stream.read(MAX_SOURCE + 1)
    if len(blob) > MAX_SOURCE:
        raise KPPError('Anchor source oversized')
    try:
        return blob, blob.decode('utf-8')
    except UnicodeError as error:
        raise KPPError('Anchor source must be UTF-8') from error


def _inspect(blob, source):
    try:
        report = inspect_blueprint(source)
    except (ValueError, TypeError, UnicodeError) as error:
        raise KPPError(str(error)) from error
    result = {'profile': report['profile'], 'source_sha256': hashlib.sha256(blob).hexdigest(),
              'source_bytes': len(blob), 'native': report, 'effect': 'TEXT_ONLY; nothing executed'}
    if report['profile'] == PROFILE and not report.get('app_document'):
        emitted = interpret(source).encode('utf-8')
        result.update(emitted_sha256=hashlib.sha256(emitted).hexdigest(), emitted_bytes=len(emitted))
    return result


def inspect_file(path):
    return _inspect(*_source(path))


def run_file(path, command=None):
    _, source = _source(path)
    try:
        result = execute_blueprint(source, command)
        return result['stdout'] if 'stdout' in result else json.dumps(result, ensure_ascii=False)
    except (ValueError, TypeError, UnicodeError) as error:
        raise KPPError(str(error)) from error


def bridge_python(source_path, destination):
    """Materialize emitted Python data once; preserve the existing KPP port."""
    target = Path(destination)
    if target.suffix != '.py' or target.exists():
        raise KPPError('Python bridge needs a new .py target')
    blob, source = _source(source_path)
    report = _inspect(blob, source)
    if report['profile'] != PROFILE or report['native'].get('app_document'):
        raise KPPError('Literal Python bridge requires EMIT_TEXT/0.2; use native app receiving for app documents')
    text = interpret(source)
    try:
        compile(text, str(target), 'exec')
    except SyntaxError as error:
        raise KPPError('Emitted Python fails syntax validation: ' + str(error)) from error
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(text)
    return {**report, 'output': str(target), 'bridge': 'python',
            'effect': 'PYTHON_FILE_WRITTEN; no execution or host permission granted'}
