from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from . import __version__
from .adapters import DEFAULT_ADAPTERS
from .graph import graph_metrics
from .inventory import DEFAULT_MAX_FILE_BYTES, FileRecord, inventory, inventory_from_manifest, read_verified_local
from .model import ExtractionResult, Finding, stable_id
from .resolution import resolve_cross_file
from .store import Store
from .evidence_graph import (
    export_completeness, export_evidence_catalog, export_evidence_graph, persist_base_graph,
)
from .integrity import refresh_refinement_completeness, write_integrity_outputs, write_projection_manifest
from .capabilities import write_nest_capability_map
from .budget import ScanBudget, BudgetController


class ScanEngine:
    def __init__(self, adapters=None, *, max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
                 max_total_bytes: int = 0, max_materialized_files: int = 0,
                 max_extraction_seconds: float = 0.0, max_nodes: int = 0,
                 max_edges: int = 0, max_evidence: int = 0, cancel_check=None):
        self.adapters = adapters or DEFAULT_ADAPTERS
        self.max_file_bytes = int(max_file_bytes)
        if self.max_file_bytes < 0:
            raise ValueError("max_file_bytes must be >= 0")
        self.budget = ScanBudget(
            max_total_bytes=int(max_total_bytes),
            max_materialized_files=int(max_materialized_files),
            max_extraction_seconds=float(max_extraction_seconds),
            max_nodes=int(max_nodes), max_edges=int(max_edges), max_evidence=int(max_evidence),
        )
        self.budget.validate()
        self.cancel_check = cancel_check

    def scan(self, root: Path, output: Path, specimen_id: str | None = None) -> dict:
        root = Path(root)
        if root.is_symlink():
            raise ValueError(f"scan root must not be a symlink: {root}")
        root = root.resolve(strict=True)
        files = inventory(
            root, excludes={".git", ".scan", "__pycache__", ".pytest_cache", ".mypy_cache"},
            max_file_bytes=self.max_file_bytes, max_total_bytes=self.budget.max_total_bytes,
            max_materialized_files=self.budget.max_materialized_files,
        )
        specimen = {"root": str(root), "specimen_id": specimen_id, "acquisition_mode": "local"}
        return self._scan_records(files, output, specimen, content_root=root)

    def scan_manifest(self, manifest_path: Path, output: Path, content_root: Path | None = None,
                      specimen_id: str | None = None) -> dict:
        manifest_path = manifest_path.resolve(strict=True)
        if content_root and Path(content_root).is_symlink():
            raise ValueError(f"content root must not be a symlink: {content_root}")
        files, manifest_specimen = inventory_from_manifest(
            manifest_path, content_root, max_file_bytes=self.max_file_bytes,
            max_total_bytes=self.budget.max_total_bytes,
            max_materialized_files=self.budget.max_materialized_files,
        )
        revision = str(manifest_specimen.get("revision") or "").strip()
        revision_is_commit = (
            len(revision) in {40, 64}
            and all(char in "0123456789abcdefABCDEF" for char in revision)
        )
        specimen = {
            **manifest_specimen,
            "specimen_id": specimen_id or manifest_specimen.get("specimen_id"),
            "commit_sha": manifest_specimen.get("commit_sha") or (revision.lower() if revision_is_commit else None),
            "manifest": str(manifest_path),
            "content_root": str(content_root.resolve()) if content_root else None,
            "acquisition_mode": "manifest",
        }
        return self._scan_records(files, output, specimen, content_root=content_root.resolve() if content_root else None)

    def _scan_records(self, files: list[FileRecord], output: Path, specimen: dict, content_root: Path | None) -> dict:
        output.mkdir(parents=True, exist_ok=True)
        db_path = output / "scan_index.sqlite"
        store = Store(db_path, recover_corrupt=True)
        store.reset_current_map()
        store.put_files(files)

        combined = ExtractionResult()
        cache_hits = 0
        cache_misses = 0
        adapter_runs = Counter()
        materialized = sum(1 for r in files if r.content_available)
        content_unavailable = sum(1 for r in files if not r.content_available)
        controller = BudgetController(self.budget, cancel_check=self.cancel_check)
        budget_stop_index: int | None = None
        budget_stop_adapter: str | None = None

        for file_index, rec in enumerate(files):
            reason = controller.check_cancel_or_time()
            if reason:
                budget_stop_index = file_index
                break
            if not rec.content_available or rec.is_binary or content_root is None:
                continue
            try:
                data = read_verified_local(content_root, rec.path, rec.sha256, max_file_bytes=self.max_file_bytes)
                text = data.decode("utf-8", errors="replace")
            except (OSError, RuntimeError, ValueError) as exc:
                combined.findings.append(Finding(
                    stable_id("finding", rec.id, "read-failure", type(exc).__name__, str(exc)), "coverage_gap",
                    f"Unable to safely reread {rec.path}", "BLOCKED",
                    {"error": str(exc), "meaning": "source changed, escaped, exceeded limits, or became unsafe after inventory"}, []
                ))
                continue
            for adapter in self.adapters:
                reason = controller.check_cancel_or_time()
                if reason:
                    budget_stop_index = file_index
                    budget_stop_adapter = adapter.name
                    break
                if not adapter.accepts(rec):
                    continue
                if rec.sha256:
                    cache_version = adapter.cache_version(content_root, rec)
                    cached = store.get_cache(rec.sha256, adapter.name, cache_version)
                else:
                    cached = None
                if cached is not None:
                    result = cached
                    cache_hits += 1
                else:
                    try:
                        result = adapter.extract(content_root, rec, text)
                    except MemoryError:
                        # Process-level memory exhaustion is not a local parser condition; do not
                        # pretend the scan can safely continue after the runtime reports it. Close
                        # the derived index before propagating the fatal condition.
                        store.close()
                        raise
                    except Exception as exc:
                        # A single malformed artifact or adapter defect must not erase the rest of
                        # the visible body. Preserve the failed region and continue other adapters.
                        rec.coverage = "PARTIAL"
                        failures = list(rec.attributes.get("adapter_failures", []))
                        failures.append({
                            "adapter": adapter.name,
                            "adapter_version": str(adapter.version),
                            "error_type": type(exc).__name__,
                            "error": str(exc)[:1000],
                        })
                        rec.attributes = {**rec.attributes, "adapter_failures": failures, "parser_state": "PARTIAL"}
                        combined.findings.append(Finding(
                            stable_id("finding", rec.id, "adapter-failure", adapter.name, str(adapter.version),
                                      type(exc).__name__, str(exc)[:1000]),
                            "parser_failure",
                            f"Adapter {adapter.name} failed while parsing {rec.path}",
                            "PARTIAL",
                            {
                                "adapter": adapter.name,
                                "adapter_version": str(adapter.version),
                                "error_type": type(exc).__name__,
                                "error": str(exc)[:1000],
                                "meaning": "this adapter produced no trusted extraction for this artifact; other adapters and files may continue",
                            },
                            [],
                        ))
                        adapter_runs[f"{adapter.name}:FAILED"] += 1
                        cache_misses += 1
                        continue
                    cache_misses += 1

                reason = controller.would_exceed_result(
                    nodes=len(combined.nodes), edges=len(combined.edges), evidence=len(combined.evidence),
                    add_nodes=len(result.nodes), add_edges=len(result.edges), add_evidence=len(result.evidence),
                )
                if reason:
                    budget_stop_index = file_index
                    budget_stop_adapter = adapter.name
                    break
                if cached is None and rec.sha256:
                    store.put_cache(rec.sha256, adapter.name, cache_version, result)
                adapter_runs[adapter.name] += 1
                combined.merge(result)
            if budget_stop_index is not None:
                break

        skipped_parser_files = 0
        if controller.triggered_reason is not None:
            start_index = budget_stop_index if budget_stop_index is not None else len(files)
            for rec in files[start_index:]:
                if rec.content_available and not rec.is_binary:
                    skipped_parser_files += 1
                    rec.coverage = "PARTIAL"
                    rec.attributes = {
                        **rec.attributes,
                        "parser_state": "BUDGET_STOPPED",
                        "scan_budget_reason": controller.triggered_reason,
                    }
            store.put_files(files)
            combined.findings.append(Finding(
                stable_id("finding", specimen.get("specimen_id"), "scan-budget", controller.triggered_reason,
                          start_index, budget_stop_adapter),
                "scan_budget",
                f"Mechanical extraction stopped at a safe boundary: {controller.triggered_reason}",
                "PARTIAL",
                {
                    "reason": controller.triggered_reason,
                    "detail": controller.triggered_detail,
                    "stopped_file_index": start_index,
                    "stopped_adapter": budget_stop_adapter,
                    "parser_eligible_files_not_fully_processed": skipped_parser_files,
                    "meaning": "remaining visible files stay accounted for; parser/effect closure is intentionally incomplete",
                },
                [],
            ))

        # Adapter failures may downgrade individual parser coverage after the initial census.
        # Persist those explicit states even when no aggregate budget stopped the scan.
        if any(r.attributes.get("adapter_failures") for r in files):
            store.put_files(files)

        if content_unavailable:
            unavailable_states = Counter(r.acquisition_state for r in files if not r.content_available)
            blocked = sum(1 for r in files if not r.content_available and r.coverage == "BLOCKED")
            combined.findings.append(Finding(
                stable_id("finding", specimen.get("specimen_id"), "content-unavailable", content_unavailable, sorted(unavailable_states.items())),
                "acquisition_gap",
                f"{content_unavailable} files are not parser-eligible because verified bytes are unavailable",
                "BLOCKED" if blocked else "PARTIAL",
                {"content_unavailable_file_count": content_unavailable, "acquisition_states": dict(unavailable_states),
                 "blocked_file_count": blocked, "meaning": "files are accounted for but not adapter-parsed"},
                [],
            ))

        combined.merge(resolve_cross_file(combined))
        store.put_result(combined)
        fingerprint = self._fingerprint(files, specimen)
        semantic_specimen = {**specimen, "fingerprint": fingerprint}
        semantic_counts = persist_base_graph(store, semantic_specimen)
        refresh_refinement_completeness(store)
        semantic_counts["completeness_dimensions"] = len(store.completeness_dimensions())
        integrity_outputs = write_integrity_outputs(store, output)
        capability_map = write_nest_capability_map(store, output / "nest_capability_map.json")
        file_rows = store.query("SELECT * FROM files ORDER BY path")
        nodes = store.query("SELECT * FROM nodes ORDER BY kind,name,id")
        edges = store.query("SELECT * FROM edges ORDER BY kind,src,dst")
        findings = store.query("SELECT * FROM findings ORDER BY kind,title")
        evidence = store.query("SELECT * FROM evidence ORDER BY path,start_line,id")

        kind_counts = dict(Counter(n["kind"] for n in nodes))
        language_counts = dict(Counter(f["language"] for f in file_rows))
        coverage_counts = dict(Counter(f["coverage"] for f in file_rows))
        acquisition_counts = dict(Counter(f["acquisition_state"] for f in file_rows))
        metrics = graph_metrics(nodes, edges)
        budget_status = controller.status()
        inventory_budget_states = {k: v for k, v in acquisition_counts.items() if str(k).startswith("RESOURCE_LIMIT_TOTAL")}
        budget_status.update({
            "inventory_limit_states": inventory_budget_states,
            "parser_eligible_files_not_fully_processed": skipped_parser_files,
            "triggered": bool(budget_status["triggered"] or inventory_budget_states),
        })

        summary = {
            "schema_version": "scan-machine-body-map/0.9",
            "engine_version": __version__,
            "specimen": {**specimen, "fingerprint": fingerprint},
            "budget": budget_status,
            "store_recovery": store.recovery_info,
            "inventory": {
                "file_count": len(file_rows),
                "byte_count_declared": sum(f["size"] for f in file_rows),
                "materialized_file_count": materialized,
                "content_unavailable_file_count": content_unavailable,
                "metadata_only_file_count": sum(1 for f in file_rows if f["acquisition_state"] == "METADATA_ONLY"),
                "binary_file_count": sum(1 for f in file_rows if f["is_binary"] == 1),
                "binary_state_unknown_count": sum(1 for f in file_rows if f["is_binary"] is None),
                "language_counts": language_counts,
                "coverage_counts": coverage_counts,
                "acquisition_counts": acquisition_counts,
            },
            "extraction": {
                "node_count": len(nodes), "edge_count": len(edges), "evidence_count": len(evidence),
                "finding_count": len(findings), "node_kind_counts": kind_counts,
                "adapter_runs": dict(adapter_runs), "cache_hits": cache_hits, "cache_misses": cache_misses,
            },
            "graph": metrics,
            "semantic_graph": {
                **semantic_counts,
                "canonical_store": "scan_index.sqlite",
                "interchange": "evidence_graph.json",
                "projections": ["machine_body_map.json", "evidence_graph.json", "evidence_catalog.json", "completeness_vector.json", "integrity_report.json", "surface_closure.json", "effect_closure.json", "nest_capability_map.json", "projection_manifest.json"],
            },
            "completeness_vector": store.completeness_dimensions(),
            "integrity": {k: v for k, v in integrity_outputs["integrity"].items() if k != "issues"},
            "surface_closure": {k: v for k, v in integrity_outputs["surface_closure"].items() if k != "records"},
            "effect_closure": {k: v for k, v in integrity_outputs["effect_closure"].items() if k != "records"},
            "nest_capability_map": {k: v for k, v in capability_map.items() if k not in {"capabilities", "effects", "boundaries", "extensions", "persistence", "guards_errors_retries"}},
            "files": file_rows, "nodes": nodes, "edges": edges, "findings": findings, "evidence": evidence,
        }
        (output / "machine_body_map.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        export_evidence_graph(store, summary["specimen"], output / "evidence_graph.json")
        export_evidence_catalog(store, output / "evidence_catalog.json")
        export_completeness(store, output / "completeness_vector.json")
        (output / "stage1_summary.md").write_text(self._summary_markdown(summary), encoding="utf-8")
        write_projection_manifest(output, [
            "machine_body_map.json", "evidence_graph.json", "evidence_catalog.json",
            "completeness_vector.json", "integrity_report.json", "surface_closure.json", "effect_closure.json", "nest_capability_map.json", "stage1_summary.md",
        ])
        store.close()
        return summary

    @staticmethod
    def _fingerprint(files: list[FileRecord], specimen: dict) -> dict:
        tree = specimen.get("tree_sha") or specimen.get("tree")
        if tree:
            return {"kind": "provider-tree", "value": str(tree), "provider": specimen.get("provider")}
        h = sha256()
        for rec in files:
            h.update(rec.path.encode("utf-8", "surrogatepass"))
            h.update(b"\x00")
            h.update((rec.sha256 or rec.provider_object_id or "UNKNOWN").encode("ascii", "replace"))
            h.update(b"\x00")
            h.update(str(rec.size).encode("ascii"))
            h.update(b"\n")
        return {"kind": "scan-ledger-sha256", "value": h.hexdigest()}

    @staticmethod
    def _summary_markdown(summary: dict) -> str:
        inv = summary["inventory"]
        ex = summary["extraction"]
        graph = summary["graph"]
        sem = summary.get("semantic_graph", {})
        lines = [
            "# SCAN Stage 1 Mechanical Summary", "",
            f"Specimen: `{summary['specimen'].get('specimen_id') or summary['specimen'].get('root') or summary['specimen'].get('repository')}`", "",
            "## Acquisition / inventory", "",
            f"- Files accounted for: {inv['file_count']}",
            f"- Materialized files: {inv['materialized_file_count']}",
            f"- Content-unavailable files: {inv['content_unavailable_file_count']}",
            f"- Metadata-only files: {inv['metadata_only_file_count']}",
            f"- Declared bytes: {inv['byte_count_declared']}",
            f"- Binary files confirmed: {inv['binary_file_count']}",
            f"- Binary state unknown: {inv['binary_state_unknown_count']}",
            f"- File coverage states: `{inv['coverage_counts']}`",
            f"- Acquisition states: `{inv['acquisition_counts']}`",
            f"- Aggregate budget triggered: {summary.get('budget', {}).get('triggered', False)} ({summary.get('budget', {}).get('reason') or summary.get('budget', {}).get('inventory_limit_states') or 'none'})", "",
            "## Mechanical extraction", "",
            f"- Nodes: {ex['node_count']}", f"- Edges: {ex['edge_count']}", f"- Evidence records: {ex['evidence_count']}",
            f"- Findings: {ex['finding_count']}", f"- Cache hits/misses: {ex['cache_hits']}/{ex['cache_misses']}", "",
            "## Graph", "",
            f"- SCCs: {graph['scc_count']}", f"- Non-trivial SCCs: {graph['nontrivial_scc_count']}", f"- Largest SCC: {graph['largest_scc']}", "",
            "## Evidence graph", "",
            f"- Canonical semantic objects: {sem.get('objects', 0)}",
            f"- Canonical semantic relations: {sem.get('relations', 0)}",
            f"- Completeness dimensions: {sem.get('completeness_dimensions', 0)}",
            "- Canonical DB: `scan_index.sqlite`",
            "- Lossless interchange: `evidence_graph.json`",
            "- Friendly projections include evidence, completeness, integrity, and surface-closure views",
            f"- Integrity state/issues: {summary.get('integrity', {}).get('state', 'UNKNOWN')}/{summary.get('integrity', {}).get('issue_count', 0)}",
            f"- Surface binding closure: {summary.get('surface_closure', {}).get('state', 'UNKNOWN')} ({summary.get('surface_closure', {}).get('bound_count', 0)} bound / {summary.get('surface_closure', {}).get('unresolved_count', 0)} unresolved)",
            f"- Deep effect closure: {summary.get('effect_closure', {}).get('state', 'UNKNOWN')} ({summary.get('effect_closure', {}).get('closed_count', 0)} closed / {summary.get('effect_closure', {}).get('partial_count', 0)} partial / {summary.get('effect_closure', {}).get('unresolved_count', 0)} unresolved)",
            f"- NEST capability projection: {summary.get('nest_capability_map', {}).get('state', 'UNKNOWN')} ({summary.get('nest_capability_map', {}).get('capability_count', 0)} capability groups / {summary.get('nest_capability_map', {}).get('effect_count', 0)} effects)", "",
            "## Node kinds", "",
        ]
        for kind, count in sorted(ex["node_kind_counts"].items()):
            lines.append(f"- `{kind}`: {count}")
        lines += ["", "This is mechanical Stage 1 output. Metadata-only files are explicitly accounted for but are not treated as parsed evidence.", ""]
        return "\n".join(lines)
