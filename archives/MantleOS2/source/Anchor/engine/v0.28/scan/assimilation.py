from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import tomllib
from typing import Any

from .model import stable_id


# Runtime languages with dedicated structural extractors in the current engine. Build/config/document
# formats are intentionally excluded from novel-runtime detection because they are supporting anatomy,
# not by themselves an application execution substrate.
_SPECIALIZED_RUNTIME_LANGUAGES: dict[str, set[str]] = {
    "clang_cpp": {"C", "C/C++ Header", "C++", "C++ Header"},
    "cpp_qt": {"C", "C/C++ Header", "C++", "C++ Header"},
    "m3c_cpp": {"C", "C/C++ Header", "C++", "C++ Header"},
    "typescript-electron": {"JavaScript", "TypeScript"},
}

_SUPPORTING_LANGUAGES = {
    "Markdown", "JSON", "YAML", "TOML", "XML", "Qt UI XML", "Qt Resource XML",
    "CMake", "QMake", "Make", "Dockerfile", "Gradle", "Properties", "INI", "Config",
}

_MANIFEST_NAMES = {
    "package.json", "pyproject.toml", "cargo.toml", "requirements.txt", "requirements-dev.txt",
    "pom.xml", "build.gradle", "build.gradle.kts", "composer.json", "gemfile", "go.mod",
}


def _json(value: Any, default):
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def _active_specialized_languages(adapter_runs: dict[str, int]) -> set[str]:
    out: set[str] = set()
    for adapter_name, languages in _SPECIALIZED_RUNTIME_LANGUAGES.items():
        if any(str(name).split(":", 1)[0] == adapter_name and count for name, count in adapter_runs.items()):
            out.update(languages)
    return out


def _safe_manifest_hints(content_root: Path | None, files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return bounded dependency/framework hints without importing or executing specimen code."""
    if content_root is None:
        return []
    hints: list[dict[str, Any]] = []
    for row in files:
        rel = str(row.get("path") or "")
        name = Path(rel).name.lower()
        if name not in _MANIFEST_NAMES:
            continue
        path = content_root / rel
        try:
            data = path.read_bytes()
        except OSError:
            continue
        # Workbench hints are never canonical evidence. Bound file size and output cardinality so an
        # unfamiliar dependency tree cannot turn assimilation planning into another whole-repo parser.
        if len(data) > 2 * 1024 * 1024:
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        deps: set[str] = set()
        try:
            if name == "package.json":
                obj = json.loads(text)
                for key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
                    value = obj.get(key) or {}
                    if isinstance(value, dict):
                        deps.update(str(x) for x in value)
            elif name == "pyproject.toml":
                obj = tomllib.loads(text)
                project = obj.get("project") or {}
                for dep in project.get("dependencies") or []:
                    deps.add(re.split(r"[<>=!~ ;\[]", str(dep), 1)[0])
                optional = project.get("optional-dependencies") or {}
                if isinstance(optional, dict):
                    for values in optional.values():
                        for dep in values or []:
                            deps.add(re.split(r"[<>=!~ ;\[]", str(dep), 1)[0])
            elif name == "cargo.toml":
                obj = tomllib.loads(text)
                for key in ("dependencies", "dev-dependencies", "build-dependencies"):
                    value = obj.get(key) or {}
                    if isinstance(value, dict):
                        deps.update(str(x) for x in value)
            elif name.startswith("requirements"):
                for raw in text.splitlines():
                    raw = raw.strip()
                    if not raw or raw.startswith("#") or raw.startswith("-"):
                        continue
                    deps.add(re.split(r"[<>=!~ ;\[]", raw, 1)[0])
        except (ValueError, TypeError):
            # Unknown or malformed manifest syntax remains visible as a manifest with no extracted
            # hints; assimilation never guesses dependency names from a failed parse.
            pass
        hints.append({"path": rel, "dependencies": sorted(x for x in deps if x)[:80]})
        if len(hints) >= 12:
            break
    return hints


def _module_hints(nodes: list[dict[str, Any]]) -> list[str]:
    modules: set[str] = set()
    for row in nodes:
        if row.get("kind") != "module_reference":
            continue
        attrs = _json(row.get("attributes_json") or row.get("attributes"), {})
        value = attrs.get("module") or row.get("name")
        if value:
            modules.add(str(value))
    return sorted(modules)[:120]


def _read_projection(output: Path, name: str) -> dict[str, Any]:
    try:
        return json.loads((output / name).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _evidence_samples(evidence: list[dict[str, Any]], interesting_paths: set[str]) -> list[dict[str, Any]]:
    by_path: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in evidence:
        path = str(row.get("path") or "")
        if path in interesting_paths:
            by_path[path].append(row)
    out: list[dict[str, Any]] = []
    for path in sorted(interesting_paths):
        rows = sorted(by_path.get(path, []), key=lambda r: (r.get("start_line") or 0, str(r.get("id") or "")))
        for row in rows[:6]:
            out.append({
                "id": row.get("id"), "path": path,
                "start_line": row.get("start_line"), "end_line": row.get("end_line"),
                "evidence_class": row.get("evidence_class"), "extractor": row.get("extractor"),
                "excerpt": row.get("excerpt"),
            })
        if len(out) >= 72:
            break
    return out[:72]


def _candidate_adapter_text(profile_id: str, target_languages: list[str]) -> str:
    return f'''from __future__ import annotations\n\n# AUTO-GENERATED ASSIMILATION SCAFFOLD.\n# This file is inert until an authorized coding/LLM step implements it and a human/CI explicitly loads it.\n# It must remain specimen-generic: no specimen filenames, symbol names, labels, or hard-coded routes.\n\nfrom pathlib import Path\n\nfrom scan.adapters.base import Adapter\nfrom scan.inventory import FileRecord\nfrom scan.model import ExtractionResult\n\n\nPROFILE_ID = {profile_id!r}\nTARGET_LANGUAGES = {target_languages!r}\n\n\nclass CandidateAssimilationAdapter(Adapter):\n    name = "assimilation-candidate"\n    version = "0"\n\n    def accepts(self, record: FileRecord) -> bool:\n        return record.language in TARGET_LANGUAGES\n\n    def extract(self, root: Path, record: FileRecord, text: str) -> ExtractionResult:\n        # TODO(LLM/coding agent): replace with reusable mechanical extraction.\n        # Rules:\n        # - parse source bytes only; never execute/import/build/stimulate the specimen;\n        # - emit stable evidence before interpretation;\n        # - preserve UNKNOWN/PARTIAL/BLOCKED rather than guessing;\n        # - model human surfaces, routes, effects, state, and BODY/NEST boundaries explicitly;\n        # - do not encode specimen-specific names or expected answers.\n        return ExtractionResult()\n'''


def _candidate_probe_text(profile_id: str) -> str:
    return f'''from __future__ import annotations\n\n# AUTO-GENERATED PARSE-ONLY PROBE SCAFFOLD for {profile_id}.\n# A coding agent may replace this with a language/framework parser helper. It must never import or\n# execute specimen modules. Input is one source file; output is deterministic JSON.\n\nimport json\nfrom pathlib import Path\nimport sys\n\n\ndef main() -> int:\n    if len(sys.argv) != 2:\n        print("usage: candidate_probe.py <source-file>", file=sys.stderr)\n        return 2\n    path = Path(sys.argv[1])\n    text = path.read_text(encoding="utf-8", errors="replace")\n    print(json.dumps({{"schema_version": "scan-assimilation-probe/0.1", "bytes": len(text.encode('utf-8')), "records": []}}, sort_keys=True))\n    return 0\n\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n'''


def _candidate_test_text(target_languages: list[str]) -> str:
    return f'''from __future__ import annotations\n\n# AUTO-GENERATED candidate test scaffold. These tests live in the workbench and are not part of the\n# trusted scanner suite until the candidate is reviewed and promoted.\n\nfrom candidate_adapter import CandidateAssimilationAdapter, TARGET_LANGUAGES\n\n\ndef test_candidate_targets_detected_languages():\n    assert TARGET_LANGUAGES == {target_languages!r}\n\n\ndef test_candidate_is_not_specimen_named():\n    # Promotion review should add fixture-driven behavioral tests and reject specimen literals.\n    assert "candidate" in CandidateAssimilationAdapter.name\n'''


def _llm_brief(request: dict[str, Any]) -> str:
    reasons = "\n".join(f"- {r['kind']}: {r['detail']}" for r in request["reasons"])
    langs = ", ".join(request["unknown_runtime_languages"]) or "none"
    modules = ", ".join(request["module_hints"][:30]) or "none"
    return f'''# SCAN Adaptive Assimilation Task\n\nYou are extending the SCAN scanner for an unfamiliar or incompletely mapped software substrate.\n\nProfile: `{request['profile_id']}`\nSpecimen fingerprint: `{request['specimen_fingerprint']}`\nUnknown runtime languages: {langs}\nObserved module/framework hints: {modules}\n\n## Why assimilation opened\n\n{reasons}\n\n## Authority boundary\n\nThe specimen is evidence, not executable input. Do **not** run, import, build, instrument, or stimulate it.\nYour job is to improve reusable scanner code so deterministic extraction can recover the missing anatomy.\nThe LLM may design/author candidate scanner code, but it may not promote semantic claims merely because they\nare plausible. Every emitted fact must remain traceable to source/config evidence.\n\n## Work\n\n1. Inspect `assimilation_request.json`, `evidence_samples.json`, and the bounded specimen paths listed there.\n2. Implement `candidate_adapter.py` and, only if needed, `candidate_probe.py` as generic substrate support.\n3. Add fixture-driven tests to `test_candidate_adapter.py` for every generic rule learned.\n4. Never hard-code specimen filenames, labels, symbols, IPC channels, expected counts, or routes.\n5. Run the unchanged scanner regression suite.\n6. Cold-scan the exact frozen specimen with the old adapters, then with the candidate.\n7. Run the candidate scan twice and require byte-identical canonical projections.\n8. Inspect *newly closed* routes for false joins/cross-contamination; lower honest closure beats false closure.\n9. Promote only after `promotion_gate.json` is satisfied.\n\n## Desired outcome\n\nTurn this specimen-specific surprise into reusable scanner knowledge that benefits the next project using the\nsame language/framework patterns. Preserve A1-A8 throughout.\n'''


def prepare_assimilation_workbench(*, output: Path, specimen: dict[str, Any], files: list[dict[str, Any]],
                                   nodes: list[dict[str, Any]], findings: list[dict[str, Any]],
                                   evidence: list[dict[str, Any]], adapter_runs: dict[str, int],
                                   content_root: Path | None) -> dict[str, Any]:
    """Detect extraction blind spots and create a deterministic, inert self-extension workbench.

    This function never calls an LLM and never executes generated code. It turns mechanical scan gaps into a
    bounded coding handoff so an authorized LLM/coding agent can add reusable adapters without blurring A2.
    """
    output = Path(output)
    active_languages = _active_specialized_languages(adapter_runs)
    runtime_language_counts = Counter(
        str(row.get("language") or "Unknown") for row in files
        if not bool(row.get("is_binary")) and str(row.get("language") or "Unknown") not in _SUPPORTING_LANGUAGES
    )
    unknown_languages = sorted(
        lang for lang, count in runtime_language_counts.items()
        if count and lang not in active_languages and lang != "Unknown"
    )
    unknown_paths = {
        str(row.get("path")) for row in files
        if str(row.get("language") or "Unknown") in set(unknown_languages)
    }
    parser_failures = [row for row in findings if row.get("kind") == "parser_failure"]
    resolution_gaps = [row for row in findings if row.get("kind") == "resolution_gap"]
    surface = _read_projection(output, "surface_closure.json")
    effect = _read_projection(output, "effect_closure.json")

    reasons: list[dict[str, Any]] = []
    if unknown_languages:
        reasons.append({
            "kind": "unsupported_runtime_language",
            "detail": f"runtime source lacks a dedicated structural adapter: {unknown_languages}",
            "count": sum(runtime_language_counts[x] for x in unknown_languages),
        })
    if parser_failures:
        reasons.append({"kind": "parser_failure", "detail": f"{len(parser_failures)} adapter parses failed", "count": len(parser_failures)})
    if surface.get("surface_count") and (surface.get("partial_count", 0) or surface.get("unresolved_count", 0)):
        reasons.append({
            "kind": "human_surface_closure",
            "detail": f"{surface.get('partial_count', 0)} partial and {surface.get('unresolved_count', 0)} unresolved human routes",
            "count": int(surface.get("partial_count", 0)) + int(surface.get("unresolved_count", 0)),
        })
    if effect.get("surface_count") and (effect.get("partial_count", 0) or effect.get("unresolved_count", 0)):
        reasons.append({
            "kind": "effect_closure",
            "detail": f"{effect.get('partial_count', 0)} partial and {effect.get('unresolved_count', 0)} unresolved surface-to-effect routes",
            "count": int(effect.get("partial_count", 0)) + int(effect.get("unresolved_count", 0)),
        })
    if resolution_gaps:
        reasons.append({"kind": "resolution_gap", "detail": f"{len(resolution_gaps)} ambiguous/unresolved structural resolutions", "count": len(resolution_gaps)})

    required = bool(reasons)
    workbench = output / "assimilation"
    if workbench.exists():
        shutil.rmtree(workbench)
    if not required:
        return {
            "state": "NOT_REQUIRED", "required": False, "workbench": None,
            "unknown_runtime_languages": [], "reason_count": 0,
        }

    module_hints = _module_hints(nodes)
    manifest_hints = _safe_manifest_hints(content_root, files)
    fingerprint = (specimen.get("fingerprint") or {}).get("value") or specimen.get("specimen_id") or "unknown"
    signature_payload = json.dumps({
        "fingerprint": fingerprint, "unknown_languages": unknown_languages, "module_hints": module_hints,
        "reason_kinds": [r["kind"] for r in reasons],
    }, sort_keys=True, ensure_ascii=False)
    profile_id = stable_id("assimilation-profile", signature_payload)

    interesting_paths = set(unknown_paths)
    for row in parser_failures[:24] + resolution_gaps[:24]:
        attrs = _json(row.get("attributes_json") or row.get("attributes"), {})
        for key in ("path", "source_path", "file", "file_path"):
            if attrs.get(key):
                interesting_paths.add(str(attrs[key]))
    for record in (surface.get("records") or []):
        if record.get("closure") in {"PARTIAL", "UNRESOLVED"} and record.get("path"):
            interesting_paths.add(str(record["path"]))
        if len(interesting_paths) >= 40:
            break

    request = {
        "schema_version": "scan-adaptive-assimilation/0.1",
        "profile_id": profile_id,
        "state": "OPEN",
        "specimen_fingerprint": str(fingerprint),
        "specimen": {
            "specimen_id": specimen.get("specimen_id"), "repository": specimen.get("repository"),
            "commit_sha": specimen.get("commit_sha"), "tree_sha": specimen.get("tree_sha") or specimen.get("tree"),
        },
        "authority": {
            "ordinary_scan_remains_non_executing": True,
            "generated_candidate_code_auto_executed": False,
            "llm_may_author_scanner_code": True,
            "llm_may_invent_evidence": False,
            "promotion_requires_regression_and_determinism": True,
        },
        "reasons": reasons,
        "runtime_language_counts": dict(sorted(runtime_language_counts.items())),
        "unknown_runtime_languages": unknown_languages,
        "representative_paths": sorted(interesting_paths)[:60],
        "module_hints": module_hints,
        "manifest_hints": manifest_hints,
        "surface_closure": {k: surface.get(k) for k in ("state", "surface_count", "bound_count", "partial_count", "unresolved_count", "closure_ratio")},
        "effect_closure": {k: effect.get(k) for k in ("state", "surface_count", "closed_count", "partial_count", "unresolved_count", "closure_ratio")},
        "adapter_runs": dict(sorted(adapter_runs.items())),
    }

    samples = _evidence_samples(evidence, set(request["representative_paths"]))
    gate = {
        "schema_version": "scan-assimilation-promotion-gate/0.1",
        "profile_id": profile_id,
        "required": [
            "existing SCAN regression suite passes",
            "candidate rules contain no specimen-specific literals/expected counts/routes",
            "candidate does not execute/import/build/instrument/stimulate specimen code",
            "exact specimen identity is unchanged between baseline and candidate runs",
            "candidate canonical projections are byte-identical across two fresh unchanged runs",
            "integrity ERROR count does not increase",
            "new closure routes are evidence-backed and manually/adversarially checked for false joins",
            "UNKNOWN/PARTIAL/BLOCKED states are preserved where evidence is insufficient",
            "generic fixture tests encode every new transferable rule before promotion",
        ],
        "promotion_state": "BLOCKED_UNTIL_VALIDATED",
    }

    workbench.mkdir(parents=True, exist_ok=True)
    (workbench / "assimilation_request.json").write_text(json.dumps(request, indent=2, ensure_ascii=False), encoding="utf-8")
    (workbench / "evidence_samples.json").write_text(json.dumps({
        "schema_version": "scan-assimilation-evidence-samples/0.1", "profile_id": profile_id,
        "samples": samples,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    (workbench / "promotion_gate.json").write_text(json.dumps(gate, indent=2, ensure_ascii=False), encoding="utf-8")
    (workbench / "candidate_adapter.py").write_text(_candidate_adapter_text(profile_id, unknown_languages), encoding="utf-8")
    (workbench / "candidate_probe.py").write_text(_candidate_probe_text(profile_id), encoding="utf-8")
    (workbench / "test_candidate_adapter.py").write_text(_candidate_test_text(unknown_languages), encoding="utf-8")
    (workbench / "LLM_ASSIMILATION_TASK.md").write_text(_llm_brief(request), encoding="utf-8")
    (workbench / "README.md").write_text(
        "# SCAN assimilation workbench\n\n"
        "This directory was generated because the mechanical scan found substrate/closure gaps. It is an inert "
        "self-extension workbench, not canonical evidence and not automatically executable code. Start with "
        "`LLM_ASSIMILATION_TASK.md`; preserve the frozen specimen identity and satisfy `promotion_gate.json` before "
        "moving any candidate rule into the scanner.\n",
        encoding="utf-8",
    )

    manifest = []
    for path in sorted(workbench.iterdir()):
        data = path.read_bytes()
        manifest.append({"name": path.name, "bytes": len(data), "sha256": sha256(data).hexdigest()})
    (workbench / "WORKBENCH_MANIFEST.json").write_text(json.dumps({
        "schema_version": "scan-assimilation-workbench-manifest/0.1", "profile_id": profile_id,
        "files": manifest,
    }, indent=2), encoding="utf-8")

    return {
        "state": "OPEN", "required": True, "profile_id": profile_id,
        "workbench": "assimilation", "unknown_runtime_languages": unknown_languages,
        "reason_count": len(reasons), "evidence_sample_count": len(samples),
    }
