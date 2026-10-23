"""Compare shared bytes with an explicitly checked-out KPP Git commit; never update."""
import argparse
from pathlib import Path
import re
import subprocess

from project_files import ProjectError, read_json, safe_path, sha
from kpp_upstream import check


def pin(root):
    value = read_json(Path(root)/'upstream/kpp.lock.json')
    upstream = value['upstream']
    commit = upstream.get('base_commit')
    if (upstream.get('official_url') != 'https://github.com/jodydugas-ctrl/Kitchen-Party-Protocol'
            or upstream.get('dirty') is not False
            or not isinstance(commit, str) or not re.fullmatch('[0-9a-f]{40}',commit)):
        raise ProjectError('Alignment requires a clean, reviewed KPP Git commit')
    return commit


def verify(root, source):
    root, source = Path(root).resolve(), Path(source).resolve()
    expected = pin(root)
    check(root)
    result = subprocess.run(['git','--no-optional-locks','-c','core.fsmonitor=false','-C',
                             str(source),'rev-parse','HEAD'],capture_output=True,text=True,check=True)
    if result.stdout.strip() != expected:
        raise ProjectError('KPP checkout differs from the declared commit')
    lock = read_json(root/'upstream/kpp.lock.json')
    for destination, item in lock['files'].items():
        if sha(safe_path(source,item['source']).read_bytes()) != item['sha256']:
            raise ProjectError('Pinned KPP source differs: '+destination)
    record = read_json(safe_path(source,'SHARED-SOURCE.json'))
    implementation = {name:item['sha256'] for name,item in lock['files'].items()
                      if item['group']=='implementation'}
    actual = {p.relative_to(source).as_posix() for p in (source/'src/mantleos').rglob('*')
              if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo')}
    if actual != set(implementation):
        raise ProjectError('Pinned KPP has missing or additional shared files')
    from project_files import digest
    if (record.get('files') != implementation or record.get('source_digest') != digest(implementation)
            or lock.get('shared_source_digest') != digest(implementation)):
        raise ProjectError('Pinned KPP implementation inventory differs')
    return {'result':'PASS','commit':expected,'files':len(lock['files'])}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,default=Path(__file__).resolve().parents[1])
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--commit-only',action='store_true')
    group.add_argument('--source',type=Path)
    args=parser.parse_args()
    try:
        print(pin(args.project) if args.commit_only else verify(args.project,args.source))
        return 0
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as error:
        parser.exit(2,str(error)+'\n')


if __name__=='__main__':raise SystemExit(main())
