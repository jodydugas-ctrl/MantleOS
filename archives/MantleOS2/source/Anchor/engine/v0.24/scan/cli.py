from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3

from .engine import ScanEngine
from .inventory import DEFAULT_MAX_FILE_BYTES
from .acquire_github import DEFAULT_MAX_BLOB_BYTES, GitHubAcquirer
from .evidence_graph import (
    export_completeness,
    export_evidence_catalog,
    export_evidence_graph,
    refresh_machine_body_map_projection,
    ingest_overlay,
    load_overlay,
    trace_impact,
    trace_why,
)
from .store import Store
from .integrity import audit_integrity, effect_closure, refresh_refinement_completeness, surface_closure, write_integrity_outputs, write_projection_manifest
from .capabilities import write_nest_capability_map
from .reconstruction import (
    export_reconstruction_contract, load_reconstruction_proposal, promote_reconstruction_proposal,
    validate_reconstruction_proposal,
)


from .reconstruction_trial import (
    prepare_reconstruction_trial, score_reconstruction_trial, verify_reconstruction_trial,
)

from .queries import QUERY_SQL
from .release import (certify_manifest, certify_reconstruction_handoff, certify_specimen, qualify_release,
                      verify_certification, verify_package, verify_projection_manifest, write_package_manifest)



def _open_store(db_path: Path, *, readonly: bool = True) -> Store:
    if not db_path.exists():
        raise FileNotFoundError(db_path)
    return Store(db_path, readonly=readonly)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="scan-body", description="SCAN evidence-first software anatomy scanner")
    sub = parser.add_subparsers(dest="command", required=True)
    p_scan = sub.add_parser("scan", help="mechanically scan a local specimen")
    p_scan.add_argument("root", type=Path)
    p_scan.add_argument("--out", type=Path, default=Path(".scan"))
    p_scan.add_argument("--specimen-id", default=None)
    p_scan.add_argument("--max-file-bytes", type=int, default=DEFAULT_MAX_FILE_BYTES,
                        help="maximum bytes read from one local specimen file; 0 disables the limit")
    p_scan.add_argument("--max-total-bytes", type=int, default=0, help="aggregate specimen bytes eligible for materialization; 0 disables")
    p_scan.add_argument("--max-materialized-files", type=int, default=0, help="aggregate parser-eligible file count; 0 disables")
    p_scan.add_argument("--max-extraction-seconds", type=float, default=0.0, help="mechanical extraction time ceiling checked at safe boundaries; 0 disables")
    p_scan.add_argument("--max-nodes", type=int, default=0, help="maximum committed structural nodes; 0 disables")
    p_scan.add_argument("--max-edges", type=int, default=0, help="maximum committed structural edges; 0 disables")
    p_scan.add_argument("--max-evidence", type=int, default=0, help="maximum committed evidence records; 0 disables")

    p_manifest = sub.add_parser("scan-manifest", help="scan a source manifest; parse only materialized bytes")
    p_manifest.add_argument("manifest", type=Path)
    p_manifest.add_argument("--content-root", type=Path, default=None,
                            help="optional scanner-owned directory containing materialized files matching manifest paths")
    p_manifest.add_argument("--out", type=Path, default=Path(".scan"))
    p_manifest.add_argument("--specimen-id", default=None)
    p_manifest.add_argument("--max-file-bytes", type=int, default=DEFAULT_MAX_FILE_BYTES,
                            help="maximum bytes read from one materialized manifest file; 0 disables the limit")
    p_manifest.add_argument("--max-total-bytes", type=int, default=0, help="aggregate materialized manifest bytes; 0 disables")
    p_manifest.add_argument("--max-materialized-files", type=int, default=0, help="aggregate parser-eligible file count; 0 disables")
    p_manifest.add_argument("--max-extraction-seconds", type=float, default=0.0, help="mechanical extraction time ceiling checked at safe boundaries; 0 disables")
    p_manifest.add_argument("--max-nodes", type=int, default=0, help="maximum committed structural nodes; 0 disables")
    p_manifest.add_argument("--max-edges", type=int, default=0, help="maximum committed structural edges; 0 disables")
    p_manifest.add_argument("--max-evidence", type=int, default=0, help="maximum committed evidence records; 0 disables")

    p_acquire = sub.add_parser("acquire-github", help="acquire an exact GitHub revision into scanner-owned storage")
    p_acquire.add_argument("repository", help="GitHub repository in owner/name form")
    p_acquire.add_argument("--ref", required=True, help="exact commit/tag/ref to resolve; never defaults to a moving branch")
    p_acquire.add_argument("--out", type=Path, required=True, help="scanner-owned acquisition directory")
    p_acquire.add_argument("--token-env", default="GITHUB_TOKEN", help="environment variable containing an optional GitHub token")
    p_acquire.add_argument("--workers", type=int, default=6)
    p_acquire.add_argument("--strict", action="store_true", help="fail command if any provider blob cannot be acquired")
    p_acquire.add_argument("--max-blob-bytes", type=int, default=DEFAULT_MAX_BLOB_BYTES,
                           help="maximum bytes materialized for one provider blob; 0 disables the limit")

    p_query = sub.add_parser("query", help="run a predefined mechanical query against a SCAN SQLite index")
    p_query.add_argument("db", type=Path)
    p_query.add_argument("query", choices=sorted(QUERY_SQL))
    p_query.add_argument("--limit", type=int, default=100)

    p_overlay = sub.add_parser("ingest-knowledge", help="ingest a data-only semantic overlay of behaviors/interpretations/anchors")
    p_overlay.add_argument("db", type=Path)
    p_overlay.add_argument("overlay", type=Path)
    p_overlay.add_argument("--out-dir", type=Path, default=None,
                           help="optional directory whose evidence/projection JSON should be refreshed")

    p_validate_recon = sub.add_parser("validate-reconstruction", help="validate a reconstruction proposal without mutating the canonical graph")
    p_validate_recon.add_argument("db", type=Path)
    p_validate_recon.add_argument("proposal", type=Path)
    p_validate_recon.add_argument("--out", type=Path, default=None)

    p_promote_recon = sub.add_parser("promote-reconstruction", help="mechanically gate and promote an evidence-backed reconstruction proposal")
    p_promote_recon.add_argument("db", type=Path)
    p_promote_recon.add_argument("proposal", type=Path)
    p_promote_recon.add_argument("--out-dir", type=Path, required=True, help="scan output directory whose canonical projections will be refreshed")

    p_export_recon = sub.add_parser("reconstruction-contract", help="export reconstruction-ready anchors/behavior contracts from the canonical graph")
    p_export_recon.add_argument("db", type=Path)
    p_export_recon.add_argument("--out", type=Path, required=True)

    p_why = sub.add_parser("why", help="walk backward from a semantic claim/anchor to its supporting evidence")
    p_why.add_argument("db", type=Path)
    p_why.add_argument("object_id")
    p_why.add_argument("--depth", type=int, default=8)

    p_impact = sub.add_parser("impact", help="walk forward from evidence/source to dependent claims and anchors")
    p_impact.add_argument("db", type=Path)
    p_impact.add_argument("object_id")
    p_impact.add_argument("--depth", type=int, default=8)

    p_obj = sub.add_parser("object", help="show one semantic object and its incoming/outgoing relations")
    p_obj.add_argument("db", type=Path)
    p_obj.add_argument("object_id")

    p_audit = sub.add_parser("audit", help="audit evidence-graph integrity and proof-chain health")
    p_audit.add_argument("db", type=Path)
    p_audit.add_argument("--depth", type=int, default=12)
    p_audit.add_argument("--out", type=Path, default=None)
    p_audit.add_argument("--strict", action="store_true", help="return non-zero when integrity ERROR issues exist")

    p_closure = sub.add_parser("closure", help="measure mechanical human-surface binding closure")
    p_closure.add_argument("db", type=Path)
    p_closure.add_argument("--out", type=Path, default=None)

    p_deep = sub.add_parser("deep-closure", help="trace surfaces through handlers/calls to state/effect/NEST/feedback terminals")
    p_deep.add_argument("db", type=Path)
    p_deep.add_argument("--depth", type=int, default=12)
    p_deep.add_argument("--out", type=Path, default=None)

    p_self = sub.add_parser("self-audit", help="verify packaged bytes and optionally one emitted scan package")
    p_self.add_argument("package_root", type=Path)
    p_self.add_argument("--scan-output", type=Path, default=None)
    p_self.add_argument("--out", type=Path, default=None)

    p_qualify = sub.add_parser("qualify", help="run the packaged LLM-disabled mechanical release qualification")
    p_qualify.add_argument("package_root", type=Path)
    p_qualify.add_argument("--out", type=Path, default=None)

    p_certify = sub.add_parser("certify", help="scan and seal one local specimen as an agent-verifiable evidence handoff")
    p_certify.add_argument("package_root", type=Path, help="extracted SCAN release tree whose package manifest must verify")
    p_certify.add_argument("specimen_root", type=Path, help="local read-only specimen directory")
    p_certify.add_argument("--out", type=Path, required=True, help="certification directory; contains scan/, receipt, and manifest")
    p_certify.add_argument("--bundle", type=Path, default=None, help="optional deterministic ZIP handoff path")
    p_certify.add_argument("--specimen-id", default=None)
    p_certify.add_argument("--max-file-bytes", type=int, default=DEFAULT_MAX_FILE_BYTES)
    p_certify.add_argument("--max-total-bytes", type=int, default=0)
    p_certify.add_argument("--max-materialized-files", type=int, default=0)
    p_certify.add_argument("--max-extraction-seconds", type=float, default=0.0)
    p_certify.add_argument("--max-nodes", type=int, default=0)
    p_certify.add_argument("--max-edges", type=int, default=0)
    p_certify.add_argument("--max-evidence", type=int, default=0)

    p_certify_manifest = sub.add_parser("certify-manifest", help="scan and seal a provider/source manifest while preserving acquisition provenance")
    p_certify_manifest.add_argument("package_root", type=Path)
    p_certify_manifest.add_argument("manifest", type=Path)
    p_certify_manifest.add_argument("--content-root", type=Path, default=None)
    p_certify_manifest.add_argument("--out", type=Path, required=True)
    p_certify_manifest.add_argument("--bundle", type=Path, default=None)
    p_certify_manifest.add_argument("--specimen-id", default=None)
    p_certify_manifest.add_argument("--max-file-bytes", type=int, default=DEFAULT_MAX_FILE_BYTES)
    p_certify_manifest.add_argument("--max-total-bytes", type=int, default=0)
    p_certify_manifest.add_argument("--max-materialized-files", type=int, default=0)
    p_certify_manifest.add_argument("--max-extraction-seconds", type=float, default=0.0)
    p_certify_manifest.add_argument("--max-nodes", type=int, default=0)
    p_certify_manifest.add_argument("--max-edges", type=int, default=0)
    p_certify_manifest.add_argument("--max-evidence", type=int, default=0)

    p_certify_recon = sub.add_parser("certify-reconstruction", help="derive and seal a reconstruction-aware handoff from a verified mechanical certification")
    p_certify_recon.add_argument("package_root", type=Path)
    p_certify_recon.add_argument("source_certification_root", type=Path)
    p_certify_recon.add_argument("proposal", type=Path)
    p_certify_recon.add_argument("--out", type=Path, required=True)
    p_certify_recon.add_argument("--bundle", type=Path, default=None)

    p_verify_cert = sub.add_parser("verify-certification", help="verify a sealed SCAN specimen-certification directory")
    p_verify_cert.add_argument("certification_root", type=Path)
    p_verify_cert.add_argument("--out", type=Path, default=None)

    p_prepare_trial = sub.add_parser("prepare-reconstruction-trial", help="split a verified reconstruction certification into a source-free public challenge and private evaluator")
    p_prepare_trial.add_argument("source_certification_root", type=Path)
    p_prepare_trial.add_argument("--challenge-out", type=Path, required=True)
    p_prepare_trial.add_argument("--evaluator-out", type=Path, required=True)
    p_prepare_trial.add_argument("--challenge-bundle", type=Path, default=None)
    p_prepare_trial.add_argument("--evaluator-bundle", type=Path, default=None)

    p_score_trial = sub.add_parser("score-reconstruction-trial", help="scan and score a source-blind reconstructed candidate against a private evaluator")
    p_score_trial.add_argument("package_root", type=Path)
    p_score_trial.add_argument("evaluator_root", type=Path)
    p_score_trial.add_argument("candidate_root", type=Path)
    p_score_trial.add_argument("submission", type=Path)
    p_score_trial.add_argument("--out", type=Path, required=True)
    p_score_trial.add_argument("--bundle", type=Path, default=None)

    p_verify_trial = sub.add_parser("verify-reconstruction-trial", help="verify a sealed reconstruction trial and candidate scan")
    p_verify_trial.add_argument("trial_root", type=Path)
    p_verify_trial.add_argument("--out", type=Path, default=None)

    p_manifest_build = sub.add_parser("package-manifest", help="regenerate deterministic PACKAGE_MANIFEST.json for a release tree")
    p_manifest_build.add_argument("package_root", type=Path)

    args = parser.parse_args(argv)
    if args.command == "acquire-github":
        import os
        import sys
        token = os.environ.get(args.token_env) if args.token_env else None
        try:
            report = GitHubAcquirer(token=token, max_workers=args.workers,
                                     max_blob_bytes=args.max_blob_bytes).acquire(
                args.repository, args.ref, args.out, strict=args.strict
            )
        except (RuntimeError, ValueError, OSError) as exc:
            failure = {
                "success": False,
                "stage": "ACQUIRE",
                "provider": "github",
                "repository": args.repository,
                "requested_ref": args.ref,
                "acquisition_state": "BLOCKED",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "output": str(args.out.resolve()),
            }
            print(json.dumps(failure, indent=2), file=sys.stderr)
            return 2
        print(json.dumps(report, indent=2))
        return 0

    if args.command == "package-manifest":
        result = write_package_manifest(args.package_root)
        print(json.dumps({"state": "PASS", "engine_version": result["engine_version"], "file_count": len(result["files"]), "manifest": str((args.package_root / "PACKAGE_MANIFEST.json").resolve())}, indent=2))
        return 0
    if args.command == "self-audit":
        result = {"package": verify_package(args.package_root)}
        if args.scan_output is not None:
            result["scan_output"] = verify_projection_manifest(args.scan_output)
        result["state"] = "PASS" if all(v.get("state") == "PASS" for k, v in result.items() if k != "state") else "FAIL"
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 0 if result["state"] == "PASS" else 5
    if args.command == "qualify":
        result = qualify_release(args.package_root, output_path=args.out)
        print(json.dumps(result, indent=2))
        return 0 if result["state"] == "PASS" else 6
    if args.command == "certify":
        result = certify_specimen(
            args.package_root, args.specimen_root, args.out, specimen_id=args.specimen_id,
            max_file_bytes=args.max_file_bytes, max_total_bytes=args.max_total_bytes,
            max_materialized_files=args.max_materialized_files, max_extraction_seconds=args.max_extraction_seconds,
            max_nodes=args.max_nodes, max_edges=args.max_edges, max_evidence=args.max_evidence,
            bundle_path=args.bundle,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["state"] == "PASS" else 7
    if args.command == "certify-manifest":
        result = certify_manifest(
            args.package_root, args.manifest, args.out, content_root=args.content_root,
            specimen_id=args.specimen_id, max_file_bytes=args.max_file_bytes,
            max_total_bytes=args.max_total_bytes, max_materialized_files=args.max_materialized_files,
            max_extraction_seconds=args.max_extraction_seconds, max_nodes=args.max_nodes,
            max_edges=args.max_edges, max_evidence=args.max_evidence, bundle_path=args.bundle,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["state"] == "PASS" else 7
    if args.command == "certify-reconstruction":
        result = certify_reconstruction_handoff(
            args.package_root, args.source_certification_root, args.proposal, args.out,
            bundle_path=args.bundle,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get("state") == "PASS" else 5
    if args.command == "verify-certification":
        result = verify_certification(args.certification_root)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 0 if result["state"] == "PASS" else 8
    if args.command == "prepare-reconstruction-trial":
        result = prepare_reconstruction_trial(
            args.source_certification_root, args.challenge_out, args.evaluator_out,
            challenge_bundle=args.challenge_bundle, evaluator_bundle=args.evaluator_bundle,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get("state") == "PASS" else 9
    if args.command == "score-reconstruction-trial":
        result = score_reconstruction_trial(
            args.package_root, args.evaluator_root, args.candidate_root, args.submission,
            args.out, bundle_path=args.bundle,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get("state") in {"PASS", "PARTIAL"} else 10
    if args.command == "verify-reconstruction-trial":
        result = verify_reconstruction_trial(args.trial_root)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get("state") == "PASS" else 11

    if args.command == "scan":
        summary = ScanEngine(
            max_file_bytes=args.max_file_bytes, max_total_bytes=args.max_total_bytes,
            max_materialized_files=args.max_materialized_files, max_extraction_seconds=args.max_extraction_seconds,
            max_nodes=args.max_nodes, max_edges=args.max_edges, max_evidence=args.max_evidence,
        ).scan(args.root, args.out, args.specimen_id)
    elif args.command == "scan-manifest":
        summary = ScanEngine(
            max_file_bytes=args.max_file_bytes, max_total_bytes=args.max_total_bytes,
            max_materialized_files=args.max_materialized_files, max_extraction_seconds=args.max_extraction_seconds,
            max_nodes=args.max_nodes, max_edges=args.max_edges, max_evidence=args.max_evidence,
        ).scan_manifest(args.manifest, args.out, args.content_root, args.specimen_id)
    elif args.command == "query":
        path = args.db.resolve(strict=True)
        db = sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)
        try:
            db.row_factory = sqlite3.Row
            sql = QUERY_SQL[args.query] + " LIMIT ?"
            rows = [dict(r) for r in db.execute(sql, (args.limit,)).fetchall()]
        finally:
            db.close()
        print(json.dumps(rows, indent=2))
        return 0
    elif args.command == "ingest-knowledge":
        store = _open_store(args.db, readonly=False)
        payload = load_overlay(args.overlay)
        result = ingest_overlay(store, payload)
        refinement = refresh_refinement_completeness(store)
        result["refinement"] = {
            "integrity_state": refinement["integrity"].get("state"),
            "integrity_issue_count": refinement["integrity"].get("issue_count", 0),
            "surface_closure_state": refinement["surface_closure"].get("state"),
            "effect_closure_state": refinement["effect_closure"].get("state"),
            "updated_dimensions": refinement.get("updated_dimensions", []),
        }
        if args.out_dir:
            args.out_dir.mkdir(parents=True, exist_ok=True)
            # Specimen identity is already preserved by the base graph; use a compact pointer here.
            specimen_objects = [x for x in store.semantic_objects() if x["object_type"] == "SPECIMEN"]
            specimen = specimen_objects[0]["attributes"] if specimen_objects else {}
            export_evidence_graph(store, specimen, args.out_dir / "evidence_graph.json")
            export_evidence_catalog(store, args.out_dir / "evidence_catalog.json")
            export_completeness(store, args.out_dir / "completeness_vector.json")
            write_integrity_outputs(store, args.out_dir)
            write_nest_capability_map(store, args.out_dir / "nest_capability_map.json")
            refresh_machine_body_map_projection(store, args.out_dir / "machine_body_map.json")
            write_projection_manifest(args.out_dir, [
                "machine_body_map.json", "evidence_graph.json", "evidence_catalog.json",
                "completeness_vector.json", "integrity_report.json", "surface_closure.json", "effect_closure.json", "nest_capability_map.json", "stage1_summary.md",
            ])
        store.close()
        print(json.dumps(result, indent=2))
        return 0
    elif args.command == "validate-reconstruction":
        store = _open_store(args.db)
        try:
            payload = load_reconstruction_proposal(args.proposal)
            result = validate_reconstruction_proposal(store, payload)
        finally:
            store.close()
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get("state") == "PASS" else 5
    elif args.command == "promote-reconstruction":
        store = _open_store(args.db, readonly=False)
        try:
            payload = load_reconstruction_proposal(args.proposal)
            args.out_dir.mkdir(parents=True, exist_ok=True)
            contract_path = args.out_dir / "reconstruction_contract.json"
            result = promote_reconstruction_proposal(store, payload, contract_path=contract_path)
            if result.get("state") == "PROMOTED":
                specimen_objects = [x for x in store.semantic_objects() if x["object_type"] == "SPECIMEN"]
                specimen = specimen_objects[0]["attributes"] if specimen_objects else {}
                export_evidence_graph(store, specimen, args.out_dir / "evidence_graph.json")
                export_evidence_catalog(store, args.out_dir / "evidence_catalog.json")
                export_completeness(store, args.out_dir / "completeness_vector.json")
                write_integrity_outputs(store, args.out_dir)
                write_nest_capability_map(store, args.out_dir / "nest_capability_map.json")
                refresh_machine_body_map_projection(store, args.out_dir / "machine_body_map.json")
                write_projection_manifest(args.out_dir, [
                    "machine_body_map.json", "evidence_graph.json", "evidence_catalog.json",
                    "completeness_vector.json", "integrity_report.json", "surface_closure.json",
                    "effect_closure.json", "nest_capability_map.json", "reconstruction_contract.json",
                    "stage1_summary.md",
                ])
        finally:
            store.close()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get("state") == "PROMOTED" else 5
    elif args.command == "reconstruction-contract":
        store = _open_store(args.db)
        try:
            result = export_reconstruction_contract(store, args.out)
        finally:
            store.close()
        print(json.dumps({"state": "PASS", "path": str(args.out), "anchor_count": result["anchor_count"], "behavior_count": result["behavior_count"]}, indent=2))
        return 0
    elif args.command == "why":
        store = _open_store(args.db)
        try:
            result = trace_why(store, args.object_id, args.depth)
        except KeyError:
            store.close()
            print(json.dumps({"error": "object-not-found", "object_id": args.object_id}, indent=2))
            return 3
        store.close()
        print(json.dumps(result, indent=2))
        return 0
    elif args.command == "impact":
        store = _open_store(args.db)
        try:
            result = trace_impact(store, args.object_id, args.depth)
        except KeyError:
            store.close()
            print(json.dumps({"error": "object-not-found", "object_id": args.object_id}, indent=2))
            return 3
        store.close()
        print(json.dumps(result, indent=2))
        return 0
    elif args.command == "object":
        store = _open_store(args.db)
        obj = store.semantic_object(args.object_id)
        if obj is None:
            store.close()
            print(json.dumps({"error": "object-not-found", "object_id": args.object_id}, indent=2))
            return 3
        result = {
            "object": obj,
            "incoming": store.incoming_semantic_relations(args.object_id),
            "outgoing": store.outgoing_semantic_relations(args.object_id),
        }
        store.close()
        print(json.dumps(result, indent=2))
        return 0
    elif args.command == "audit":
        store = _open_store(args.db)
        result = audit_integrity(store, proof_depth=args.depth)
        store.close()
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(result, indent=2))
        if args.strict and result.get("severity_counts", {}).get("ERROR", 0):
            return 4
        return 0
    elif args.command == "closure":
        store = _open_store(args.db)
        result = surface_closure(store)
        store.close()
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 0
    elif args.command == "deep-closure":
        store = _open_store(args.db)
        result = effect_closure(store, max_depth=args.depth)
        store.close()
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 0
    else:
        raise AssertionError(args.command)

    print(json.dumps({
        "file_count": summary["inventory"]["file_count"],
        "materialized_file_count": summary["inventory"]["materialized_file_count"],
        "content_unavailable_file_count": summary["inventory"]["content_unavailable_file_count"],
        "metadata_only_file_count": summary["inventory"]["metadata_only_file_count"],
        "node_count": summary["extraction"]["node_count"],
        "edge_count": summary["extraction"]["edge_count"],
        "evidence_count": summary["extraction"]["evidence_count"],
        "semantic_object_count": summary["semantic_graph"]["objects"],
        "semantic_relation_count": summary["semantic_graph"]["relations"],
        "completeness_dimension_count": summary["semantic_graph"]["completeness_dimensions"],
        "budget": summary.get("budget"),
        "store_recovery": summary.get("store_recovery"),
        "output": str(args.out.resolve()),
    }, indent=2))
    return 0
