"""One verified construction, compilation, snapshot and rebuild pipeline."""
from pathlib import Path
import json
import os
import shutil
import tempfile
import uuid

from . import builder, cartridge, compiled, engram, kernel
from .transactions import body_lock, ensure_clean, stage_body, publish_body, write_json


def _operational(body):
    birth = compiled.read_json(Path(body)/'BIRTH.json')
    if birth['distribution']['role'] != 'operational' or not birth['distribution']['mutable']:
        raise PermissionError('Reference Bodies must be cloned before mutation')


def _destination(output, source=None):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Output already exists')
    if source and output.is_relative_to(Path(source).resolve()):
        raise ValueError('Output must be outside the source Body')
    output.parent.mkdir(parents=True,exist_ok=True)
    return output


def install_programs(body, catalog):
    catalog = Path(catalog).resolve()
    specification = compiled.read_json(catalog)
    if specification.get('schema') != 'mantle.programs/1':
        raise ValueError('Unsupported program catalog')
    for item in specification['programs']:
        if 'source' not in item:
            continue
        source = compiled.relative_file(catalog.parent,item['source'])
        pid = compiled.json_contract.identifier(item['id'])
        suffix = '.anchor'
        target = Path(body)/'programs'/(pid+suffix)
        target.parent.mkdir(exist_ok=True)
        shutil.copy2(source,target)
        item['source'] = target.relative_to(body).as_posix()
    write_json(Path(body)/'PROGRAMS.json',specification)
    # Changed programs cannot inherit unqualified old state implicitly.
    (Path(body)/'PROGRAM-STATE.json').unlink(missing_ok=True)


def finalize(body, *, install_runtime=False, portable=False):
    body = Path(body)
    if install_runtime:
        builder._install_runtime_library(body, minimal_metadata='version' not in compiled.read_json(body/'BIRTH.json'))
    if portable:
        runtime = Path(__file__).resolve().parents[2]/'runtime'
        if not (body/'runtime/python.exe').exists() and (runtime/'python.exe').is_file():
            shutil.copytree(runtime,body/'runtime',dirs_exist_ok=True)
    if (body/'runtime/python.exe').exists():
        (body/'Run.cmd').write_text('@echo off\n"%~dp0runtime\\python.exe" -X utf8 -B "%~dp0runtime.py" %*\n',encoding='utf-8')
    cartridge.write_manifest(body)
    receipt = compiled.compile_body(body)
    from .checkpoint import render
    (body/'ENGRAM.md').write_text(render(body),encoding='utf-8')
    cartridge.write_manifest(body)
    compiled.load(body,expected_sha256=receipt['sha256'])
    return receipt


def create(birth, output, *, blueprint=None, cartridge_id=None, programs=None,
           parent=None, inherit_memory=False, portable=True, format=None, nest=None, store=None):
    if type(inherit_memory) is not bool or (inherit_memory and parent is None):
        raise ValueError('Memory inheritance requires an explicit boolean and parent')
    selected=kernel.format_name(format or ('chroma' if str(output).lower().endswith('.png') else 'cartridge'))
    cloud=str(output).startswith('gdrive://')
    if format is not None or cloud or Path(output).suffix.lower() in {'.vcw','.zip','.png'}:
        if not cloud:_destination(output,parent)
        if parent is not None and nest is not None and Path(nest).resolve().is_relative_to(Path(parent).resolve()):
            raise ValueError('NEST must be outside the parent Body')
        with tempfile.TemporaryDirectory(prefix='mantle-new-') as td:
            stage=Path(td)/'body'
            created=create(birth,stage,blueprint=blueprint,cartridge_id=cartridge_id,programs=programs,
                           parent=parent,inherit_memory=inherit_memory,portable=portable)
            saved=save(stage,output,format=selected,nest=nest,store=store)
            return {**saved,**{key:created[key] for key in ('identity','lineage','records')}}
    output = _destination(output,parent)
    stage = output.parent/('.'+output.name+'.stage-'+uuid.uuid4().hex)
    with body_lock(output):
        try:
            builder.build(birth,stage,blueprint=blueprint,cartridge_id=cartridge_id)
            if parent is not None:
                parent = Path(parent).resolve()
                with body_lock(parent):
                    ensure_clean(parent); cartridge.verify(parent)
                    parent_birth = compiled.read_json(parent/'BIRTH.json')
                    if parent_birth['id'] == compiled.read_json(stage/'BIRTH.json')['id']:
                        raise ValueError('Child requires a distinct Bio-Software identity')
                    parent_cartridge = compiled.read_json(parent/'CARTRIDGE.json')
                    child = compiled.read_json(stage/'CARTRIDGE.json')
                    child['lineage'] = {'generation':parent_cartridge['lineage']['generation']+1,
                        'parent':parent_cartridge['cartridge_id'], 'parent_identity':parent_birth['id'],
                        'parent_ledger_head':engram.head(parent/'ENGRAM.jsonl'),
                        'birth':'explicit-descendant' if inherit_memory else 'explicit-blank-descendant',
                        'memory_inheritance':'all' if inherit_memory else 'none'}
                    write_json(stage/'CARTRIDGE.json',child)
                    if inherit_memory:
                        shutil.copy2(parent/'ENGRAM.jsonl',stage/'ENGRAM.jsonl')
            if programs is not None:
                install_programs(stage,programs)
            receipt = finalize(stage,portable=portable)
            lineage=compiled.read_json(stage/'CARTRIDGE.json')['lineage']
            if output.exists():
                raise ValueError('Output already exists')
            os.rename(stage,output)
            return {**receipt,'result':'CREATED','output':str(output),'lineage':lineage}
        finally:
            if stage.exists():
                shutil.rmtree(stage)


def compile_existing(body):
    body = Path(body).resolve()
    with body_lock(body):
        ensure_clean(body); _operational(body); cartridge.verify(body)
        stage = stage_body(body)
        try:
            receipt = finalize(stage)
            return {**receipt,**publish_body(stage,body)}
        finally:
            if stage.exists() and not __import__('mantleos.transactions',fromlist=['journal_path']).journal_path(body).exists():
                shutil.rmtree(stage)


def rebuild(body, *, programs=None, birth=None, allow_identity_change=False, expected_head=None):
    body = Path(body).resolve()
    with body_lock(body):
        ensure_clean(body); _operational(body); cartridge.verify(body)
        current_head = engram.head(body/'ENGRAM.jsonl')
        if expected_head is not None and expected_head != current_head:
            raise ValueError('Stale rebuild head')
        stage = stage_body(body)
        try:
            if birth is not None:
                if not allow_identity_change:
                    raise PermissionError('Identity revision requires explicit authorization')
            # Recompile after all edits, never from a partially edited candidate.
            (stage/'COMPILED.json').unlink(missing_ok=True)
            if birth is not None:
                from .birth import validate_birth
                from .primer import create_lock
                old = compiled.read_json(stage/'BIRTH.json')
                new = validate_birth(birth)
                for key in ('id','kind','blueprint','distribution','construction','continuity'):
                    if new[key] != old[key]:
                        raise ValueError('Identity revision cannot change '+key+'; create a child instead')
                old_hash = validate_birth(old)['birth_sha256']
                revision = stage/'IDENTITY-REVISIONS'/old_hash
                revision.mkdir(parents=True,exist_ok=True)
                shutil.copy2(stage/'BIRTH.json',revision/'BIRTH.json')
                shutil.copytree(stage/'PRIMER',revision/'PRIMER',dirs_exist_ok=True)
                write_json(stage/'BIRTH.json',{k:v for k,v in new.items() if k!='birth_sha256'})
                (stage/'PRIMER/PERSONA.md').write_text(new['primer']['persona'].strip()+'\n',encoding='utf-8')
                (stage/'PRIMER/COMMANDMENTS.md').write_text(new['primer']['commandments'].strip()+'\n',encoding='utf-8')
                create_lock(stage)
                cart = compiled.read_json(stage/'CARTRIDGE.json')
                bio = compiled.read_json(stage/'BIO-SOFTWARE.json')
                cell = compiled.read_json(stage/'ANATOMY.json')
                cart['birth']['sha256'] = new['birth_sha256']
                bio['birth_contract']['sha256'] = new['birth_sha256']
                bio.update({k:new[k] for k in ('name','description')})
                for declaration in (cart, bio, cell):
                    declaration.pop('version', None)
                    if 'version' in new:
                        declaration['version'] = new['version']
                bio['persona']['name'] = new['primer']['persona_name']
                write_json(stage/'CARTRIDGE.json',cart); write_json(stage/'BIO-SOFTWARE.json',bio)
                write_json(stage/'ANATOMY.json',cell)
                engram.append(stage/'ENGRAM.jsonl','identity-revision','explicit-rebuild',
                    {'previous_birth':old_hash,'birth':new['birth_sha256'],'previous_contract':revision.relative_to(stage).as_posix()})
            if programs is not None:
                install_programs(stage,programs)
            previous = compiled.read_json(stage/'CARTRIDGE.json')
            previous['lineage']['rebuild_generation'] = previous['lineage'].get('rebuild_generation',0)+1
            previous['lineage']['previous_ledger_head'] = current_head
            write_json(stage/'CARTRIDGE.json',previous)
            engram.append(stage/'ENGRAM.jsonl','rebuild','explicit-rebuild',{'previous_head':current_head})
            receipt = finalize(stage,install_runtime=True,portable=True)
            if not (stage/'ENGRAM.jsonl').read_bytes().startswith((body/'ENGRAM.jsonl').read_bytes()):
                raise ValueError('Rebuild violated history prefix')
            return {**receipt,**publish_body(stage,body)}
        finally:
            from .transactions import journal_path
            if stage.exists() and not journal_path(body).exists():
                shutil.rmtree(stage)


def run(body, program, inputs=None, *, commit=False, request_id=None, expected_head=None):
    body = Path(body).resolve()
    with body_lock(body):
        ensure_clean(body)
        if not commit:
            return compiled.execute(body,program,inputs)
        _operational(body)
        if not isinstance(request_id,str) or not request_id or len(request_id)>128:
            raise ValueError('Committed execution requires a bounded request id')
        request_digest = compiled.digest({'program':program,'inputs':inputs or {}})
        for record in engram.read(body/'ENGRAM.jsonl'):
            if record.get('type')=='compiled-run' and record['body'].get('request_id')==request_id:
                if record['body']['request_sha256']!=request_digest:
                    raise ValueError('Request id replay conflict')
                compiled.load(body)
                return {**record['body']['receipt'],'replayed':True}
        if expected_head is not None and engram.head(body/'ENGRAM.jsonl') != expected_head:
            raise ValueError('Stale execution head')
        receipt = compiled.execute(body,program,inputs)
        stage = stage_body(body)
        try:
            if receipt['profile']=='NOTEPAD_LLM/1.3' and receipt['result']['effect_claim']=='NONE':
                states = compiled.read_json(stage/'PROGRAM-STATE.json') if (stage/'PROGRAM-STATE.json').exists() else {}
                states[program] = receipt['result']['state']; write_json(stage/'PROGRAM-STATE.json',states)
            # Keep the qualified graph; only state/history changes, so the compiler
            # can refresh indexes without parsing the original programs again.
            cartridge.write_manifest(stage)
            engram.append(stage/'ENGRAM.jsonl','compiled-run','deterministic-runtime',
                {'request_id':request_id,'request_sha256':request_digest,'receipt':receipt})
            finalize(stage)
            publication = publish_body(stage,body)
            return {**receipt,'publication':publication}
        finally:
            from .transactions import journal_path
            if stage.exists() and not journal_path(body).exists(): shutil.rmtree(stage)


def admit(body, record_type, payload, *, expected_head):
    """Explicit host admission; proposals never obtain this authority from their text."""
    body = Path(body).resolve()
    with body_lock(body):
        ensure_clean(body); _operational(body); cartridge.verify(body)
        if engram.head(body/'ENGRAM.jsonl') != expected_head:
            raise ValueError('Stale admission head')
        stage = stage_body(body)
        try:
            record = engram.append(stage/'ENGRAM.jsonl',record_type,'operator-admitted',payload,expected_head=expected_head)
            finalize(stage); result = publish_body(stage,body)
            return {**result,'record':record['id'],'ledger_head':record['sha256']}
        finally:
            from .transactions import journal_path
            if stage.exists() and not journal_path(body).exists(): shutil.rmtree(stage)


def save(body, destination, *, format='cartridge', nest=None, store=None):
    from .storage import publish
    body = Path(body).resolve()
    format=kernel.format_name(format)
    if nest is not None and Path(nest).resolve().is_relative_to(body):
        raise ValueError('NEST must be outside portable Body')
    if not str(destination).startswith('gdrive://'):
        _destination(destination,body)
    with body_lock(body), tempfile.TemporaryDirectory(prefix='mantle-snapshot-') as td:
        ensure_clean(body); cartridge.verify(body)
        stage = Path(td)/'body'; shutil.copytree(body,stage,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        receipt = finalize(stage,install_runtime=not (stage/'COMPILED.json').exists(),portable=True)
        snapshot = Path(td)/('snapshot.png' if format=='chroma' else 'snapshot.vcw')
        encoded=kernel.pack_verified_body(stage,snapshot,format=format)
        restored = Path(td)/'restored'
        kernel.verify_restored_output(snapshot,restored,format=format)
        compiled.load(restored,expected_sha256=receipt['sha256'])
        result = publish(snapshot,destination,nest=nest,store=store)
        return {**encoded,**result,'output':result['destination'],'format':format,'kernel_format':format,
                'compiled_sha256':receipt['sha256'],'ledger_head':receipt['ledger_head'],
                'snapshot_head':receipt['ledger_head'],'restored_verify':'PASS'}


def restore(source, output, *, nest=None, expected_sha256=None, store=None):
    from .storage import fetch
    output = _destination(output)
    if nest is not None and Path(nest).resolve().is_relative_to(output):
        raise ValueError('NEST must be outside restored Body')
    with body_lock(output), tempfile.TemporaryDirectory(prefix='mantle-restore-') as td:
        archive = Path(td)/'snapshot'
        receipt = fetch(source,archive,nest=nest,expected_sha256=expected_sha256,store=store)
        format = 'chroma' if archive.read_bytes()[:8]==b'\x89PNG\r\n\x1a\n' else 'cartridge'
        stage = output.parent/('.'+output.name+'.stage-'+uuid.uuid4().hex)
        try:
            kernel.verify_restored_output(archive,stage,format=format)
            if (stage/'COMPILED.json').exists(): compiled.load(stage)
            else: finalize(stage,install_runtime=True)
            os.rename(stage,output)
            return {**receipt,'result':'RESTORED','output':str(output),'format':format}
        finally:
            if stage.exists(): shutil.rmtree(stage)
