"""Standard-library release observations; checks never confer Baker acceptance."""
import argparse
import datetime
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'kpp.release-validation/1'


def marker(name, explanation):
    return {'status':'NOT_RUN','name':name,'reason':explanation}


def command_check(name, args, timeout=150, interpreter=None):
    """No shell; a subprocess result is evidence of its invocation, not a signature."""
    start=time.monotonic()
    try:
        env=dict(os.environ)
        env['PYTHONPATH']=str(next(parent/'src' for parent in Path(__file__).resolve().parents if (parent/'src/mantleos').is_dir()))
        result=subprocess.run(args,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                              text=True,errors='replace',timeout=timeout,check=False)
        stdout=result.stdout[-3000:]
        stderr=result.stderr[-3000:]
        state='PASS' if result.returncode == 0 else 'FAIL'
        if state=='FAIL' and '"result": "BLOCKED"' in stdout:
            state='BLOCKED'
        if state=='FAIL' and '"result": "BLOCKED"' in stderr:
            state='BLOCKED'
        check={'status':state,'name':name,'exit_code':result.returncode,
               'duration_seconds':round(time.monotonic()-start,3),'stdout_tail':stdout,
               'stderr_tail':stderr, 'invocation':list(args)}
        found=re.search(r'Ran (\d+) tests? in',stdout+'\n'+stderr)
        if found:
            check['tests_run']=int(found.group(1))
            skipped=re.search(r'OK \(skipped=(\d+)\)',stdout+'\n'+stderr)
            check['tests_skipped']=int(skipped.group(1)) if skipped else 0
        return check
    except (OSError,subprocess.TimeoutExpired) as error:
        return {'status':'BLOCKED' if isinstance(error, OSError) else 'FAIL',
                'name':name,'reason':str(error)[:400],
                'duration_seconds':round(time.monotonic()-start,3),
                'invocation':list(args)}


def assess(checks):
    required=('unittests','doctor','task_agent_smoke','release_inventory')
    local='PASS' if all(checks.get(name,{}).get('status')=='PASS' for name in required) else 'OPEN'
    return {'local_functional_checks':local,
            'browser_notepad':checks.get('browser_preview',{}).get('status','NOT_RUN'),
            'browser_calculator':checks.get('progressive_calculator_browser',{}).get('status','NOT_RUN'),
            'browser_recovery':checks.get('preview_recovery_browser',{}).get('status','NOT_RUN'),
            'browser_gui_matrix':checks.get('gui_observations_browser',{}).get('status','NOT_RUN'),
            'baker_acceptance':'NOT_GRANTED',
            'scope':'Measured local checks only; no automatic acceptance or isolation claim'}


def validate(args):
    if args.json_out and (ROOT.resolve()==args.json_out.resolve() or ROOT.resolve() in args.json_out.resolve().parents):
        raise ValueError('Write release-validation output OUTSIDE the release root to retain an exact inventory')
    interpreter=args.python
    checks={
        'unittests':command_check('unittests',[interpreter,'-m','unittest','discover','-s','tests','-q'],timeout=180),
        'doctor':command_check('doctor',[interpreter,'-m','mantleos','kpp','doctor'],timeout=30),
        'task_agent_smoke':command_check('task_agent_smoke',[interpreter,'examples/adaptive-reflex/smoke.py'],timeout=30),
        'release_inventory':command_check('release_inventory',[interpreter,'tools/verify_release.py'],timeout=30)
    }
    node=shutil.which('node')
    if node:
        results=[command_check('node-'+path.name,[node,'--check',str(path)],timeout=20)
                 for path in (sorted((next(parent/'src' for parent in Path(__file__).resolve().parents if (parent/'src/mantleos').is_dir())/'mantleos/kpp/assets').glob('*.js')) + sorted((ROOT/'previews').rglob('*.js')))]
        checks['javascript_syntax']={'name':'javascript_syntax',
                                    'status':'PASS' if all(x['status']=='PASS' for x in results) else 'FAIL',
                                    'scripts_checked':len(results),'results':results}
    else:
        checks['javascript_syntax']=marker('javascript_syntax','Node.js not installed; optional JS syntax check unexecuted')
    if args.browser:
        call=[interpreter,'tools/check_browser_preview.py']
        if args.chromium: call.extend(['--chromium',args.chromium])
        checks['browser_preview']=command_check('browser_preview',call,timeout=75)
        call=[interpreter,'tools/check_progressive_calculator.py']
        if args.chromium:call.extend(['--chromium',args.chromium])
        checks['progressive_calculator_browser']=command_check('progressive_calculator_browser',call,timeout=75)
        for name,script in [('preview_recovery_browser','check_preview_recovery.py'),('gui_observations_browser','check_gui_observations.py')]:
            call=[interpreter,'tools/'+script]
            if args.chromium:call.extend(['--chromium',args.chromium])
            checks[name]=command_check(name,call,timeout=100)
    else:
        checks['browser_preview']=marker('browser_preview','Not requested; real browser test needs Playwright and Chromium')
        checks['progressive_calculator_browser']=marker('progressive_calculator_browser','Not requested; real browser test needs Playwright and Chromium')
        for name in ('preview_recovery_browser','gui_observations_browser'):
            checks[name]=marker(name,'Not requested; real browser test needs Playwright and Chromium')
    required=['unittests','doctor','task_agent_smoke','release_inventory']
    requested=['browser_preview','progressive_calculator_browser','preview_recovery_browser','gui_observations_browser'] if args.browser else []
    if node: requested.append('javascript_syntax')
    failures=[x for x in required+requested if checks[x]['status']!='PASS']
    report={'schema':SCHEMA,
            'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
            'runtime':{'python':sys.version.split()[0],'target_python':interpreter,
                       'platform':platform.platform(),'architecture':platform.machine()},
            'observations':checks,'gates':assess(checks),
            'requested_check_failures':failures,
            'run_result':'PASS' if not failures else 'INCOMPLETE',
            'disclaimer':'Local, unsigned observations only. No deployment or Baker approval.'}
    return report


def main(argv=None):
    p=argparse.ArgumentParser(description='Run and record KPP release checks without granting Baker acceptance')
    p.add_argument('--python',default=sys.executable,help='Interpreter for tests (does not prove additional Python versions)')
    p.add_argument('--browser',action='store_true',help='Opt into REAL Chromium browser E2E; requires Playwright')
    p.add_argument('--chromium',help='Locally installed Chromium executable for --browser')
    p.add_argument('--json-out',type=Path,help='Machine-readable record OUTSIDE the repository')
    args=p.parse_args(argv)
    try:
        report=validate(args)
    except ValueError as error:
        p.error(str(error))
    output=json.dumps(report,indent=2,sort_keys=True)+'\n'
    if args.json_out:
        args.json_out.parent.mkdir(parents=True,exist_ok=True)
        args.json_out.write_text(output,encoding='utf-8')
    print(output)
    return 0 if report['run_result']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
