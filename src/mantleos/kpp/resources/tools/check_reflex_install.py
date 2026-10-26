"""Install one wheel offline in a fresh environment and exercise REFLEX outside source.

This developer check runs only the bundled synthetic reference example. It never
installs a candidate, issues approval or dispatches a candidate's effects.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import venv
import zipfile


def checkout_roots():
    # Both the root generated tool and its packaged canonical copy are supported.
    return [p for p in Path(__file__).resolve().parents
            if (p / 'pyproject.toml').is_file() and (p / 'src/mantleos').is_dir()]


def check(wheel, output, *, pip_wheel=None, pip_sha256=None):
    wheel, output = Path(wheel).resolve(), Path(output).resolve()
    if not wheel.is_file() or wheel.suffix != '.whl':
        raise ValueError('Supply an existing wheel file')
    if (pip_wheel is None) != (pip_sha256 is None):
        raise ValueError('Offline pip bootstrap requires both --pip-wheel and --pip-sha256')
    if pip_wheel is not None:
        pip_wheel = Path(pip_wheel).resolve()
        if hashlib.sha256(pip_wheel.read_bytes()).hexdigest() != pip_sha256:
            raise ValueError('Offline pip wheel digest mismatch')
    if any(output.is_relative_to(root) for root in checkout_roots()):
        raise ValueError('Output must be OUTSIDE the source checkout')
    output.mkdir(parents=True, exist_ok=False)
    environment = output / 'venv'
    work = output / 'work'
    work.mkdir()
    clean_env = {k: v for k, v in os.environ.items()
                 if k.upper() not in {'PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV'}}
    clean_env.update(PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1', PIP_NO_INDEX='1',
                     PIP_DISABLE_PIP_VERSION_CHECK='1')
    report = {'schema': 'mantle.reflex-installed-check/1', 'result': 'FAIL',
              'wheel': wheel.name, 'wheel_sha256': hashlib.sha256(wheel.read_bytes()).hexdigest(),
              'host': {'system': platform.system(), 'python': platform.python_version()},
              'checks': [], 'authority': 'Synthetic reproducibility only; no approval granted'}

    def command(name, args, *, as_json=True):
        completed = subprocess.run(args, cwd=work, env=clean_env, capture_output=True,
                                   encoding='utf-8', errors='strict', timeout=180)
        (output / (name + '.stdout')).write_text(completed.stdout, encoding='utf-8')
        (output / (name + '.stderr')).write_text(completed.stderr, encoding='utf-8')
        report['checks'].append({'name': name, 'exit_code': completed.returncode})
        completed.check_returncode()
        return json.loads(completed.stdout) if as_json else completed.stdout

    def require(condition, message):
        if not condition:
            raise ValueError(message)

    try:
        venv.EnvBuilder(with_pip=pip_wheel is None, system_site_packages=False).create(environment)
        python = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        if pip_wheel is not None:
            # Some minimal distributions omit ensurepip. Seed only a separately
            # supplied, digest-pinned pip wheel into this disposable environment.
            purelib = command('bootstrap-location', [str(python), '-I', '-c',
                'import json,sysconfig;print(json.dumps(sysconfig.get_path("purelib")))'])
            destination = Path(purelib).resolve()
            require(destination.is_relative_to(environment.resolve()), 'Unsafe bootstrap destination')
            with zipfile.ZipFile(pip_wheel) as archive:
                for item in archive.infolist():
                    name = item.filename
                    require(not name.startswith('/') and '\\' not in name and ':' not in name
                            and all(p not in ('.', '..') for p in name.rstrip('/').split('/'))
                            and (name.startswith('pip/') or name.split('/')[0].startswith('pip-')
                                 and name.split('/')[0].endswith('.dist-info'))
                            and (item.external_attr >> 16) & 0o170000 != 0o120000,
                            'Unsafe pip bootstrap wheel member')
                archive.extractall(destination)
            report['pip_bootstrap_sha256'] = pip_sha256
        command('install', [str(python), '-I', '-m', 'pip', 'install', '--no-index',
                            '--no-deps', '--no-cache-dir', str(wheel)], as_json=False)
        probe = '''import json, sys
from pathlib import Path
from importlib.resources import files
import mantleos
from mantleos.reflex_book import evaluation
base = files('mantleos.reflex_book')
assert base.joinpath('SPEC.md').read_bytes()
assert base.joinpath('resources/examples/location_rule.json').read_bytes()
module = Path(mantleos.__file__).resolve()
assert module.is_relative_to(Path(sys.prefix).resolve()), str(module)
print(json.dumps({'module': str(module), 'prefix': sys.prefix, 'identity': evaluation.source_identity()}))
'''
        report['installed'] = command('installed-resources', [str(python), '-I', '-c', probe])
        cli = [str(python), '-I', '-m', 'mantleos', 'reflex-book']
        command('help', [str(python), '-I', '-m', 'mantleos', '--help'], as_json=False)
        command('demo', cli + ['demo', '--output', 'demo'])
        records = [work / 'demo' / (name + '.json') for name in ('fresh', 'stale')]
        projections = []
        for name, record in zip(('fresh', 'stale'), records):
            projection = command('inspect-' + name, cli + ['inspect', str(record), '--format', 'json'])
            text = command('inspect-text-' + name,
                           cli + ['inspect', str(record), '--format', 'text'], as_json=False)
            require(json.loads(text) == projection, 'Inspection text/JSON projections differ')
            require(projection['execution'] == 'NOT_PERFORMED', 'Inspection performed execution')
            projections.append(projection)
            reproduced = command('reproduce-' + name, cli + ['reproduce', str(record)])
            require(reproduced['status'] == 'REPRODUCED', 'Record did not reproduce')
        comparison_args = cli + ['compare', *(str(p) for p in records)]
        comparison = command('compare', comparison_args + ['--format', 'json'])
        text = command('compare-text', comparison_args + ['--format', 'text'], as_json=False)
        require(json.loads(text) == comparison, 'Comparison text/JSON projections differ')
        require(comparison['same_program'] and comparison['same_observation_values']
                and not comparison['same_input'] and comparison['freshness_changed'],
                'Expected freshness-only change is missing')
        for projection, status, age in zip(projections, ('NORMAL', 'UNKNOWN'), (30, 630)):
            require(projection['recorded_claims']['trace']['result']['status'] == status,
                    'Unexpected synthetic decision')
            require(projection['checked']['observations'][0]['age_seconds'] == age,
                    'Unexpected observation age')
            require(projection['checked']['guards'][0]['max_age_seconds'] == 180,
                    'Unexpected freshness threshold')
        command('evaluate', cli + ['evaluate', 'demo/program.rfx', '--input', 'demo/input.json',
                                   '--output', 'evaluated.json'])
        require(command('reproduce-evaluated', cli + ['reproduce', 'evaluated.json'])['status']
                == 'REPRODUCED', 'Explicit evaluation did not reproduce')
        if wheel.name.startswith('kitchen_party_protocol-'):
            command('kpp-doctor', [str(python), '-I', '-m', 'kpp', 'doctor'])
            command('kpp-reflex-help', [str(python), '-I', '-m', 'kpp', 'reflex-book', '--help'],
                    as_json=False)
        report['result'] = 'PASS'
    except Exception as error:
        report['error'] = str(error)
        raise
    finally:
        (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pip-wheel', type=Path,
                        help='Optional reviewed offline pip wheel for hosts without ensurepip')
    parser.add_argument('--pip-sha256', help='Independently supplied SHA-256 of that pip wheel')
    args = parser.parse_args()
    try:
        print(json.dumps(check(args.wheel, args.output, pip_wheel=args.pip_wheel,
                              pip_sha256=args.pip_sha256), indent=2))
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
