"""Verified, portable summaries of source, trace, evidence and candidate gates."""
import html
from .common import ScanError, canonical, digest
from .evidence import context, verify_evidence
from .investigator import _report, verify_trace
from .observations import snapshot_check

SCOPE = "Artifact consistency within declared scope; no automatic semantic acceptance, promotion or release authority"


def build(report, source, receipts, *, feature_trace=None, specification=None, contract=None, expected_contract_sha256=None,
          candidate=None, conformance=None, runtime_receipts=None, authorized_runs=None):
    graph = _report(report)
    if not isinstance(receipts, list) or not 1 <= len(receipts) <= 64 or len({item["id"] for item in receipts}) != len(receipts):
        raise ScanError("Dossier needs 1-64 distinct evidence envelopes")
    snapshot_check(report, source)
    verdicts = [verify_evidence(item, report, source, runtime_receipts=runtime_receipts, authorized_runs=authorized_runs) for item in receipts]
    artifacts = [{"kind": "source-report", "digest": digest(report), "identity": report["graph_digest"],
                  "status": "STATIC_SCOPE_ONLY", "scope": "Current hashed source references; coverage gaps remain explicit"}]
    for receipt, verdict in zip(receipts, verdicts):
        artifacts.append({"kind": "evidence", "digest": digest(receipt), "identity": receipt["id"],
                          "status": receipt["evidence_class"], "scope": verdict["scope"]})
    if feature_trace is not None:
        verify_trace(feature_trace, report)
        artifacts.append({"kind": "feature-trace", "digest": digest(feature_trace), "identity": "trace:" + digest(feature_trace),
                          "status": "POSSIBLE_STATIC_PATHS", "scope": "Possible static relationships; no runtime causality"})
    blueprint = None
    if specification is not None:
        from ..anchor_qualification import verify_specification
        verify_specification(specification, report, source, receipts, contract, expected_contract_sha256=expected_contract_sha256,
                             runtime_receipts=runtime_receipts, authorized_runs=authorized_runs)
        blueprint = {key: specification["blueprint"][key] for key in ("id", "name", "purpose", "status")}
        artifacts.extend([
            {"kind": "specification", "digest": digest(specification), "identity": specification["sha256"], "status": "CANDIDATE_ONLY",
             "scope": "Evidence-linked DRAFT; independent semantic critique and human review required"},
            {"kind": "behavior-contract", "digest": digest(contract), "identity": expected_contract_sha256, "status": "PRESELECTED_ORACLE",
             "scope": "Operator-trusted literal fixtures; digest alone does not establish independent origin"}])
    elif contract is not None or expected_contract_sha256 is not None:
        raise ScanError("Contract inputs require an evidence-bound specification")
    qualification = None
    if conformance is not None or candidate is not None:
        if specification is None or conformance is None or not isinstance(candidate, str):
            raise ScanError("Conformance dossier requires specification, candidate and conformance together")
        from ..anchor_qualification import verify_conformance
        verdict = verify_conformance(conformance, candidate, contract, expected_contract_sha256=expected_contract_sha256)
        if conformance["specification_sha256"] != specification["sha256"]:
            raise ScanError("Conformance does not bind this specification")
        qualification = {"status": conformance["status"], "conformance_passed": verdict["conformance_passed"],
                         "run_authenticity": "NOT_ESTABLISHED_BY_DOSSIER", "human_review": "REQUIRED", "promotion": "NOT_PERFORMED"}
        artifacts.append({"kind": "conformance", "digest": digest(conformance), "identity": conformance["sha256"],
                          "status": conformance["status"], "scope": "Declared fixture comparisons; separately trusted run and human review required"})
    body = {"schema": "scan.dossier/1", "context": context(report), "scope": SCOPE,
            "source": {"root": context(report)["source_root"], "files": len(graph["files"]), "nodes": len(graph["nodes"]), "edges": len(graph["edges"]),
                       "inventory_complete_within_exclusions": graph["scope"].get("inventory_exhausted_within_exclusions") is True,
                       "unhashed_files": sum(item.get("sha256") is None for item in graph["files"]), "coverage_gaps": graph["gaps"]},
            "artifacts": artifacts, "blueprint": blueprint, "qualification": qualification,
            "uncertainty": ["External provider narratives retain UNKNOWN authority.", "Static paths do not prove runtime causality.",
                            "Receipt consistency does not establish provider authenticity or behavioral equivalence.",
                            "Passing declared fixtures still requires independent semantic critique and human program review."],
            "promotion_authority": False, "release_authority": False}
    if len(canonical(body).encode("utf-8")) > 8_000_000: raise ScanError("Dossier byte budget exceeded")
    return dict(body, sha256=digest(body))


def render(value):
    """Inert offline HTML, with no scripts, network assets or provider-generated links."""
    if value.get("schema") != "scan.dossier/1" or value.get("sha256") != digest({key: item for key, item in value.items() if key != "sha256"}):
        raise ScanError("Dossier identity mismatch")
    if value.get("promotion_authority") is not False or value.get("release_authority") is not False or value.get("scope") != SCOPE:
        raise ScanError("Dossier cannot grant promotion or release authority")
    if value.get("blueprint") is not None and value["blueprint"].get("status") != "DRAFT":
        raise ScanError("Dossier proposal must remain DRAFT")
    escape = lambda item: html.escape(str(item), quote=True)
    rows = "".join("<tr><td>" + "</td><td>".join(escape(row[key]) for key in ("kind", "status", "identity", "scope")) + "</td></tr>" for row in value["artifacts"])
    uncertainty = "".join("<li>" + escape(item) + "</li>" for item in value["uncertainty"])
    panels = "".join("<section><h2>" + title + "</h2><pre>" + escape(canonical(value[key])) + "</pre></section>" for key, title in
                     (("source", "Source coverage"), ("blueprint", "Blueprint proposal"), ("qualification", "Declared fixture verdict")))
    return ("<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'\">"
            "<title>MantleOS evidence dossier</title><style>body{font:16px/1.55 system-ui;margin:0;background:#f2f6f5;color:#17313d}"
            "header{background:#14323d;color:#f2fffa;padding:30px}main{max-width:1200px;margin:auto;padding:24px}"
            "section{background:white;border:1px solid #ccdcd8;border-radius:12px;padding:18px;margin:18px 0}"
            "table{border-collapse:collapse;width:100%}th,td{padding:12px;text-align:left;border-bottom:1px solid #dde7e4;vertical-align:top;overflow-wrap:anywhere}"
            "pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}code{overflow-wrap:anywhere}.table{overflow:auto}h1{margin:0}</style>"
            "<header><h1>MantleOS evidence dossier</h1><p>Source → possible feature paths → evidence → DRAFT Blueprint → declared fixtures</p>"
            "<p>Independent review remains required. Promotion and release authority: none.</p></header><main><p>Context <code>"
            + escape(value["context"]["id"]) + "</code></p><section><h2>Artifact gates</h2><div class='table'><table>"
            "<thead><tr><th>Artifact</th><th>Status</th><th>Identity</th><th>What was checked</th></tr></thead><tbody>" + rows +
            "</tbody></table></div></section>" + panels + "<section><h2>Uncertainty and review</h2><ul>" + uncertainty +
            "</ul><p>" + escape(SCOPE) + "</p></section><p>Dossier SHA-256 <code>" + escape(value["sha256"]) + "</code></p></main></html>")
