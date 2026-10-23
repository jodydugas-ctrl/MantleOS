"""Opt-in reference cache and a read-only progressive Chase dashboard."""
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from . import chase_v2 as catalog
from .common import ScanError, sha

OFFICIAL_HOSTS = frozenset({'docs.letta.com','docs.langchain.com','openai.github.io','learn.microsoft.com','docs.all-hands.dev'})


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ScanError('Reference refresh redirects require separate review')


def fetch_document(url):
    request = Request(url, headers={'User-Agent':'MantleOS-reference-reader','Accept':'text/plain,text/html,application/json'})
    with build_opener(NoRedirect).open(request, timeout=10) as response:
        if response.status != 200: raise ScanError('Reference refresh did not return HTTP 200')
        data = response.read(catalog.INPUT_LIMIT + 1)
    if len(data) > catalog.INPUT_LIMIT: raise ScanError('Reference refresh byte budget exceeded')
    return data


def refresh_reference(workspace, target_id, expected_revision, *, permit_fetch=False, declared_revision='UNVERIFIED',
                      license='UNVERIFIED', fetcher=None, body=None):
    if permit_fetch is not True: raise ScanError('Reference networking disabled; explicit host permission required')
    catalog.text(declared_revision,128); catalog.text(license,256)
    initial = catalog.list_catalog(workspace,body=body)
    target = next((t for t in initial['targets'] if t['target_id'] == target_id),None)
    if target is None: raise ScanError('Unknown reference target')
    catalog.revision(expected_revision)
    if initial['revision'] != expected_revision: raise ScanError('Stale reference refresh revision')
    parsed = urlsplit(target['reference_url'])
    if parsed.hostname not in OFFICIAL_HOSTS or parsed.port not in (None,443):
        raise ScanError('Reference URL is outside the official HTTPS allowlist')
    data = (fetcher or fetch_document)(target['reference_url'])
    if not isinstance(data,bytes) or len(data) > catalog.INPUT_LIMIT: raise ScanError('Invalid bounded reference response')
    # Persist inert UTF-8 text; binary/code is neither imported nor executed.
    content = data.decode('utf-8')
    record = {'kind':'REFERENCE_CACHE','target_id':target_id,'url':target['reference_url'],
              'retrieved_at':datetime.now(timezone.utc).isoformat(),'content_sha256':sha(data),
              'declared_revision':declared_revision,'license':license,'content_text':content,'status':'UNVERIFIED'}
    with catalog.transaction(workspace,expected_revision,body=body) as state:
        state['receipt_links'].append(record)
    return state


SHELL = ('<h1>Capability Chase</h1><label>Filter challenges <input id="chase-filter"></label>'
         '<p id="chase-revision"></p><div id="chase-scorecard"></div>'
         '<h2>Proposals and manual reviews</h2><pre id="chase-proposals"></pre>'
         '<p>Read-only. Evidence does not grant integration permission.</p>')


def dashboard_snapshot(workspace, *, body=None):
    state = catalog.list_catalog(workspace,body=body)
    return {'schema':'mantle.chase.dashboard/2','revision':state['revision'],
            'scorecard':catalog.build_scorecard(workspace,body=body),
            'proposals':[{'proposal_id':p['proposal_id'],'challenge_id':p['challenge_id'],'status':p['status']}
                         for p in state['proposals']],
            'reviews':[{'proposal_id':r['proposal_id'],'approver':r['approver'],'status':r['status']}
                       for r in state['reviews']], 'authority':'NONE'}


def publish_dashboard(workspace, app_workspace, *, expected_revision, body=None):
    from .. import progressive_app as app
    from ..anchor_engine.tools.anchor_runtime import render_hello_world
    folder = catalog._path(app_workspace,body).parent
    # The dashboard's app files cannot clobber catalog state or sit above it.
    source = Path(workspace).resolve()
    if folder.is_relative_to(source) or source.is_relative_to(folder):
        raise ScanError('Dashboard and catalog need separate external workspaces')
    snapshot = dashboard_snapshot(workspace,body=body)
    if snapshot['revision'] != expected_revision: raise ScanError('Stale dashboard catalog revision')
    folder.parent.mkdir(parents=True,exist_ok=True)
    from tempfile import TemporaryDirectory
    with TemporaryDirectory(prefix='chase-dashboard-',dir=folder.parent) as temporary:
        shell = Path(temporary) / 'shell.anchor'
        shell.write_text(render_hello_world('ChaseDashboard',SHELL,profile='EMIT_TEXT/0.2'),encoding='utf-8',newline='\n')
        if not folder.exists():
            app.start(folder,shell,'ChaseDashboard',body=body or Path(temporary) / 'guard')
        state = app.read(folder)
        if state['app_id'] != 'ChaseDashboard' or state['shell'] != SHELL:
            raise ScanError('Dashboard workspace belongs to a different app')
        mid = 'chase-revision-' + str(snapshot['revision'])
        encoded = json.dumps(snapshot,ensure_ascii=True).replace('<','\\u003c')
        script = """const data = DATA;
window.MantleChase = data;
const filter = root.querySelector('#chase-filter');
function draw(){
 const latest = window.MantleChase;
 const cards = root.querySelector('#chase-scorecard'); cards.replaceChildren();
 for (const row of latest.scorecard.challenges){
  if(!row.challenge_id.includes(filter.value)) continue;
  const card = document.createElement('p');
  card.textContent = row.challenge_id + ': ' + row.title + ' / ' + row.test_state + ' / gap ' + row.gap_status
   + ' / evidence ' + row.evidence_grade
   + ' / validated receipt at snapshot ' + (row.receipt_sha256 || 'NONE');
  cards.append(card);
 }
 root.querySelector('#chase-revision').textContent = 'Catalog revision ' + latest.revision;
 root.querySelector('#chase-proposals').textContent = JSON.stringify({proposals:latest.proposals,reviews:latest.reviews},null,2);
}
if(!filter.dataset.chaseBound){filter.addEventListener('input',draw);filter.dataset.chaseBound='1';}
draw(); api.ready();""".replace('DATA',encoded,1)
        existing = next((m for m in state['modules'] if m['id'] == mid),None)
        if existing:
            if existing['content'] != script: raise ScanError('Conflicting dashboard evidence at same catalog revision')
        else:
            module = Path(temporary) / 'module.anchor'
            module.write_text(render_hello_world('ChaseUpdate',script,profile='EMIT_TEXT/0.2'),encoding='utf-8',newline='\n')
            app.add(folder,module,mid,'javascript',[],expected_revision=state['revision'],body=body or Path(temporary) / 'guard')
    return app.payload(folder)
