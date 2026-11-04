"""Read-only Studio startup comparison; run against a quiescent synthetic NEST.

The sequential reference reproduces the old manifest read_bytes/hash/length
loop. It is explicit benchmark instrumentation, not a production verifier mode.
No MIND requests, handlers or canonical memory appends are performed.
"""
import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time


def sequential_reference(actual):
    for relative, path in actual.items():
        raw=path.read_bytes()
        yield relative,hashlib.sha256(raw).hexdigest(),len(raw)


def sample(nest, mode, warm_samples):
    from mantleos import cartridge,studio
    original=cartridge._manifest_fingerprints
    if studio._sessions:raise ValueError('Fresh benchmark process required')
    with studio.database(nest) as db:
        if studio._setting(db,'phase')!='STASIS':raise ValueError('Benchmark requires Studio stasis')
    pin=studio.controller_pin()
    try:
        if mode=='sequential-reference':cartridge._manifest_fingerprints=sequential_reference
        started=time.perf_counter();receipt=studio.boot(nest);cold=(time.perf_counter()-started)*1000
        heads={name:session.head() for name,session in studio._sessions.items()}
        warm=[]
        for _ in range(warm_samples):
            started=time.perf_counter();studio.boot(nest);warm.append((time.perf_counter()-started)*1000)
        if pin!=studio.controller_pin():raise ValueError('Benchmark source changed')
        if heads!={name:session.head() for name,session in studio._sessions.items()}:
            raise ValueError('Canonical memory changed during benchmark')
        return {'mode':mode,'controller_pin':pin,'sessions':receipt['sessions'],'cold_ms':cold,
                'warm_samples_ms':warm,'canonical_heads_unchanged':True,
                'model_calls':0,'preparations_created':0}
    finally:
        cartridge._manifest_fingerprints=original
        for session in list(studio._sessions.values()):session.close()
        studio._sessions.clear()


def run(nest, output, runs=3, warm_samples=20):
    from mantleos import studio
    from mantleos.limbs import worker_lease
    nest=Path(nest).resolve();output=Path(output).resolve()
    if output==nest or output.is_relative_to(nest):raise ValueError('Benchmark output must stay outside the NEST')
    if not 1<=runs<=20 or not 20<=warm_samples<=1000:raise ValueError('Use 1–20 cold runs and 20–1000 warm checks')
    rows=[]
    with ExitStack() as stopped:
        stopped.enter_context(worker_lease(nest,'controller'))
        runtime=studio.limb_set(nest)
        for member in runtime.status()['members']:
            stopped.enter_context(worker_lease(runtime.root,member['id']))
        with studio.database(nest) as db:
            if studio._setting(db,'phase')!='STASIS':raise ValueError('Quiesce Studio before benchmarking')
        output.mkdir(parents=True,exist_ok=False)
        source=studio.controller_pin()
        for index in range(runs):
            modes=('sequential-reference','bounded') if index%2==0 else ('bounded','sequential-reference')
            for mode in modes:
                child=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--nest',str(nest),
                    '--child-mode',mode,'--warm-samples',str(warm_samples)],
                    capture_output=True,text=True,encoding='utf8',timeout=180)
                if child.returncode:
                    (output/'failed-child.stderr').write_text(child.stderr,encoding='utf8')
                    raise RuntimeError('Startup benchmark failed; private diagnostics retained')
                row=json.loads(child.stdout)
                if row['controller_pin']!=source:raise ValueError('Benchmark source changed between processes')
                rows.append(row)
                (output/'samples.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
                print(json.dumps({'mode':mode,'cold_ms':row['cold_ms']}),flush=True)
    medians={mode:statistics.median(r['cold_ms'] for r in rows if r['mode']==mode)
             for mode in ('sequential-reference','bounded')}
    report={'scope':'STUDIO_PROCESS_STARTUP_ONLY','rows':rows,'cold_median_ms':medians,
        'observed_reduction_percent':100*(1-medians['bounded']/medians['sequential-reference']),
        'model_calls':0,'limitations':['Sequential manifest loop is an explicit reference fixture',
            'Not OS cache-cold, ordinary-turn, provider, large-history or attachment qualification']}
    (output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--nest',type=Path,required=True)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--runs',type=int,default=3)
    parser.add_argument('--warm-samples',type=int,default=20)
    parser.add_argument('--child-mode',choices=('sequential-reference','bounded'),help=argparse.SUPPRESS)
    args=parser.parse_args(argv)
    if not 20<=args.warm_samples<=1000:parser.error('Use 20–1000 warm checks')
    if args.child_mode:
        print(json.dumps(sample(args.nest,args.child_mode,args.warm_samples)))
    else:
        if args.output is None:parser.error('--output is required')
        report=run(args.nest,args.output,args.runs,args.warm_samples)
        print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))
    return 0


if __name__=='__main__':raise SystemExit(main())
