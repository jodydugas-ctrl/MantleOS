"""Opt-in native parity check, using Hermes' canonical isolated test runner.

Provision the pinned requirements into a Python 3.11-3.13 virtual environment
and set HERMES_PYTHON to its interpreter. No provider is needed.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess

TESTS = (
    'tests/agent/test_turn_context.py',
    'tests/agent/test_turn_finalizer_iteration_limit_exit.py',
    'tests/agent/test_turn_finalizer_interrupt_alternation.py',
    'tests/agent/test_turn_finalizer_final_response_persistence.py',
    'tests/agent/test_turn_finalizer_cleanup_guard.py',
    'tests/agent/test_tool_executor_checkpoint_paths.py',
    'tests/run_agent/test_authorization_gate.py',
    'tests/cli/test_single_query_session_finalize.py',
    'tests/cli/test_session_boundary_hooks.py',
    'tests/tui_gateway/test_finalize_session_persist.py',
    'tests/gateway/test_finalize_session_off_loop.py',
    'tests/hermes_cli/test_lifecycle.py',
)
COMMIT = '63279301bcbdc185c1b07b98a9312eb0c862f26d'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('pristine', type=Path); p.add_argument('integrated', type=Path)
    p.add_argument('--bash', default='bash'); p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    results = []
    for name, root in [('pristine', args.pristine), ('integrated', args.integrated)]:
        root = root.resolve()
        revision = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
        if revision != COMMIT:
            raise ValueError('Checkout differs from pinned Hermes')
        if (root / 'mantle').exists() != (name == 'integrated'):
            raise ValueError('Unexpected assimilation state')
        environment = dict(os.environ)
        environment['HERMES_TEST_WORKERS'] = '2'
        environment['HERMES_TEST_FILE_RETRIES'] = '0'
        environment['PYTHONUTF8'] = '1'
        command = [args.bash, 'scripts/run_tests.sh', *TESTS, '--file-timeout', '180']
        with (args.output / (name + '.log')).open('w', encoding='utf-8') as log:
            result = subprocess.run(command, cwd=root, env=environment, stdout=log, stderr=subprocess.STDOUT)
        results.append({'checkout': name, 'exit_code': result.returncode, 'log': name + '.log'})
        print(name, result.returncode, flush=True)
    report = {'schema': 'mantle.hermes-parity/1', 'commit': COMMIT, 'test_files': TESTS,
              'results': results, 'passed': all(r['exit_code'] == 0 for r in results),
              'scope': 'Focused native behavior; no full-host or model-provider certification'}
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
