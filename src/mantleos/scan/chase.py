"""A reference is a proposed target until a local comparison demonstrates it."""
from pathlib import Path
from .common import ScanError, digest, read_json, write_json


def targets(workspace):
    path = Path(workspace) / "chase-targets.json"
    return read_json(path) if path.exists() else []


def add_target(workspace, record):
    for key in ("name", "quality", "reference", "environment", "acceptance_check"):
        if not isinstance(record.get(key), str) or not record[key].strip():
            raise ScanError("Chase record needs name, quality, reference, environment and acceptance_check strings")
    # Incoming claims never grant verification status. The experiment receipt is separate.
    item = {k: record[k] for k in ("name", "quality", "reference", "environment", "acceptance_check")}
    # Comparable baseline identity is essential for a defensible stopping rule.
    # Legacy, non-pinned targets remain proposals and cannot claim parity.
    if 'reference_digest' in record:
        value=record['reference_digest']
        if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):
            raise ScanError('Reference digest must be a lowercase SHA-256 tree identity')
        item['reference_digest']=value
    ratio=record.get('max_latency_ratio',1.05)
    if type(ratio) not in (float,int) or not 0<ratio<=2:
        raise ScanError('Chase latency ratio must be >0 and <=2')
    item['max_latency_ratio']=ratio
    item.update(id=digest(item)[:24], status="PROPOSED_TARGET", local_feasibility="UNVERIFIED")
    entries = targets(workspace)
    if not any(e["id"] == item["id"] for e in entries): entries.append(item)
    write_json(Path(workspace) / "chase-targets.json", entries)
    return item


def qualify(workspace, target_id, receipt_path):
    receipt = read_json(receipt_path)
    if receipt.get("schema") != "scan.experiment/1" or receipt.get("status") != "VERIFIED_WITHIN_DECLARED_CHECK_SCOPE":
        raise ScanError("Qualification needs a successful local experiment receipt")
    entries = targets(workspace)
    selected = next((e for e in entries if e["id"] == target_id), None)
    if selected is None: raise ScanError("Unknown Chase target")
    selected.update(status="LOCAL_EXPERIMENT_ATTACHED", local_feasibility="SUPPORTED_ONLY_FOR_RECEIPT_CHECK_SCOPE",
                    receipt_digest=digest(receipt), receipt=str(Path(receipt_path).resolve()),
                    caution="The user must establish that this experiment measures the named quality under comparable conditions. Receipts are local evidence, not signed attestations.")
    write_json(Path(workspace) / "chase-targets.json", entries)
    return selected


def assess(workspace,target_id,receipt_path):
    """Scoped allostatic stop/redirect gate; not autonomous code rewriting.

    A target is 'reached' only against a pinned reference tree, with identical
    outputs and passing checks on both sides of the local experiment. A later
    baseline mutation or new external target requires a new evaluation.
    """
    receipt=read_json(receipt_path)
    entries=targets(workspace)
    selected=next((e for e in entries if e['id']==target_id),None)
    if selected is None:raise ScanError('Unknown Chase target')
    if receipt.get('schema')!='scan.experiment/1':raise ScanError('Not a SCAN experiment receipt')
    before=receipt.get('identities_before',{})
    if not selected.get('reference_digest') or before.get('baseline')!=selected['reference_digest']:
        raise ScanError('Chase target must pin the exact reference tree measured in the receipt')
    if receipt.get('identities_after')!=before:
        raise ScanError('Source changed during Chase experiment')
    spec=receipt.get('specification',{})
    if spec.get('compare_stdout',True) is not True:
        raise ScanError('Chase parity requires output comparison')
    if receipt.get('status') not in {'VERIFIED_WITHIN_DECLARED_CHECK_SCOPE','NO_SUPPORTED_IMPROVEMENT'}:
        raise ScanError('Experiment check/measurement did not complete safely')
    trials=[r for r in receipt.get('trials',[]) if not r.get('warmup')]
    checks=receipt.get('checks',{})
    def passes(run):return (isinstance(run,dict) and run.get('status')=='COMPLETED'
                           and run.get('exit_code')==0 and run.get('truncated') is False)
    if not trials or not all(passes(checks.get(k)) for k in ('baseline','candidate')):
        raise ScanError('Missing successful reference/candidate check')
    if not all(passes(row.get(k)) for row in trials for k in ('baseline','candidate')):
        raise ScanError('Missing successful paired trial')
    if not all(row['baseline']['stdout_sha256']==row['candidate']['stdout_sha256'] for row in trials):
        raise ScanError('Chase output mismatch; cannot declare target reached')
    result=receipt.get('measurement',{})
    reference_seconds=result.get('baseline_median_seconds')
    candidate_seconds=result.get('candidate_median_seconds')
    if (type(reference_seconds) not in (float,int) or reference_seconds<=0 or
        type(candidate_seconds) not in (float,int) or candidate_seconds<0):
        raise ScanError('Missing valid matched performance measurement')
    latency_ratio=candidate_seconds/reference_seconds
    reached=latency_ratio<=selected['max_latency_ratio']
    selected.update(status='TARGET_REACHED_WITHIN_CHECK_SCOPE' if reached else 'CHASE_ACTIVE',
                    next_priority='OTHER_UNMET_TARGET' if reached else 'THIS_TARGET',
                    observed_latency_ratio=round(latency_ratio,6),
                    receipt_digest=digest(receipt),receipt=str(Path(receipt_path).resolve()),
                    scope='Performance and output parity ONLY for pinned tree and declared checks; no global behavioral equivalence')
    write_json(Path(workspace)/'chase-targets.json',entries)
    return selected
