"""Pinned n8n command declarations -> draft KPP obligations, never parity evidence.

Read-only Git/source inspection. No installation, execution, acceptance or runtime
migration. Dynamic factories, dialogs, node catalogs and edition gates need review.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from mantleos import anchors, anchor_design
from mantleos.kpp.core import validate_recipe, write_json

PIN='261663556d98c9502663f6618edd8edd537e5688'
FRONT='packages/frontend/editor-ui/src/'


def declarations(text, path):
    """Bounded lexical declarations only, not Vue execution or complete discovery."""
    results=[]
    match=re.search(r'const ITEM_ID\s*=\s*\{(.*?)\}',text,re.S)
    if match:
        for item in re.finditer(r"^[ \t]*([A-Z_]+):\s*'([^']+)'",match[1],re.M):
            offset=match.start(1)+item.start()
            results.append(dict(command=item[2],symbol=item[1],source=path,line=text[:offset].count('\n')+1))
    if path.endswith('useContextMenuItems.ts'):
        match=re.search(r'export type ContextMenuAction\s*=(.*?);',text,re.S)
        if match:
            for item in re.finditer(r"\|\s*'([^']+)'",match[1]):
                offset=match.start(1)+item.start()
                results.append(dict(command=item[1],symbol=item[1],source=path,line=text[:offset].count('\n')+1))
    return results


def discover(source):
    source=Path(source).resolve()
    head=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    if head!=PIN:raise ValueError('Reference must be exact n8n 2.46.4 commit '+PIN)
    paths=sorted((source/FRONT/'features/shared/commandBar/composables').glob('use*Commands.ts'))
    paths+=[source/FRONT/'features/shared/contextMenu/composables/useContextMenuItems.ts']
    if not paths:raise ValueError('Pinned frontend sources are missing')
    records=[];pins={};dynamic=[]
    for path in paths:
        relative=path.relative_to(source).as_posix()
        if path.is_symlink() or not path.resolve().is_relative_to(source):raise ValueError('Unsafe reference path')
        raw=path.read_bytes()
        if len(raw)>1_000_000:raise ValueError('Oversized declaration source')
        committed=subprocess.check_output(['git','-C',str(source),'show',PIN+':'+relative])
        if raw!=committed:raise ValueError('Changed reference source: '+relative)
        pins[relative]=hashlib.sha256(raw).hexdigest();text=raw.decode('utf8')
        records+=declarations(text,relative)
        if any(term in text for term in ('children:', '.map(', 'generateMergedNodesAndActions','isEnterpriseFeatureEnabled')):dynamic.append(relative)
    for relative in ('packages/nodes-base/nodes/If/V2/IfV2.node.ts','packages/workflow/src/node-parameters/filter-parameter.ts'):
        raw=(source/relative).read_bytes()
        if raw!=subprocess.check_output(['git','-C',str(source),'show',PIN+':'+relative]):raise ValueError('Changed IF source')
        pins[relative]=hashlib.sha256(raw).hexdigest()
    return dict(reference=dict(repository='n8n-io/n8n',release='2.46.4',commit=PIN,edition='SELF_HOSTED_COMMUNITY'),
                files=pins,declarations=records,dynamic_sources=dynamic,
                completeness='NOT_ESTABLISHED: lexical command declarations only; dynamic children, dialogs, settings, node operations, credentials and edition gates require source/runtime review',
                verification='NOT_RUN',acceptance='NOT_GRANTED')


def design():
    roles=[('BH-COMMAND','BlackHole','Receive user commands, item data and reference observations.'),
           ('N-WORKFLOW','Neutral','Own editable workflows, item links, parameters, history and persisted execution state.'),
           ('N-HOST','Neutral','Coordinate the Node-RED Body, private Engrams, supervised cognition and portable handoff.'),
           ('WH-CONTRACT','WhiteHole','Enforce typed conditions, source/revision, independent authority, error and release boundaries.')]
    return anchor_design.validate(dict(schema='anchor.design/1',id='Studio-Deep-Chase',purpose='Preserve declared command consequences at reviewed Fidelity scope.',
        applications=[anchors.application(i,definition_id=t,attributes=dict(responsibility=r)) for i,t,r in roles],
        flows=[dict(**{'from':'BH-COMMAND','to':'WH-CONTRACT'},relationship='Check command inputs and authority'),dict(**{'from':'WH-CONTRACT','to':'N-WORKFLOW'},relationship='Admit valid state transitions'),dict(**{'from':'N-WORKFLOW','to':'N-HOST'},relationship='Perform admitted Body work and retain checked observations')],
        state=[dict(id='workflow-state',owner='N-WORKFLOW'),dict(id='native-host-bindings',owner='N-HOST')],
        effects=[dict(id='workflow-execution',requester='N-HOST',guard='WH-CONTRACT',confirmation='Explicit operator deployment/run and independently granted host effects; model text never grants authority.')]))


def recipe(inventory, resources):
    value=json.loads((Path(resources)/'recipes/anchor-studio-visual-chase.json').read_text('utf8'))
    value.update(id='anchor-studio-community-deep-chase',goal='Chase all reviewed self-hosted n8n Community user command consequences on Node-RED; keep missing behavior explicit')
    value['target'].update(reference_version='n8n@2.46.4:'+PIN,source='https://github.com/n8n-io/n8n/tree/'+PIN,
        fidelity_semantics='Existing numeric Fidelity declaration retained. Deepen nested command, parameter, dataflow, failure, persistence and cross-system consequences; discovery completeness is an explicit mandatory gate.')
    value['anchor_design']=design()
    for item in value['anchors']:item['design_anchors']=['BH-COMMAND','N-WORKFLOW','N-HOST','WH-CONTRACT']
    value['anchors'].append(dict(id='community-scope-review',statement='Review Community edition visibility, all nested dialogs/settings, dynamic node catalogs and operation variants against the pinned reference; do not infer completeness from static declarations',
        test='Reconcile source declarations with actual reference runtime and require a disposition for every observed command, field, nested operation and guard; missing functions remain unmet',required=True,depth=5,depends=[],design_anchors=['BH-COMMAND','WH-CONTRACT']))
    for index,record in enumerate(inventory['declarations']):
        value['anchors'].append(dict(id='reference-command-'+str(index+1),required=True,depth=5,depends=['community-scope-review'],design_anchors=['BH-COMMAND','N-WORKFLOW','N-HOST','WH-CONTRACT'],
            statement='DRAFT REQUIRES REVIEW: reproduce '+record['command']+' from '+record['source']+':'+str(record['line'])+' for its applicable Community states; inspect its actual handler and all child commands before admission.',
            test='Compare reference/candidate visible and keyboard entry points, enabled/disabled guards, valid and invalid input, confirm/cancel, state/data effects, undo where applicable, persistence after reload, error/permission cases and interacting prior behaviors. A menu entry alone does not pass.'))
    return validate_recipe(value)


def run(source,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    inventory=discover(source);resources=Path(__file__).resolve().parents[1]
    value=recipe(inventory,resources)
    write_json(output/'discovery.json',inventory);write_json(output/'recipe.json',value)
    (output/'contract.anchor.txt').write_text(anchor_design.render_contract(value),encoding='utf8')
    return dict(commands=len(inventory['declarations']),source_files=len(inventory['files']),obligations=len(value['anchors']),
                status='DRAFT_TRANSLATION_REQUIRES_SOURCE_AND_RUNTIME_REVIEW',acceptance='NOT_GRANTED',output=str(output.resolve()))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    print(json.dumps(run(a.source,a.output),indent=2))
