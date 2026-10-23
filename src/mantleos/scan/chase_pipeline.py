"""Candidate-only proposals, receipt validation and manual review boundaries."""
from datetime import datetime, timezone
import math
from pathlib import Path, PurePosixPath
from . import chase_v2 as catalog
from .common import ScanError, digest, read_json, sha, strict_json, tree_identity


def relative_path(value):
    catalog.text(value, 512)
    path = PurePosixPath(value)
    if path.is_absolute() or '\\' in value or ':' in value or '..' in path.parts or str(path) != value or value == '.':
        raise ScanError('Candidate scope needs normalized relative paths')
    if any(part.casefold() in catalog.PROTECTED for part in path.parts):
        raise ScanError('Protected Body identity/ledger/source pins cannot be proposed')
    return value


def _proposal(value):
    value = catalog.bounded(value)
    catalog.exact(value, 'schema proposal_id challenge_id objective allowed_paths protected_paths baseline_tree_digest implementation_notes risk independent_checks rollback_plan created_at status')
    if value['schema'] != 'mantle.chase.proposal/2' or value['status'] != 'DRAFT':
        raise ScanError('Proposals start as DRAFT only')
    catalog.identifier(value['proposal_id']); catalog.identifier(value['challenge_id'])
    for key in ('objective', 'implementation_notes', 'risk', 'rollback_plan'): catalog.text(value[key])
    catalog.hash_value(value['baseline_tree_digest']); catalog.utc(value['created_at'])
    for key in ('allowed_paths', 'protected_paths', 'independent_checks'):
        if not isinstance(value[key],list) or not 1 <= len(value[key]) <= 128 or len(set(value[key])) != len(value[key]):
            raise ScanError('Proposal needs bounded unique paths and independent checks')
    for path in value['allowed_paths']: relative_path(path)
    for path in value['protected_paths']:
        catalog.text(path,512)
        if PurePosixPath(path).is_absolute() or '..' in PurePosixPath(path).parts or '\\' in path or ':' in path:
            raise ScanError('Invalid protected scope')
        if any(path == allowed or PurePosixPath(allowed).is_relative_to(path) or PurePosixPath(path).is_relative_to(allowed)
               for allowed in value['allowed_paths']):
            raise ScanError('Allowed paths intersect protected scope')
    for check in value['independent_checks']: catalog.text(check)
    return value


def proposal(state, proposal_id):
    item = next((p for p in state['proposals'] if p['proposal_id'] == proposal_id),None)
    if item is None: raise ScanError('Unknown Chase proposal')
    return item


def create_proposal(workspace, value, expected_revision, *, body=None):
    value = _proposal(value)
    with catalog.transaction(workspace, expected_revision, body=body) as state:
        catalog.challenge(state, value['challenge_id'])
        if any(p['proposal_id'] == value['proposal_id'] for p in state['proposals']):
            raise ScanError('Immutable proposal ID already exists')
        state['proposals'].append(value)
    return state


def _binding(value):
    catalog.exact(value, 'fixture fixture_path fixture_sha256 oracle oracle_path oracle_sha256 environment baseline_identity runtime_versions check measure repeats timeout_seconds total_seconds minimum_improvement_percent compare_stdout')
    relative_path(value['fixture_path']); relative_path(value['oracle_path'])
    for key in ('fixture','oracle','environment'): catalog.text(value[key])
    for key in ('fixture_sha256','oracle_sha256','baseline_identity'): catalog.hash_value(value[key])
    if not isinstance(value['runtime_versions'],dict) or not 1 <= len(value['runtime_versions']) <= 16:
        raise ScanError('Pin runtime/tool versions')
    for k,v in value['runtime_versions'].items(): catalog.text(k,100); catalog.text(v,100)
    for key in ('check','measure'):
        command = value[key]
        if not isinstance(command,list) or not 1 <= len(command) <= 64:
            raise ScanError('Independent check and measurement need argument arrays')
        for arg in command: catalog.text(arg,4096)
    for key, low, high in (('repeats',3,15),('timeout_seconds',1,120),('total_seconds',1,3600)):
        if type(value[key]) is not int or not low <= value[key] <= high: raise ScanError('Invalid experiment bound')
    if type(value['minimum_improvement_percent']) not in (int,float) or not 0 <= value['minimum_improvement_percent'] < 100 or value['compare_stdout'] is not True:
        raise ScanError('Invalid comparison contract')
    return catalog.bounded(value)


def verify_inputs(baseline, candidate, binding):
    for root in (Path(baseline).resolve(),Path(candidate).resolve()):
        for key in ('fixture','oracle'):
            path = root / binding[key + '_path']
            if not path.resolve().is_relative_to(root) or any(p.is_symlink() for p in (path,*path.parents) if p.is_relative_to(root)):
                raise ScanError('Fixture/oracle path escapes source or traverses symlink')
            if not path.is_file() or path.stat().st_size > catalog.INPUT_LIMIT or sha(path.read_bytes()) != binding[key + '_sha256']:
                raise ScanError('Pinned independent fixture/oracle bytes differ')


def transition_proposal(workspace, proposal_id, status, expected_revision, *, binding=None, body=None):
    if status not in ('READY_FOR_EXPERIMENT','REJECTED'):
        raise ScanError('This transition requires a verified receipt or trusted review')
    ready = _binding(binding) if status == 'READY_FOR_EXPERIMENT' else None
    if status == 'REJECTED' and binding is not None: raise ScanError('Rejected transition does not take a binding')
    with catalog.transaction(workspace,expected_revision,body=body) as state:
        item = proposal(state,proposal_id)
        if item['status'] not in ('DRAFT','READY_FOR_EXPERIMENT') or (status == 'READY_FOR_EXPERIMENT' and item['status'] != 'DRAFT'):
            raise ScanError('Invalid proposal state transition')
        if ready:
            evaluation = catalog.challenge(state,item['challenge_id'])['evaluation']
            if any(ready[k] != evaluation[k] for k in ('fixture','oracle','environment')) or ready['baseline_identity'] != item['baseline_tree_digest']:
                raise ScanError('Fixture/oracle/environment/baseline differ from immutable challenge')
            item['binding'] = ready
        item['status'] = status
    return state


def _run(value):
    if not isinstance(value,dict) or value.get('status') != 'COMPLETED' or value.get('exit_code') != 0 or value.get('truncated') is not False:
        raise ScanError('Receipt run failed, partial or truncated')
    for key in ('stdout','stderr'):
        if not isinstance(value.get(key),str) or sha(value[key].encode('utf-8')) != value.get(key + '_sha256'):
            raise ScanError('Receipt output byte hash mismatch; require UTF-8 oracle output')
    if type(value.get('seconds')) not in (int,float) or not math.isfinite(value['seconds']) or value['seconds'] < 0:
        raise ScanError('Invalid receipt timing')
    return value


def _metric(run, evaluation, binding):
    # The check command must output a machine-readable oracle result, not a
    # free-form PASS string. This is scoped local evidence, not attestation.
    result = strict_json(_run(run)['stdout'])
    catalog.exact(result,'schema fixture fixture_sha256 oracle_sha256 environment metric sample_size value case_ids')
    if result['schema'] != 'mantle.chase.oracle-result/2' or any(result[k] != binding[k] for k in ('fixture','fixture_sha256','oracle_sha256','environment')):
        raise ScanError('Oracle fixture/environment digest mismatch')
    if result['metric'] != evaluation['metric'] or type(result['sample_size']) is not int or result['sample_size'] != evaluation['sample_size']:
        raise ScanError('Oracle metric/sample size mismatch')
    ids = result['case_ids']
    if not isinstance(ids,list) or len(ids) != result['sample_size'] or not all(isinstance(x,str) and x.strip() for x in ids) or len(set(ids)) != len(ids):
        raise ScanError('Oracle must enumerate distinct evaluated fixture cases')
    number = result['value']
    if type(number) not in (int,float) or not math.isfinite(number) or number < 0:
        raise ScanError('Oracle returned invalid metric')
    return result


def link_experiment(workspace, proposal_id, receipt_path, expected_revision, *, expected_receipt_sha256,
                    baseline, candidate, body=None):
    catalog.hash_value(expected_receipt_sha256)
    receipt = read_json(receipt_path,catalog.STATE_LIMIT)
    if sha(Path(receipt_path).read_bytes()) != expected_receipt_sha256:
        raise ScanError('Experiment receipt file hash mismatch')
    before = receipt.get('identities_before')
    if (receipt.get('schema') != 'scan.experiment/1' or receipt.get('status') not in
            ('VERIFIED_WITHIN_DECLARED_CHECK_SCOPE','NO_SUPPORTED_IMPROVEMENT') or before != receipt.get('identities_after')):
        raise ScanError('Incomplete or changed-source experiment receipt')
    actual = {'baseline':tree_identity(baseline), 'candidate':tree_identity(candidate)}
    if before != actual or Path(baseline).resolve() == Path(candidate).resolve():
        raise ScanError('Stale source/candidate or non-distinct experiment trees')
    if body is not None:
        from .common import outside
        outside(candidate,body); outside(receipt_path,body)
    with catalog.transaction(workspace,expected_revision,body=body) as state:
        item = proposal(state,proposal_id)
        if item['status'] != 'READY_FOR_EXPERIMENT': raise ScanError('Proposal is not ready for experiment')
        binding = item['binding']
        verify_inputs(baseline,candidate,binding)
        if before['baseline'] != item['baseline_tree_digest'] or receipt.get('specification') != {
                key:binding[key] for key in ('check','measure','repeats','timeout_seconds','total_seconds','minimum_improvement_percent','compare_stdout')}:
            raise ScanError('Experiment does not match exact independent check contract')
        # Candidate changes must stay within the proposal, independently of stdout.
        from .common import source_paths
        def inventory(root): return {p.relative_to(root).as_posix():sha(p.read_bytes()) for p in source_paths(root)}
        old,new = inventory(Path(baseline).resolve()),inventory(Path(candidate).resolve())
        changed = [p for p in old.keys() | new.keys() if old.get(p) != new.get(p)]
        for path in changed: relative_path(path)
        if any(not any(p == allowed or PurePosixPath(p).is_relative_to(allowed) for allowed in item['allowed_paths']) for p in changed):
            raise ScanError('Candidate changed files outside allowed proposal scope')
        evaluation = catalog.challenge(state,item['challenge_id'])['evaluation']
        checks = receipt.get('checks',{})
        baseline_result = _metric(checks.get('baseline'),evaluation,binding)
        local = _metric(checks.get('candidate'),evaluation,binding)
        if local['case_ids'] != baseline_result['case_ids']: raise ScanError('Oracle case identities differ')
        trials = receipt.get('trials')
        if not isinstance(trials,list) or len(trials) != binding['repeats'] + 1:
            raise ScanError('Missing matched experiment trials')
        if [r.get('trial') for r in trials] != list(range(-1,binding['repeats'])) or any(r.get('warmup') is not (i == 0) for i,r in enumerate(trials)):
            raise ScanError('Malformed/wrong matched trial identities')
        for row in trials:
            for key in ('baseline','candidate'): _run(row.get(key))
            if row['baseline']['stdout_sha256'] != row['candidate']['stdout_sha256']:
                raise ScanError('Matched trial output differs')
        if any(r['receipt_sha256'] == expected_receipt_sha256 for r in state['receipt_links'] if r['kind'] == 'EXPERIMENT'):
            raise ScanError('Experiment receipt already linked')
        value, threshold = local['value'],evaluation['threshold']
        passed = {'>=':value >= threshold,'<=':value <= threshold,'==':value == threshold}[evaluation['comparator']]
        state['receipt_links'].append({'kind':'EXPERIMENT','proposal_id':proposal_id,'challenge_id':item['challenge_id'],
            'receipt_sha256':expected_receipt_sha256,'receipt_path':str(Path(receipt_path).resolve()),
            'candidate_tree_digest':actual['candidate'],'baseline_tree_digest':actual['baseline'],
            'binding_sha256':digest(binding),'runtime_versions':binding['runtime_versions'],
            'matched_trials':binding['repeats'],'local_result':local,'baseline_result':baseline_result,
            'scope':catalog.challenge(state,item['challenge_id'])['scope'],
            'test_state':'LOCAL_CAPABILITY_DEMONSTRATED' if passed else 'LOCAL_GAP_EVIDENCED',
            'reference_status':'UNVERSIONED_UNVERIFIED','authority':'NONE'})
        item['status'] = 'VALIDATED_WITHIN_SCOPE' if passed else 'REJECTED'
    return state


def review_proposal(workspace, decision, expected_revision, *, verifier=None, body=None, now=None):
    decision = catalog.bounded(decision)
    catalog.exact(decision,'schema proposal_id candidate_tree_digest receipt_digest scope approver expires_at nonce decision rollback_note')
    if decision['schema'] != 'mantle.chase.review/2' or decision['decision'] not in ('APPROVE','REJECT'):
        raise ScanError('Invalid manual review decision')
    for key in ('candidate_tree_digest','receipt_digest'): catalog.hash_value(decision[key])
    for key in ('scope','approver','nonce','rollback_note'): catalog.text(decision[key])
    expiry = catalog.utc(decision['expires_at'])
    instant = now or datetime.now(timezone.utc)
    if instant.tzinfo is None or expiry <= instant: raise ScanError('Expired manual review')
    if not callable(verifier): raise ScanError('Independent trusted host approval verifier required')
    with catalog.transaction(workspace,expected_revision,body=body) as state:
        item = proposal(state,decision['proposal_id'])
        if item['status'] != 'VALIDATED_WITHIN_SCOPE': raise ScanError('Only validated proposals can be reviewed')
        link = next((r for r in state['receipt_links'] if r['kind'] == 'EXPERIMENT' and r['proposal_id'] == item['proposal_id']),None)
        if link is None or any(decision[a] != link[b] for a,b in (('candidate_tree_digest','candidate_tree_digest'),('receipt_digest','receipt_sha256'),('scope','scope'))):
            raise ScanError('Review hash/scope mismatch')
        if sha(Path(link['receipt_path']).read_bytes()) != link['receipt_sha256']:
            raise ScanError('Review experiment receipt changed')
        if any(r['nonce'] == decision['nonce'] for r in state['reviews']): raise ScanError('Replayed review nonce')
        # Callback receives an independent copy after all bindings are checked.
        if verifier(catalog.bounded(decision)) is not True: raise ScanError('Trusted host denied review')
        result = 'APPROVED_FOR_MANUAL_INTEGRATION' if decision['decision'] == 'APPROVE' else 'REJECTED'
        state['reviews'].append({**decision,'status':result,'automatic_promotion':False})
        item['status'] = result
    return state


def record_comparison(workspace, proposal_id, reference, expected_revision, *, receipt_path,
                      expected_receipt_sha256, reference_tree, candidate, verifier=None, body=None):
    """Host-verified pinned reference plus a separately executed paired receipt.

    The host verifies provenance of the checkout. Local matched measurements
    establish only the named challenge; no framework-wide parity is asserted.
    """
    reference = catalog.bounded(reference)
    catalog.exact(reference,'schema target_id source_url revision license tree_digest')
    if reference['schema'] != 'mantle.chase.pinned-reference/2': raise ScanError('Invalid pinned reference schema')
    catalog.identifier(reference['target_id']); catalog.url(reference['source_url'])
    for key in ('revision','license'): catalog.text(reference[key],256)
    catalog.hash_value(reference['tree_digest']); catalog.hash_value(expected_receipt_sha256)
    if reference['revision'] == 'UNVERIFIED' or not callable(verifier):
        raise ScanError('Pinned checkout provenance requires a trusted host verifier')
    receipt = read_json(receipt_path,catalog.STATE_LIMIT)
    if sha(Path(receipt_path).read_bytes()) != expected_receipt_sha256: raise ScanError('Comparative receipt file hash mismatch')
    actual = {'baseline':tree_identity(reference_tree),'candidate':tree_identity(candidate)}
    if (reference['tree_digest'] != actual['baseline'] or receipt.get('identities_before') != actual or
            receipt.get('identities_after') != actual or Path(reference_tree).resolve() == Path(candidate).resolve()):
        raise ScanError('Comparative pinned reference/candidate mismatch')
    if body is not None:
        from .common import outside
        outside(reference_tree,body); outside(candidate,body); outside(receipt_path,body)
    with catalog.transaction(workspace,expected_revision,body=body) as state:
        item = proposal(state,proposal_id)
        challenge = catalog.challenge(state,item['challenge_id'])
        local = next((r for r in state['receipt_links'] if r['kind'] == 'EXPERIMENT' and r['proposal_id'] == proposal_id),None)
        if local is None or local['test_state'] != 'LOCAL_CAPABILITY_DEMONSTRATED' or local['candidate_tree_digest'] != actual['candidate']:
            raise ScanError('Comparison needs the exact locally demonstrated candidate')
        if reference['target_id'] != challenge['target_id']: raise ScanError('Wrong comparative target')
        binding = item['binding']; evaluation = challenge['evaluation']
        verify_inputs(reference_tree,candidate,binding)
        specification = {k:binding[k] for k in ('check','measure','repeats','timeout_seconds','total_seconds','minimum_improvement_percent','compare_stdout')}
        if receipt.get('schema') != 'scan.experiment/1' or receipt.get('status') not in ('VERIFIED_WITHIN_DECLARED_CHECK_SCOPE','NO_SUPPORTED_IMPROVEMENT') or receipt.get('specification') != specification:
            raise ScanError('Comparative oracle/environment/run contract differs')
        results = [_metric(receipt.get('checks',{}).get(k),evaluation,binding) for k in ('baseline','candidate')]
        if results[0] != results[1] or results[1] != local['local_result']:
            raise ScanError('Comparative case/metric results differ')
        trials = receipt.get('trials',[])
        if len(trials) != binding['repeats']+1 or [r.get('trial') for r in trials] != list(range(-1,binding['repeats'])):
            raise ScanError('Missing comparative paired trials')
        for i,row in enumerate(trials):
            if row.get('warmup') is not (i == 0): raise ScanError('Comparative warmup identity differs')
            if _run(row.get('baseline'))['stdout_sha256'] != _run(row.get('candidate'))['stdout_sha256']:
                raise ScanError('Comparative trial output differs')
        if any(r.get('receipt_sha256') == expected_receipt_sha256 for r in state['receipt_links']):
            raise ScanError('Comparative receipt must be a separate unreplayed run')
        if verifier(catalog.bounded(reference)) is not True: raise ScanError('Host rejected reference checkout provenance')
        state['receipt_links'].append({'kind':'COMPARISON','proposal_id':proposal_id,'challenge_id':item['challenge_id'],
                'reference':reference,'receipt_path':str(Path(receipt_path).resolve()),'receipt_sha256':expected_receipt_sha256,
                'local_receipt_sha256':local['receipt_sha256'],'candidate_tree_digest':actual['candidate'],
                'binding_sha256':digest(binding),'status':'COMPARATIVE_RESULT_VERIFIED','scope':challenge['scope'],'authority':'NONE'})
    return state


def run_proposal_experiment(workspace, proposal_id, expected_revision, *, baseline, candidate, output,
                            body=None, permit=False, host_policy=None, policy_verifier=None):
    """Explicit adapter to existing Kernel/Metabolism experiment, then receipt link.

    Policy describes host responsibility; this code supplies no OS isolation.
    """
    if permit is not True: raise ScanError('Explicit experiment permission required')
    catalog.exact(host_policy,'schema mode identity')
    if host_policy['schema'] != 'mantle.chase.host-policy/2' or host_policy['mode'] not in ('TRUSTED_BENIGN_FIXTURE','HOST_ISOLATED'):
        raise ScanError('Host must declare trusted fixture or enforced isolation')
    catalog.text(host_policy['identity'])
    if not callable(policy_verifier) or policy_verifier(catalog.bounded(host_policy)) is not True:
        raise ScanError('Independent host isolation/trust policy verifier required')
    state = catalog.list_catalog(workspace,body=body)
    catalog.revision(expected_revision)
    if state['revision'] != expected_revision: raise ScanError('Stale experiment proposal revision')
    item = proposal(state,proposal_id)
    if item['status'] != 'READY_FOR_EXPERIMENT': raise ScanError('Proposal not ready for execution')
    binding = item['binding']; verify_inputs(baseline,candidate,binding)
    if tree_identity(baseline) != item['baseline_tree_digest']: raise ScanError('Stale baseline before execution')
    from ..kernel import scan
    specification = {k:binding[k] for k in ('check','measure','repeats','timeout_seconds','total_seconds','minimum_improvement_percent','compare_stdout')}
    checked = scan('scan.experiment',{'baseline':str(baseline),'candidate':str(candidate),
                   'specification':specification,'output':str(output)},body=body,permit=permit)
    if checked['stage'] != 'VERIFIED': raise ScanError('Existing experiment checked action failed')
    return link_experiment(workspace,proposal_id,output,expected_revision,expected_receipt_sha256=sha(Path(output).read_bytes()),
                           baseline=baseline,candidate=candidate,body=body)


def validate_state(state):
    """Reject unknown/forged state transitions; storage is still unsigned data."""
    known = {c['challenge_id'] for c in state['challenges']}
    if any(len(state[key]) > 4096 for key in catalog.COLLECTIONS): raise ScanError('Chase collection budget exceeded')
    ids = set()
    statuses = {'DRAFT','READY_FOR_EXPERIMENT','VALIDATED_WITHIN_SCOPE','REJECTED','APPROVED_FOR_MANUAL_INTEGRATION'}
    for item in state['proposals']:
        if item.get('status') not in statuses or item.get('challenge_id') not in known or item.get('proposal_id') in ids:
            raise ScanError('Invalid stored proposal identity/status')
        base = {k:v for k,v in item.items() if k != 'binding'}
        base['status'] = 'DRAFT'; _proposal(base)
        ids.add(item['proposal_id'])
        if 'binding' in item: _binding(item['binding'])
        elif item['status'] not in ('DRAFT','REJECTED'): raise ScanError('Stored proposal missing ready binding')
    for link in state['receipt_links']:
        if link.get('kind') not in ('EXPERIMENT','REFERENCE_CACHE','COMPARISON'):
            raise ScanError('Unknown stored receipt kind')
        if link['kind'] == 'EXPERIMENT':
            catalog.exact(link,'kind proposal_id challenge_id receipt_sha256 receipt_path candidate_tree_digest baseline_tree_digest binding_sha256 runtime_versions matched_trials local_result baseline_result scope test_state reference_status authority')
            item = proposal(state,link['proposal_id'])
            if link['test_state'] not in ('LOCAL_CAPABILITY_DEMONSTRATED','LOCAL_GAP_EVIDENCED') or link['reference_status'] != 'UNVERSIONED_UNVERIFIED' or link['authority'] != 'NONE' or link['binding_sha256'] != digest(item.get('binding')) or link['challenge_id'] != item['challenge_id']:
                raise ScanError('Invalid stored scoped receipt')
            for key in ('receipt_sha256','candidate_tree_digest','baseline_tree_digest'): catalog.hash_value(link[key])
            evaluation = catalog.challenge(state,link['challenge_id'])['evaluation']
            if (link['baseline_tree_digest'] != item['baseline_tree_digest'] or link['runtime_versions'] != item['binding']['runtime_versions']
                    or link['matched_trials'] != item['binding']['repeats'] or link['scope'] != catalog.challenge(state,link['challenge_id'])['scope']):
                raise ScanError('Stored receipt contract mismatch')
            path = Path(link['receipt_path'])
            if path.exists():
                receipt = read_json(path,catalog.STATE_LIMIT)
                if sha(path.read_bytes()) == link['receipt_sha256']:
                    before = {'baseline':link['baseline_tree_digest'],'candidate':link['candidate_tree_digest']}
                    if (receipt.get('identities_before') != before or receipt.get('identities_after') != before or
                            _metric(receipt.get('checks',{}).get('candidate'),evaluation,item['binding']) != link['local_result'] or
                            _metric(receipt.get('checks',{}).get('baseline'),evaluation,item['binding']) != link['baseline_result']):
                        raise ScanError('Stored metrics do not match bound receipt')
                    value, threshold = link['local_result']['value'],evaluation['threshold']
                    passed = {'>=':value >= threshold,'<=':value <= threshold,'==':value == threshold}[evaluation['comparator']]
                    if link['test_state'] != ('LOCAL_CAPABILITY_DEMONSTRATED' if passed else 'LOCAL_GAP_EVIDENCED'):
                        raise ScanError('Stored metric status mismatch')
        elif link['kind'] == 'COMPARISON':
            catalog.exact(link,'kind proposal_id challenge_id reference receipt_path receipt_sha256 local_receipt_sha256 candidate_tree_digest binding_sha256 status scope authority')
            item = proposal(state,link['proposal_id'])
            if link['status'] != 'COMPARATIVE_RESULT_VERIFIED' or link['authority'] != 'NONE' or link['binding_sha256'] != digest(item['binding']) or link['challenge_id'] != item['challenge_id']:
                raise ScanError('Invalid stored comparative record')
            catalog.hash_value(link['receipt_sha256'])
            if not any(r.get('receipt_sha256') == link['local_receipt_sha256'] and r.get('candidate_tree_digest') == link['candidate_tree_digest'] for r in state['receipt_links'] if r.get('kind') == 'EXPERIMENT'):
                raise ScanError('Comparative record missing matching local run')
            reference = link['reference']
            catalog.exact(reference,'schema target_id source_url revision license tree_digest')
            if reference['schema'] != 'mantle.chase.pinned-reference/2' or reference['revision'] == 'UNVERIFIED' or reference['target_id'] != catalog.challenge(state,item['challenge_id'])['target_id']:
                raise ScanError('Invalid stored pinned reference')
            catalog.url(reference['source_url']); catalog.hash_value(reference['tree_digest'])
            for key in ('revision','license'): catalog.text(reference[key],256)
            path = Path(link['receipt_path'])
            if path.exists():
                receipt = read_json(path,catalog.STATE_LIMIT)
                if sha(path.read_bytes()) == link['receipt_sha256']:
                    expected = {'baseline':reference['tree_digest'],'candidate':link['candidate_tree_digest']}
                    spec = {k:item['binding'][k] for k in ('check','measure','repeats','timeout_seconds','total_seconds','minimum_improvement_percent','compare_stdout')}
                    if receipt.get('identities_before') != expected or receipt.get('identities_after') != expected or receipt.get('specification') != spec or receipt.get('status') not in ('VERIFIED_WITHIN_DECLARED_CHECK_SCOPE','NO_SUPPORTED_IMPROVEMENT'):
                        raise ScanError('Stored comparative receipt contract mismatch')
                    evaluation = catalog.challenge(state,item['challenge_id'])['evaluation']
                    results = [_metric(receipt.get('checks',{}).get(k),evaluation,item['binding']) for k in ('baseline','candidate')]
                    if results[0] != results[1]: raise ScanError('Stored comparative oracle mismatch')
        else:
            catalog.exact(link,'kind target_id url retrieved_at content_sha256 declared_revision license content_text status')
            catalog.url(link['url']); catalog.utc(link['retrieved_at']); catalog.hash_value(link['content_sha256'])
            if link['status'] != 'UNVERIFIED' or sha(link['content_text'].encode('utf-8')) != link['content_sha256']:
                raise ScanError('Invalid cached reference identity/status')
    nonces = set()
    for item in state['reviews']:
        catalog.exact(item,'schema proposal_id candidate_tree_digest receipt_digest scope approver expires_at nonce decision rollback_note status automatic_promotion')
        if item['automatic_promotion'] is not False or item['status'] not in ('APPROVED_FOR_MANUAL_INTEGRATION','REJECTED') or item['nonce'] in nonces:
            raise ScanError('Invalid stored manual review')
        proposal(state,item['proposal_id']); catalog.utc(item['expires_at'])
        nonces.add(item['nonce'])
    for item in state['proposals']:
        if item['status'] in ('VALIDATED_WITHIN_SCOPE','APPROVED_FOR_MANUAL_INTEGRATION') and not any(r.get('proposal_id') == item['proposal_id'] and r.get('test_state') == 'LOCAL_CAPABILITY_DEMONSTRATED' for r in state['receipt_links']):
            raise ScanError('Validated proposal missing local experiment evidence')
        if item['status'] == 'APPROVED_FOR_MANUAL_INTEGRATION' and not any(r['proposal_id'] == item['proposal_id'] and r['status'] == item['status'] for r in state['reviews']):
            raise ScanError('Manual integration status missing review')


def learning_summary(workspace, *, body=None):
    state = catalog.list_catalog(workspace,body=body)
    rows = [{'proposal_id':p['proposal_id'],'challenge_id':p['challenge_id'],'status':p['status']} for p in state['proposals']]
    next_challenges = [c['challenge_id'] for c in state['challenges'] if not any(
        r.get('challenge_id') == c['challenge_id'] and r.get('test_state') == 'LOCAL_CAPABILITY_DEMONSTRATED' for r in state['receipt_links'])]
    result = {'schema':'mantle.chase.learning/2','revision':state['revision'], 'state_digest':digest(state),
              'results':rows[:32], 'omitted_results':max(0,len(rows)-32),'next_challenges':next_challenges[:32],
              'receipt_digests':[r['receipt_sha256'] for r in state['receipt_links'] if r['kind'] == 'EXPERIMENT'][-32:],
              'authority':'NONE','memory_admission':'Separate memory.engram checked action with explicit operator consent'}
    if len(catalog.canonical(result)) > 12000: raise ScanError('Learning summary budget exceeded')
    return result


def admit_learning(workspace, body, *, expected_head, expected_revision, broker=None):
    """Explicit host operation using memory.admit and the transactional commit path.

    This is intentionally absent from diagnostic/native catalog commands. The
    host must independently obtain consent and supply its broker at invocation.
    """
    from .. import lifecycle, organs
    from ..effects import Capability, CapabilityRegistry, CheckedActionExecutor
    from ..transactions import body_lock
    summary = learning_summary(workspace,body=body)
    catalog.revision(expected_revision)
    if summary['revision'] != expected_revision: raise ScanError('Stale learning revision')
    if not callable(broker): raise ScanError('Explicit host memory admission broker required')
    with body_lock(body):
        existing = organs.system_registry(Path(body)).capability_registry().get('memory.engram')
        registry = CapabilityRegistry()
        registry.register(Capability(name='memory.engram',effect='MUTATE',
            provider=lambda args:lifecycle.admit(body,'memory',{'text':catalog.canonical(args),'evidence':'REPORTED'},expected_head=expected_head),
            verifier=lambda result:isinstance(result,dict) and 'ledger_head' in result,
            authority=existing.authority,provider_id=existing.provider_id))
        result = CheckedActionExecutor(registry,broker).execute('memory.engram',summary,request_id=summary['state_digest'])
        if result['stage'] != 'VERIFIED': raise ScanError('Learning admission denied or stale: ' + str(result['trace'][-1]))
        return result
