from __future__ import annotations

"""Static Blueprint-to-candidate conformance.

The coding agent builds; SCAN verifies. Candidate code is rescanned read-only and
compared with the machine-readable contract embedded in the source Blueprint.
"""

from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from .conformance_contract import build_conformance_manifest, parse_blueprint_manifest
from .engine import ScanEngine
from .store import Store

CONFORMANCE_REPORT_SCHEMA = "scan-anchor-conformance-report/0.2"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sig(value: Any) -> str:
    return sha256(_canonical(value).encode("utf-8")).hexdigest()


def _identity_key(contract: dict[str, Any]) -> str:
    return _sig({
        "area": contract.get("area"),
        "kind": contract.get("kind"),
        "identity": contract.get("identity") or {},
    })


def _exact_key(contract: dict[str, Any]) -> str:
    return _sig({
        "area": contract.get("area"),
        "kind": contract.get("kind"),
        "identity": contract.get("identity") or {},
        "expected": contract.get("expected") or {},
    })


def compare_manifests(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    *,
    previous_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    candidate_contracts = list(candidate.get("contracts") or [])
    exact_counts: Counter[str] = Counter()
    by_identity: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for contract in candidate_contracts:
        exact_counts[_exact_key(contract)] += int(contract.get("count") or 1)
        by_identity[_identity_key(contract)].append(contract)

    results: list[dict[str, Any]] = []
    for expected in baseline.get("contracts") or []:
        contract_id = str(expected.get("contract_id"))
        expected_count = int(expected.get("count") or 1)
        exact_count = exact_counts.get(_exact_key(expected), 0)
        alternatives = by_identity.get(_identity_key(expected), [])

        if exact_count >= expected_count:
            status = "SATISFIED"
        elif alternatives:
            status = "CONTRADICTED"
        else:
            status = "MISSING"

        results.append({
            "contract_id": contract_id,
            "area": expected.get("area"),
            "kind": expected.get("kind"),
            "enforcement": expected.get("enforcement") or "REQUIRED",
            "comparison": expected.get("comparison") or "EXACT",
            "source_coverage": expected.get("coverage") or "MAPPED",
            "status": status,
            "expected_count": expected_count,
            "exact_candidate_count": exact_count,
            "identity": expected.get("identity") or {},
            "expected": expected.get("expected") or {},
            "baseline_source_refs": expected.get("source_refs") or [],
            "candidate_alternatives": [
                {
                    "expected": row.get("expected") or {},
                    "count": int(row.get("count") or 1),
                    "source_refs": row.get("source_refs") or [],
                }
                for row in alternatives
            ],
        })

    prior_status = {}
    if previous_report:
        prior_status = {
            str(row.get("contract_id")): str(row.get("status"))
            for row in previous_report.get("contracts") or []
            if row.get("contract_id")
        }
    regressions = []
    for row in results:
        before = prior_status.get(row["contract_id"])
        if before == "SATISFIED" and row["status"] != "SATISFIED":
            regressions.append({
                "contract_id": row["contract_id"],
                "area": row["area"],
                "kind": row["kind"],
                "previous_status": before,
                "current_status": row["status"],
            })

    statuses = Counter(row["status"] for row in results)
    hard_failures = statuses.get("MISSING", 0) + statuses.get("CONTRADICTED", 0)
    state = "FAIL" if hard_failures or regressions else "PASS"
    return {
        "schema_version": CONFORMANCE_REPORT_SCHEMA,
        "state": state,
        "baseline": {
            "app_name": baseline.get("app_name"),
            "blueprint_schema": baseline.get("blueprint_schema"),
            "contract_schema": baseline.get("schema_version"),
            "contract_count": len(baseline.get("contracts") or []),
        },
        "candidate": {
            "app_name": candidate.get("app_name"),
            "contract_count": len(candidate_contracts),
        },
        "summary": {
            "status_counts": dict(sorted(statuses.items())),
            "regression_count": len(regressions),
        },
        "regressions": regressions,
        "contracts": results,
        "authority": {
            "source_blueprint": "PORTABLE_DERIVED_CONTRACT",
            "candidate_measurement": "FRESH_READ_ONLY_SCAN",
            "candidate_self_report": "NO_AUTHORITY",
            "runtime_equivalence_claimed": False,
        },
    }


def render_conformance_report(report: dict[str, Any]) -> str:
    lines = [
        f"# {(report.get('baseline') or {}).get('app_name') or 'Application'} Anchor Conformance",
        "",
        f"**State:** `{report.get('state')}`",
        "",
        "This is a static, evidence-bound comparison. It does not claim runtime, visual/pixel, timing, "
        "network, or performance equivalence.",
        "",
        "| Contract | Area | Kind | Status |",
        "|---|---|---|---|",
    ]
    for row in report.get("contracts") or []:
        lines.append(
            f"| `{row.get('contract_id')}` | {row.get('area')} | `{row.get('kind')}` | "
            f"`{row.get('status')}` |"
        )
    if report.get("regressions"):
        lines += ["", "## Regressions", ""]
        for row in report["regressions"]:
            lines.append(
                f"- `{row['contract_id']}`: {row['previous_status']} -> {row['current_status']}"
            )
    lines += ["", "The coding agent does not certify its own work; SCAN's fresh candidate scan is the measurement authority.", ""]
    return "\n".join(lines)


def render_refinement_instructions(report: dict[str, Any]) -> str:
    unresolved = [
        row for row in report.get("contracts") or []
        if row.get("status") in {"MISSING", "CONTRADICTED"}
    ]
    lines = [
        f"# {(report.get('baseline') or {}).get('app_name') or 'Application'} Anchor Refinement",
        "",
        "Patch the existing candidate; do not rebuild it wholesale unless the operator explicitly chooses that path.",
        "Preserve every currently SATISFIED contract. SCAN will rescan after changes.",
        "",
    ]
    if not unresolved:
        lines += ["No required static contracts remain unresolved.", ""]
        return "\n".join(lines)
    lines += ["## Required unresolved contracts", ""]
    for row in unresolved:
        lines += [
            f"### {row.get('contract_id')} — {row.get('status')}",
            "",
            f"- Area: `{row.get('area')}`",
            f"- Kind: `{row.get('kind')}`",
            f"- Identity: `{_canonical(row.get('identity') or {})}`",
            f"- Expected: `{_canonical(row.get('expected') or {})}`",
            "",
        ]
    return "\n".join(lines)


def _specimen_from_store(store: Store) -> dict[str, Any]:
    rows = [row for row in store.semantic_objects() if row.get("object_type") == "SPECIMEN"]
    return dict(rows[0].get("attributes") or {}) if rows else {}


def evaluate_candidate(
    blueprint_path: Path,
    candidate_root: Path,
    output: Path,
    *,
    engine_version: str,
    specimen_id: str | None = None,
    previous_report_path: Path | None = None,
) -> dict[str, Any]:
    blueprint_path = Path(blueprint_path).resolve(strict=True)
    candidate_root = Path(candidate_root).resolve(strict=True)
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)

    baseline = parse_blueprint_manifest(blueprint_path)
    candidate_scan = output / "candidate.scan"
    ScanEngine().scan(
        candidate_root,
        candidate_scan,
        specimen_id or f"{baseline.get('app_name')}-candidate",
    )

    store = Store(candidate_scan / "scan_index.sqlite", readonly=True)
    try:
        specimen = _specimen_from_store(store)
        candidate_manifest = build_conformance_manifest(
            store,
            specimen,
            engine_version=engine_version,
            blueprint_schema=str(baseline.get("blueprint_schema") or "unknown"),
        )
    finally:
        store.close()

    previous = None
    if previous_report_path is not None:
        previous = json.loads(Path(previous_report_path).read_text(encoding="utf-8"))
        if not isinstance(previous, dict) or previous.get("schema_version") != CONFORMANCE_REPORT_SCHEMA:
            raise ValueError("--previous-report must be a compatible SCAN anchor conformance report")

    report = compare_manifests(baseline, candidate_manifest, previous_report=previous)
    report["source_blueprint"] = {
        "path": str(blueprint_path),
        "sha256": sha256(blueprint_path.read_bytes()).hexdigest(),
    }
    report["candidate_scan"] = {"path": str(candidate_scan)}

    app = str(baseline.get("app_name") or "application")
    json_path = output / "anchor_conformance.json"
    conformance_md = output / f"{app} Anchor Conformance.md"
    refinement_md = output / f"{app} Anchor Refinement.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    conformance_md.write_text(render_conformance_report(report), encoding="utf-8")
    refinement_md.write_text(render_refinement_instructions(report), encoding="utf-8")

    return {
        "state": report["state"],
        "report": report,
        "paths": {
            "candidate_scan": str(candidate_scan),
            "json": str(json_path),
            "conformance": str(conformance_md),
            "refinement": str(refinement_md),
        },
    }
