"""One staged, recoverable synchronizer for source, handbook and Engram exports."""
from pathlib import Path
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from . import checkpoint, cartridge

LOCK='SYNC.json'
TRANSACTION='.mantle-transaction'
BLOCK=re.compile(r'<!-- mantle:code ([a-z0-9_-]+) -->\r?\n```python\r?\n(.*?)\r?\n```\r?\n<!-- /mantle:code -->',re.S)


def sha(data): return hashlib.sha256(data).hexdigest()
def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def safe(root,rel):
    if not isinstance(rel,str) or '\\' in rel or ':' in rel or '..' in Path(rel).parts: raise ValueError('Unsafe synchronized path')
    value=(root/rel).resolve()
    if value==root.resolve() or not value.is_relative_to(root.resolve()): raise ValueError('Path escapes repository')
    return value


def repository_for(body):
    for root in (Path(body),*Path(body).parents):
        if (root/'spec/handbook-links.json').is_file(): return root
    return None


def files(root):
    for p in sorted(root.rglob('*')):
        rel=p.relative_to(root)
        if any(x in {'.git','__pycache__',TRANSACTION} for x in rel.parts) or p.suffix=='.pyc' or p.name.endswith('.mantle-lock'): continue
        if p.is_symlink(): raise ValueError('Symlink not allowed in synchronized repository: '+str(rel))
        if p.is_file(): yield rel.as_posix(),p


def fingerprints(root,excluded=()):
    return {rel:sha(p.read_bytes()) for rel,p in files(root) if rel not in set(excluded)|{LOCK}}


def snippet(root,spec):
    path=safe(root,spec['source'])
    if not spec['source'].startswith('src/mantleos/'): raise ValueError('Code links must target the shared package')
    text=path.read_text(encoding='utf-8');lines=text.splitlines(keepends=True)
    found=[node for node in ast.parse(text).body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)) and node.name==spec['symbol']]
    if len(found)!=1: raise ValueError('Missing or ambiguous linked symbol: '+spec['symbol'])
    node=found[0];start=min([node.lineno]+[d.lineno for d in node.decorator_list])-1
    return ''.join(lines[start:node.end_lineno]).rstrip('\r\n'),path,lines,start,node.end_lineno


def guide_links(root, chapter, destination):
    """Keep handbook-relative Markdown links valid in generated subdirectory guides."""
    target_dir=(root/destination).parent
    def relocate(match):
        address=match.group(2)
        path,marker,fragment=address.partition('#')
        if (not path or path.startswith(('/', '\\')) or '://' in path or
            path.startswith(('mailto:', 'data:'))):
            return match.group(0)
        source=(root/path).resolve()
        if not source.is_relative_to(root.resolve()):
            raise ValueError('Handbook link escapes repository: '+path)
        local=os.path.relpath(source,target_dir).replace(os.sep,'/')
        return match.group(1)+local+(marker+fragment if marker else '')+match.group(3)
    return re.sub(r'(\[[^\]]+\]\()([^)]+)(\))',relocate,chapter)


def reconcile(root):
    specs=read(root/'spec/handbook-links.json')['links']
    handbook=(root/'HANDBOOK.md').read_text(encoding='utf-8')
    matches=list(BLOCK.finditer(handbook)); blocks={m[1]:m[2] for m in matches}
    if len(blocks)!=len(matches) or set(blocks)!=set(specs): raise ValueError('Missing or duplicate handbook code links')
    previous=read(root/LOCK).get('links',{}) if (root/LOCK).exists() else {}
    current={}
    for key,spec in specs.items():
        source,path,lines,start,end=snippet(root,spec);document=blocks[key]
        source_hash=sha(source.encode());doc_hash=sha(document.encode());base=previous.get(key)
        if base is None and source_hash!=doc_hash: raise ValueError('Initial handbook must match source: '+key)
        if base and source_hash!=base and doc_hash!=base and source_hash!=doc_hash: raise ValueError('Source/document conflict: '+key)
        if base and doc_hash!=base and source_hash==base:
            replacement=document+'\n';ast.parse(replacement)
            path.write_text(''.join(lines[:start])+replacement+''.join(lines[end:]),encoding='utf-8')
            source,*_=snippet(root,spec)
        current[key]=source
    handbook=BLOCK.sub(lambda m:'<!-- mantle:code '+m[1]+' -->\n```python\n'+current[m[1]]+'\n```\n<!-- /mantle:code -->',handbook)
    (root/'HANDBOOK.md').write_text(handbook,encoding='utf-8')
    return {key:sha(value.encode()) for key,value in current.items()}


def demonstration(root):
    """Execute the handbook's actual Engram providers on disposable state."""
    from . import organs
    with tempfile.TemporaryDirectory(prefix='mantle-handbook-') as td:
        td=Path(td);body=td/'engram';shutil.copytree(root/'agents/engram',body)
        source=(root/'src/mantleos/anchor_engine/profiles/hello_world_compact.anchor').read_text('utf-8')
        anchor=organs.invoke(body,'anchor.blueprint.run',{'source':source},permit=True)
        scan=organs.invoke(body,'scan.inspect',{'source':str(root/'examples/scan-mixed'),'workspace':str(td/'scan')},permit=True)
        if anchor['stage']!='VERIFIED' or scan['stage']!='VERIFIED': raise ValueError('Handbook demonstration failed')
        a=anchor['observation']['result'];s=scan['observation']['result']
        if a['stdout']!='Hello, World!' or s['coverage_gaps']<1: raise ValueError('Handbook acceptance mismatch')
        return {'schema':'mantle.handbook-demonstration/1','code_sha256':checkpoint.code_digest(),
                'anchor':{'stage':anchor['stage'],'stdout':a['stdout'],'profile':a['profile']},
                'scan':{'stage':scan['stage'],'coverage_gaps':s['coverage_gaps'],'evidence':s['evidence']}}


def prepare(root,checkpoint_value=None,body_relative='agents/engram',*,run_tests=True):
    links=reconcile(root)
    body=safe(root,body_relative)
    imported=checkpoint.admit(body,checkpoint_value) if checkpoint_value else None
    # A shared repository Body has only a launcher; exported Bodies receive snapshots.
    generated={}
    generated[body_relative+'/ENGRAM.md']=checkpoint.render(body)
    generated['ENGRAM.md']=checkpoint.render(root/'agents/engram')
    from .organs import system_registry
    catalog=system_registry(root/'agents/engram').catalog()
    generated['docs/guides/capabilities.md']='# Engram organ availability\n\n```json\n'+json.dumps(catalog,indent=2)+'\n```\n'
    handbook=(root/'HANDBOOK.md').read_text(encoding='utf-8')
    chapters=re.split(r'(?m)^## ',handbook)[1:]
    for index,part in enumerate(chapters,1):
        name=f'docs/guides/handbook-{index:02d}.md'
        generated[name]=guide_links(root,'# '+part,name)
    aliases={'docs/getting-started/quickstart.md':2,'docs/getting-started/build-a-bio-agent.md':1,
             'docs/guides/scan-a-project.md':4,'docs/guides/use-anchorcode.md':3,
             'docs/guides/build-cartridge.md':6,'docs/concepts/engram-continuity.md':5,
             'docs/guides/verify-and-save.md':6,'docs/reference/file-layout.md':7}
    for path,chapter in aliases.items(): generated[path]=guide_links(root,'# '+chapters[chapter-1],path)
    demo=demonstration(root)
    generated['docs/guides/working-results.md']='# Executed Engram examples\n\n```json\n'+json.dumps(demo,indent=2)+'\n```\n'
    generated['evidence/handbook-examples.json']=json.dumps(demo,indent=2)+'\n'
    for rel,text in generated.items():
        target=safe(root,rel);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text,encoding='utf-8')
    cartridge.write_manifest(body)
    if body_relative!='agents/engram': cartridge.write_manifest(root/'agents/engram')
    generated[body_relative+'/MANIFEST.json']=(body/'MANIFEST.json').read_text(encoding='utf-8')
    generated['agents/engram/MANIFEST.json']=(root/'agents/engram/MANIFEST.json').read_text(encoding='utf-8')
    if run_tests:
        # Test the staged source in a fresh interpreter, never this process's cached modules.
        for pattern in ('test_platform.py','test_projects.py','test_json_contract.py','test_anchor_qualification.py','test_scan*.py',
                        'test_core.py','test_anchor_merge.py','test_chroma_kernel.py',
                        'test_chroma_selfhosting.py','test_chase_homeostasis.py',
                        'test_alignment.py'):
            p=subprocess.run([sys.executable,'-X','utf8','-B','-m','unittest','discover','-s','tests','-p',pattern],
                cwd=root,text=True,capture_output=True,encoding='utf-8',timeout=180)
            if p.returncode: raise ValueError('Staged validation failed:\n'+p.stdout+p.stderr)
    cartridge.verify(root/'agents/engram')
    state={'schema':'mantle.sync/1','links':links,
           'inputs':fingerprints(root,generated),'outputs':{k:sha(safe(root,k).read_bytes()) for k in generated},
           'agent_base':checkpoint.identity(root/'agents/engram')}
    write(root/LOCK,state)
    return {'result':'PASS','links':len(links),'agent_base':state['agent_base'],'checkpoint':imported}


def check(root):
    root=Path(root).resolve()
    if (root/TRANSACTION).exists(): raise ValueError('Interrupted synchronization; run sync --recover')
    state=read(root/LOCK)
    changed=[]
    actual=fingerprints(root,state['outputs'])
    for rel in set(actual)|set(state['inputs']):
        if actual.get(rel)!=state['inputs'].get(rel): changed.append(rel)
    for rel,value in state['outputs'].items():
        p=safe(root,rel)
        if not p.is_file() or sha(p.read_bytes())!=value: changed.append(rel)
    if changed: raise ValueError('Unsynchronized files: '+', '.join(sorted(changed)[:30]))
    cartridge.verify(root/'agents/engram')
    return {'result':'PASS','links':len(state['links']),'revision':state['agent_base']['revision']}


def publish(root,stage,*,interrupt_after=None):
    """Journal before replacement; recovery restores the pre-publication dirty workspace."""
    changes=[]
    for rel,p in files(stage):
        target=safe(root,rel)
        if not target.exists() or target.read_bytes()!=p.read_bytes(): changes.append(rel)
    journal=root/TRANSACTION
    journal.mkdir()  # Exclusive single writer.
    records=[]
    for index,rel in enumerate(changes):
        target=safe(root,rel);before=target.read_bytes() if target.exists() else None
        after=safe(stage,rel).read_bytes()
        if before is not None: (journal/f'{index}.before').write_bytes(before)
        (journal/f'{index}.after').write_bytes(after)
        records.append({'path':rel,'before':sha(before) if before is not None else None,'after':sha(after),'index':index})
    write(journal/'journal.json',{'records':records})
    for count,item in enumerate(records,1):
        target=safe(root,item['path']);target.parent.mkdir(parents=True,exist_ok=True)
        os.replace(journal/f"{item['index']}.after",target)
        if interrupt_after==count: raise RuntimeError('Simulated interrupted publication')
    shutil.rmtree(journal)


def recover(root):
    root=Path(root).resolve();journal=root/TRANSACTION
    if not journal.exists(): return {'result':'NOTHING_TO_RECOVER'}
    if not (journal/'journal.json').exists():
        # Replacements begin only after the complete journal exists.
        shutil.rmtree(journal);return {'result':'RECOVERED'}
    records=read(journal/'journal.json')['records']
    for item in records:
        p=safe(root,item['path']);current=sha(p.read_bytes()) if p.exists() else None
        if current not in {item['before'],item['after']}: raise ValueError('Recovery conflict: '+item['path'])
    for item in records:
        p=safe(root,item['path'])
        if item['before'] is None:
            if p.exists(): p.unlink()
        else: p.write_bytes((journal/f"{item['index']}.before").read_bytes())
    shutil.rmtree(journal)
    return {'result':'RECOVERED','files':len(records)}


def synchronize(root,*,checkpoint_value=None,body=None):
    root=Path(root).resolve()
    if (root/TRANSACTION).exists(): raise ValueError('Run sync --recover first')
    before=fingerprints(root)
    relative=(Path(body).resolve().relative_to(root).as_posix() if body else 'agents/engram')
    with tempfile.TemporaryDirectory(prefix='mantle-sync-') as td:
        stage=Path(td)/'repo'
        shutil.copytree(root,stage,ignore=shutil.ignore_patterns('.git','__pycache__','*.pyc',TRANSACTION))
        request=Path(td)/'request.json';write(request,{'checkpoint':checkpoint_value,'body':relative})
        p=subprocess.run([sys.executable,'-X','utf8','-B',str(stage/'tools/sync_worker.py'),str(request)],
            cwd=stage,text=True,capture_output=True,encoding='utf-8',timeout=600)
        if p.returncode: raise ValueError('Synchronization refused; previous exports retained.\n'+p.stdout+p.stderr)
        if fingerprints(root)!=before: raise ValueError('Workspace changed during synchronization; retry after resolving concurrent edits')
        publish(root,stage)
        return json.loads(p.stdout)


def package(root,output):
    root=Path(root).resolve();output=Path(output).resolve();check(root)
    if output.exists() or output.is_relative_to(root): raise ValueError('Package output must be new and outside repository')
    cartridge.validate_portable_tree(root)
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for rel,p in files(root):
            info=zipfile.ZipInfo('mantleos/'+rel,date_time=(2026,10,7,0,0,0))
            info.external_attr=(0o100644<<16)
            archive.writestr(info,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED)
    with tempfile.TemporaryDirectory(prefix='mantle-package-') as td:
        with zipfile.ZipFile(output) as archive: archive.extractall(td)
        check(Path(td)/'mantleos')
    return {'result':'PASS','output':str(output),'sha256':sha(output.read_bytes()),'bytes':output.stat().st_size}
