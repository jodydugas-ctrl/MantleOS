"""Reproducible offline experimental evidence, never Baker/Body acceptance."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time
import zlib
from mantleos import cartridge,chromamem,engram
from mantleos.reflex.canonical import dumps
from mantleos.reflex.parser import parse_program
from mantleos.reflex.compiler import compile_ir
from mantleos.reflex.bytecode import encode
from mantleos.reflex.reference import run as reference
from mantleos.reflex.vm import run
from mantleos.reflex import native
import mantleos.kpp


def qualify(output, *, examples_only=False):
    output=Path(output).resolve()
    output.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).resolve().parents[2]
    fixtures=Path(mantleos.kpp.__file__).parent/'resources/examples/reflex_book'
    recipe=Path(mantleos.kpp.__file__).parent/'resources/recipes/reflex-book-qualification.json'
    program=parse_program((fixtures/'location_rule.json').read_bytes())
    payload=dumps(program);binary=encode(compile_ir(program));digest=hashlib.sha256(payload).hexdigest()
    observations=['location_normal.json','location_anomaly.json','location_unknown.json','location_stale.json']
    for name in observations:
        raw=(fixtures/name).read_bytes()
        assert run(binary,raw)['result']==reference(program,raw)
    input_bytes=(fixtures/'location_normal.json').read_bytes()
    timings=[]
    for _ in range(100):
        started=time.perf_counter();run(binary,input_bytes);timings.append(time.perf_counter()-started)
    body=output/'synthetic-body'
    native.make_body(payload,body,identity='synthetic-reflex-example')
    original={name:(body/name).read_bytes() for name in ['BIRTH.json','BIO-SOFTWARE.json','PRIMER/PERSONA.md','PRIMER/COMMANDMENTS.md']}
    artifacts={}
    for fmt,name,pack,restore in [('cartridge','reflex-candidate.vcw',cartridge.pack,cartridge.unpack),
                                 ('chroma','reflex-candidate.png',chromamem.export_body,chromamem.extract_body)]:
        path=output/name;pack(body,path);restored=output/('restored-'+fmt);restore(path,restored)
        assert all((restored/n).read_bytes()==data for n,data in original.items())
        assert engram.read(restored/'ENGRAM.jsonl')==[]
        extracted,report=native.extract(path,fmt,digest);assert extracted==payload
        artifacts[name]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size,
                         'transport':report}
    tests={'status':'NOT_RUN','reason':'examples-only; consult separately executed full-suite evidence'}
    if not examples_only:
        test_root=root/'tests/reflex_book'
        if not test_root.is_dir():test_root=root/'tests/kpp/reflex_book'
        env=dict(os.environ,PYTHONPATH=str(root/'src'),PYTHONDONTWRITEBYTECODE='1')
        command=[sys.executable,'-m','unittest','discover','-s',str(test_root),'-t',str(test_root.parent),'-v']
        completed=subprocess.run(command,cwd=root,env=env,capture_output=True,text=True,timeout=300)
        (output/'tests.txt').write_text(completed.stdout+completed.stderr,encoding='utf-8')
        tests={'status':'PASS' if completed.returncode==0 else 'FAIL','returncode':completed.returncode,'command':command}
    package=Path(native.__file__).parent
    sources={'reflex/'+p.relative_to(package).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
             for p in package.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo')}
    for name in ['lifecycle.py','cartridge.py','chromamem.py','builder.py','transactions.py','kpp/engram_carriers.py']:
        sources[name]=hashlib.sha256((package.parent/name).read_bytes()).hexdigest()
    result={'schema':'mantle.reflex-qualification-evidence/0.1-experimental',
            'scope':'Local prototype/native data transport evidence; not a qualification or acceptance decision',
            'recipe_sha256':hashlib.sha256(dumps(json.loads(recipe.read_bytes()))).hexdigest(),
            'platform':platform.platform(),'python':platform.python_version(),
            'zlib_build':zlib.ZLIB_VERSION,'zlib_runtime':zlib.ZLIB_RUNTIME_VERSION,
            'source_sha256':sources,'program_sha256':digest,'examples':artifacts,
            'reference_vm_cases':observations,'reference_vm_agreement':'PASS',
            'measurement':{'vm_runs':len(timings),'median_seconds':statistics.median(timings),
                           'min_seconds':min(timings),'max_seconds':max(timings),
                           'interpretation':'This local corpus only; no model cost or cross-platform speed claim'},
            'tests':tests,'authorized':False,'installed':False,'baker_accepted':False,
            'production_body_authorized':False,'native_format_acceptance':'REQUIRES_REVIEW',
            'runtime_limitations':['No OS sandbox or hostile-process isolation claimed',
                                   'Raw/ZIP byte canonicality remains Python/zlib edition dependent',
                                   'Only synthetic observations and prototype-supported types/operators']}
    (output/'REPORT.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    if tests['status']=='FAIL':raise RuntimeError('REFLEX tests failed; inspect tests.txt')
    return {'result':'EVIDENCE_RECORDED','output':str(output),'tests':tests,'baker_accepted':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--examples-only',action='store_true',help='Skip unit execution and label it NOT_RUN')
    args=parser.parse_args()
    print(json.dumps(qualify(args.output,examples_only=args.examples_only),indent=2))
