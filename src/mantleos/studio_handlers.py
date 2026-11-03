"""Owner-selected deterministic Studio limb handler; no generated-code execution."""
import json
from pathlib import Path

from . import studio_project


def handle(value):
    from . import studio
    role=value['role'];payload=value['input'];nest=Path(value['nest'])
    operation=payload.get('operation')
    if operation=='inspect' and role=='body-mapping':
        with studio.database(nest) as db:
            observed=db.execute("SELECT value FROM events WHERE kind='host.started' ORDER BY seq DESC LIMIT 1").fetchone()
        return {'capabilities':{'node-red':'PRESENT' if observed else 'UNKNOWN','remote-deployment':'PROHIBITED'},
                'host_observation':json.loads(observed[0]) if observed else None}
    if operation=='validate' and role in ('design','contracts','verification'):
        return studio_project.inspection(payload['project'])
    if operation=='remember' and role in ('memory','communications'):
        return {'remembered':str(payload.get('text',''))[:4096]}
    if operation=='plan' and role=='construction':
        from .kpp import build
        from .json_contract import digest
        recipe=studio.project_get(nest)['project']['recipe']
        workspace=nest/'kpp-workspaces'/digest(recipe)
        if workspace.exists():return build.step(workspace)
        return {'status':'PROPOSAL_ONLY','reason':'Owner must prepare the KPP workspace'}
    if operation=='diagnose' and role=='repair':
        with studio.database(nest) as db:
            rows=db.execute("SELECT id,value FROM events WHERE kind='pain' ORDER BY seq DESC LIMIT 4").fetchall()
        return {'status':'OBSERVATION','pain':[{'event':i,'value':json.loads(v)} for i,v in rows],'repair_authority':'NONE'}
    return {'status':'PROPOSAL_ONLY','reason':'No executable grant for this operation','operation':operation}
