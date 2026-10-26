"""Offline fixed-corpus measurements; no model cost or qualification is invented."""
import argparse
import hashlib
import json
import platform
from pathlib import Path
import statistics
import time
import tracemalloc
import unicodedata

from .. import bytecode, compiler, reference, vm
from ..parser import parse_program
from ..canonical import dumps

from mantleos.reflex_book.fixtures import root
ROOT = root()


def measure(fn, runs):
    samples = []
    start_cpu = time.process_time_ns()
    for _ in range(runs):
        start = time.perf_counter_ns()
        fn()
        samples.append(time.perf_counter_ns() - start)
    cpu_ns = time.process_time_ns() - start_cpu
    # Allocation instrumentation is separate from latency samples.
    tracemalloc.start()
    for _ in range(min(runs, 100)):
        fn()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {'runs': runs, 'median_ns': int(statistics.median(samples)),
            'p95_ns': sorted(samples)[min(len(samples)-1, int(len(samples)*0.95))],
            'mean_ns': sum(samples)/len(samples), 'cpu_total_ns': cpu_ns,
            'allocation_probe_runs': min(runs, 100), 'peak_traced_bytes': peak}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runs', type=int, default=1000)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not 10 <= args.runs <= 100000:
        parser.error('--runs must be 10..100000')
    if args.output.exists():
        parser.error('--output must be unused')
    fixture = ROOT / 'examples/reflex_book'
    program = parse_program((fixture/'location_rule.json').read_bytes())
    binary = bytecode.encode(compiler.compile_ir(program))
    prepared = vm.prepare(binary)
    data = (fixture/'location_stale.json').read_bytes()
    expected = reference.run(program, data)
    assert vm.run_prepared(prepared, data)['result'] == expected
    cases = {
        'prepare_only': lambda: vm.prepare(binary),
        'ast_validate_and_evaluate': lambda: reference.run(program, data),
        'ast_prevalidated_evaluate': lambda: reference._run_validated(program, data),
        'vm_prepare_and_execute': lambda: vm.run(binary, data),
        'vm_prepared_execute': lambda: vm.run_prepared(prepared, data),
        'vm_prepared_explain': lambda: vm.run_prepared(prepared, data, explain=True),
    }
    measurements = {name: measure(fn, args.runs) for name, fn in cases.items()}
    # Full admission includes real local SQLite work and is reported separately.
    # These public demonstration credentials never authorize a production host.
    import tempfile
    from .demo_m3 import NOW, END, DEMO_KEY
    from ..registry import ExperimentalRegistry
    from ..evidence import make_candidate
    from ..admission import operator_issue_receipt
    baselines = {'synthetic.benchmark': hashlib.sha256(b'fixed-benchmark-v1').hexdigest()}
    evidence = b'{"scope":"synthetic-benchmark-only"}'
    candidate = make_candidate(binary, evidence, evidence_refs=['synthetic:benchmark'],
                               baseline_versions=baselines, proposed_by='synthetic_author')
    receipt = operator_issue_receipt(candidate, issuer='synthetic_host', reviewed_by='synthetic_reviewer',
                                    secret=DEMO_KEY, not_before_utc=NOW, expires_utc=END,
                                    nonce='benchmark_only')
    with tempfile.TemporaryDirectory() as directory:
        registry = ExperimentalRegistry(Path(directory)/'benchmark.sqlite')
        context = {'trusted_issuers': {'synthetic_host': DEMO_KEY}, 'now_utc': NOW,
                   'current_baselines': baselines}
        registry.install(candidate, binary, evidence, receipt, **context)
        registry.activate(candidate['candidate_sha256'], **context)
        start = time.perf_counter_ns()
        for _ in range(min(args.runs, 100)):
            registry.run_active(data, **context)
        count = min(args.runs, 100)
        admission = {'runs': count, 'mean_ns': (time.perf_counter_ns()-start)/count,
                     'audit_events_after': registry.audit()['event_count'],
                     'scope': 'full simulated host admission and audit; history grows each run'}
    report = {'schema': 'mantle.reflex-performance/0.1-experimental',
              'python': platform.python_version(), 'platform': platform.platform(),
              'unicode_database': unicodedata.unidata_version,
              'corpus': {'program_sha256': hashlib.sha256(dumps(program)).hexdigest(),
                         'input_sha256': hashlib.sha256(data).hexdigest(),
                         'canonical_program_bytes': len(dumps(program)), 'executable_bytes': len(binary)},
              'measurements': measurements, 'simulated_admission': admission,
              'measurement_scope': {'ast': 'decision result only; prevalidated case uses a host-owned unchanged AST',
                                    'vm': 'decision plus full trace, input digest, and executed instruction indices',
                                    'warning': 'These API costs differ; do not infer VM superiority from preparation costs'},
              'model_baseline': 'NOT_MEASURED', 'break_even_runs': None,
              'break_even_formula': 'one_time_cost / (repeated_model_cost_per_run - compiled_cost_per_run)',
              'break_even_condition': 'no break-even when denominator <= 0; otherwise requires measured costs',
              'qualified': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
