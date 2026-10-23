"""Safe rule proposals and deterministic assistance fallbacks."""

from __future__ import annotations

import difflib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from organize.config import Config
from organize.output import SavingOutput

from .containment import require_contained
from .events import MemorySink, TraceSession, component_inputs, component_name
from .explain import explain_config, explain_human
from .provider import (
    DisabledProvider,
    MindProvider,
    ProviderUnavailable,
    parse_answer_response,
    parse_proposal_response,
)
from .why import diagnose_path, report_events

SCHEMA_VERSION = "organize-appai.assist.v1"
FORBIDDEN_GENERATED_ACTIONS = {"delete", "trash", "shell", "python"}
ALLOWED_GENERATED_ACTIONS = {"copy", "echo", "move", "rename"}
FORBIDDEN_GENERATED_FILTERS = {"python"}
SAFE_CONFLICT_MODES = {None, "skip", "rename_new", "deduplicate"}
SAFE_TEMPLATE_VALUES = {
    "created",
    "counter",
    "extension",
    "lastmodified",
    "name",
    "stem",
}
TEMPLATE_VALUE = re.compile(r"\{\s*([A-Za-z_][A-Za-z0-9_.]*)")


def discover_workspace(start: str | Path = ".") -> Path | None:
    current = Path(start).resolve()
    for candidate in (current, *current.parents):
        marker = candidate / "WORKSPACE.txt"
        if marker.is_file():
            try:
                recorded = Path(marker.read_text(encoding="utf-8").strip()).resolve()
            except OSError:
                return None
            return recorded if recorded == candidate else None
    return None


def _safe_location(root: Path, location: str | Path | None) -> Path:
    selected = Path(location) if location is not None else root / "fixtures" / "inbox"
    if not selected.exists() and location is None:
        selected = root
    return require_contained(root, selected)


def _deterministic_payload(intent: str, location: Path, root: Path) -> dict[str, Any]:
    lower = intent.lower()
    assumptions: list[str] = []
    filters: list[dict[str, Any] | str] = []
    actions: list[dict[str, Any]] = []
    name = "Organize.AppAI proposal"

    if "duplicate" in lower:
        name = "Report duplicate files"
        filters.append({"duplicate": {"detect_original_by": "first_seen"}})
        actions.append(
            {"echo": "Duplicate candidate: {path}; original: {duplicate.original}"}
        )
        assumptions.append("Duplicates are reported only; no file is deleted or moved.")
    elif "screenshot" in lower and "rename" in lower:
        name = "Rename screenshots by creation date"
        filters.extend(
            [
                {"extension": ["png", "jpg", "jpeg"]},
                {"name": {"startswith": "screenshot"}},
                "created",
            ]
        )
        actions.append(
            {
                "rename": {
                    "new_name": "{created:%Y-%m-%d}_{name}{extension}",
                    "on_conflict": "rename_new",
                }
            }
        )
        assumptions.append(
            "Creation timestamps are available and meaningful on this filesystem."
        )
    elif "older" in lower or re.search(r"\b\d+\s*days?\b", lower):
        days_match = re.search(r"\b(\d+)\s*days?\b", lower)
        days = int(days_match.group(1)) if days_match else 90
        quarantine = require_contained(root, root / "artifacts" / "proposed-quarantine")
        name = f"Quarantine files older than {days} days"
        filters.append({"lastmodified": {"days": days, "mode": "older"}})
        actions.append(
            {"move": {"dest": quarantine.as_posix() + "/", "on_conflict": "rename_new"}}
        )
        assumptions.append(
            "Cleanup means moving to a reviewable quarantine, never deletion."
        )
    elif "pdf" in lower or "invoice" in lower:
        archive = require_contained(root, root / "artifacts" / "proposed-archive")
        name = "Archive PDF invoices by year"
        filters.extend(
            [
                {"extension": "pdf"},
                {"name": {"contains": "invoice", "case_sensitive": False}},
                "lastmodified",
            ]
        )
        actions.append(
            {
                "move": {
                    "dest": archive.as_posix() + "/{lastmodified:%Y}/unknown-vendor/",
                    "on_conflict": "rename_new",
                }
            }
        )
        assumptions.extend(
            [
                "The file modification year is used because no invoice-date field was supplied.",
                "Vendor extraction is not guessed; files go to an unknown-vendor folder.",
            ]
        )
    else:
        filters.append({"name": {"match": "*"}})
        actions.append({"echo": "Candidate: {path}"})
        assumptions.append(
            "The intent was underspecified, so the proposal is report-only."
        )

    config_data = {
        "rules": [
            {
                "name": name,
                "locations": [location.as_posix()],
                "subfolders": False,
                "filters": filters,
                "actions": actions,
            }
        ]
    }
    return {
        "config_yaml": yaml.safe_dump(
            config_data, sort_keys=False, allow_unicode=False
        ),
        "explanation": f"A safe, simulation-only proposal for: {intent}",
        "assumptions": assumptions,
    }


def _validate_proposal(config_text: str, root: Path) -> Config:
    """Validate untrusted proposal text before any host traversal or simulation."""

    raw_config = yaml.safe_load(config_text)
    if not isinstance(raw_config, dict) or not isinstance(
        raw_config.get("rules"), list
    ):
        raise TypeError("proposal must contain a rules list")
    for raw_rule in raw_config["rules"]:
        if not isinstance(raw_rule, dict):
            raise TypeError("each proposed rule must be a mapping")
        if raw_rule.get("subfolders"):
            raise ValueError("assist refuses generated recursive traversal")
        _validate_raw_locations(raw_rule.get("locations", []), root)
        for raw_filter in raw_rule.get("filters", []):
            filter_name = (
                raw_filter
                if isinstance(raw_filter, str)
                else next(iter(raw_filter), "")
            )
            if filter_name in FORBIDDEN_GENERATED_FILTERS:
                raise ValueError(f'assist refuses generated filter "{filter_name}"')
        for raw_action in raw_rule.get("actions", []):
            action_name = (
                raw_action
                if isinstance(raw_action, str)
                else next(iter(raw_action), "")
            )
            if action_name not in ALLOWED_GENERATED_ACTIONS:
                raise ValueError(f'assist refuses generated action "{action_name}"')

    config = Config.from_string(config_text)
    for rule in config.rules:
        if rule.subfolders:
            raise ValueError("assist refuses generated recursive traversal")
        for location in rule.locations:
            if location.max_depth not in {0, "inherit"}:
                raise ValueError("assist refuses generated recursive traversal")
            for configured in location.path:
                _validate_path_text(configured, root, field="location")
        for action in rule.actions:
            name = component_name(action, "action")
            if name not in ALLOWED_GENERATED_ACTIONS:
                raise ValueError(f'assist refuses generated action "{name}"')
            values = component_inputs(action)
            if values.get("on_conflict") not in SAFE_CONFLICT_MODES:
                raise ValueError("assist refuses unsafe conflict policies")
            for field in ("dest",):
                raw = values.get(field)
                if isinstance(raw, str):
                    _validate_path_template(raw, root, field=field)
            new_name = values.get("new_name")
            if isinstance(new_name, str):
                if "/" in new_name or "\\" in new_name:
                    raise ValueError(
                        "assist refuses path separators in generated filenames"
                    )
                _validate_template_values(new_name, field="new_name")
    return config


def _validate_raw_locations(raw_locations: object, root: Path) -> None:
    locations = raw_locations if isinstance(raw_locations, list) else [raw_locations]
    for location in locations:
        paths: object
        if isinstance(location, dict):
            if location.get("max_depth") not in {None, 0, "inherit"}:
                raise ValueError("assist refuses generated recursive traversal")
            paths = location.get("path", [])
        else:
            paths = location
        for value in paths if isinstance(paths, list) else [paths]:
            if not isinstance(value, str):
                raise TypeError("proposed locations must be strings")
            _validate_path_text(value, root, field="location")


def _validate_path_text(value: str, root: Path, *, field: str) -> Path:
    if "~" in value or "$" in value or "%" in value or "{env" in value.lower():
        raise ValueError(f"assist refuses environment or home expansion in {field}")
    if "{" in value or "}" in value:
        raise ValueError(f"assist refuses dynamic templates in {field}")
    return require_contained(root, value)


def _validate_template_values(value: str, *, field: str) -> None:
    referenced = {
        match.group(1).split(".", 1)[0] for match in TEMPLATE_VALUE.finditer(value)
    }
    unsupported = referenced - SAFE_TEMPLATE_VALUES
    if unsupported:
        raise ValueError(
            f"assist refuses unsupported template values in {field}: "
            + ", ".join(sorted(unsupported))
        )


def _validate_path_template(value: str, root: Path, *, field: str) -> None:
    if "~" in value or "$" in value or "%" in value or "{env" in value.lower():
        raise ValueError(f"assist refuses environment or home expansion in {field}")
    _validate_template_values(value, field=field)
    if ".." in re.split(r"[/\\]+", value):
        raise ValueError(f"assist refuses parent traversal in {field}")
    static_prefix = value.split("{", 1)[0].rstrip("/\\") or "."
    require_contained(root, static_prefix)


def create_proposal(
    intent: str,
    *,
    safe_root: str | Path,
    location: str | Path | None = None,
    existing_config: str | Path | None = None,
    proposal_dir: str | Path | None = None,
    provider: MindProvider | None = None,
) -> dict[str, Any]:
    root = Path(safe_root).resolve(strict=True)
    chosen_location = _safe_location(root, location)
    deterministic = _deterministic_payload(intent, chosen_location, root)
    source = "deterministic"
    provider_error: str | None = None

    selected_provider = provider or DisabledProvider()
    try:
        prompt = json.dumps(
            {
                "task": "Return a safe organize configuration proposal as ProposalPayload JSON.",
                "intent": intent[:2_000],
                "allowed_actions": sorted(ALLOWED_GENERATED_ACTIONS),
                "forbidden_actions": sorted(FORBIDDEN_GENERATED_ACTIONS),
                "safe_location": chosen_location.as_posix(),
                "constraints": ["never execute", "never overwrite", "simulation first"],
            },
            sort_keys=True,
        )
        model_payload = parse_proposal_response(selected_provider.complete(prompt))
        candidate = model_payload.model_dump()
        _validate_proposal(candidate["config_yaml"], root)
        deterministic = candidate
        source = selected_provider.name
    except ProviderUnavailable as error:
        provider_error = str(error)
    except Exception as error:  # noqa: BLE001 - model output is an untrusted boundary
        provider_error = f"provider output rejected: {type(error).__name__}: {error}"

    config = _validate_proposal(deterministic["config_yaml"], root)
    target_dir = require_contained(
        root, proposal_dir or root / ".organize-appai" / "proposals"
    )
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    proposal_path = require_contained(root, target_dir / f"proposal-{stamp}.yaml")
    with proposal_path.open("w", encoding="utf-8", newline="\n") as _f:
        _f.write(deterministic["config_yaml"])

    memory = MemorySink()
    trace = TraceSession(memory, simulation=True, privacy_root=root)
    output = SavingOutput()
    previous = Path.cwd()
    os.chdir(root)
    try:
        config.execute(simulate=True, output=output, working_dir=root, trace=trace)
    finally:
        os.chdir(previous)

    diff: list[str] = []
    if existing_config is not None:
        existing_path = require_contained(root, existing_config)
        existing_text = existing_path.read_text(encoding="utf-8")
        diff = list(
            difflib.unified_diff(
                existing_text.splitlines(),
                deterministic["config_yaml"].splitlines(),
                fromfile=str(existing_path),
                tofile=str(proposal_path),
                lineterm="",
            )
        )

    return {
        "schema": SCHEMA_VERSION,
        "source": source,
        "provider_error": provider_error,
        "proposal_path": str(proposal_path),
        "config_yaml": deterministic["config_yaml"],
        "explanation": deterministic["explanation"],
        "assumptions": deterministic["assumptions"],
        "validation": "passed",
        "simulation": {
            "run_id": trace.run_id,
            "events": [event.to_dict() for event in memory.events],
            "host_messages": [event.model_dump(mode="json") for event in output.queue],
        },
        "diff": diff,
        "execution": "not_performed",
        "simulation_command": f'organize sim "{proposal_path}" --working-dir "{root}"',
    }


def answer_existing(
    config: Config,
    question: str,
    *,
    safe_root: str | Path | None = None,
    provider: MindProvider | None = None,
    tags: tuple[str, ...] = (),
    skip_tags: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Answer from bounded deterministic evidence, optionally interpreted by a MIND."""

    static = explain_config(
        config, tags=tags, skip_tags=skip_tags, working_dir=safe_root or "."
    )
    evidence: list[dict[str, Any]] = []
    for rule in static["rules"]:
        evidence.append(
            {
                "ref": f"config:rule:{rule['index'] + 1}",
                "kind": "configuration",
                "fact": {
                    "name": rule["name"],
                    "eligible": rule["eligible"],
                    "eligibility_reason": rule["eligibility_reason"],
                    "targets": rule["targets"],
                    "filters": [item["name"] for item in rule["filters"]],
                    "actions": [item["name"] for item in rule["actions"]],
                    "risks": rule["suspicious"],
                },
            }
        )

    trace_reports: list[dict[str, object]] = []
    if safe_root is not None:
        root = Path(safe_root).resolve(strict=True)
        for candidate in _bounded_candidates(config, root, limit=20):
            diagnosis = diagnose_path(
                config,
                candidate,
                approved_root=root,
                tags=tags,
                skip_tags=skip_tags,
            )
            trace_reports.append(diagnosis)
            for event in report_events(diagnosis):
                if not isinstance(event, dict):
                    continue
                evidence.append(
                    {
                        "ref": f"trace:{event['run_id']}:{event['sequence']}",
                        "kind": "trace",
                        "fact": {
                            "rule_name": event["rule_name"],
                            "resource_path": event["resource_path"],
                            "stage": event["stage"],
                            "component": event["component_name"],
                            "outcome": event["outcome"],
                            "reason_code": event["reason_code"],
                            "explanation": event["explanation"],
                        },
                    }
                )
                if len(evidence) >= 200:
                    break
            if len(evidence) >= 200:
                break

    allowed_refs = {item["ref"] for item in evidence}
    selected_provider = provider or DisabledProvider()
    provider_error: str | None = None
    source = "deterministic"
    citations: list[dict[str, str]] = []
    uncertainty = (
        "No filesystem trace was gathered; this answer describes parsed configuration only."
        if not trace_reports
        else "The evidence is a bounded, read-only sample and may not include every resource."
    )
    answer = _deterministic_answer(question, static, evidence, uncertainty)
    try:
        prompt = json.dumps(
            {
                "task": "Answer using only this bounded evidence. Return AnswerPayload JSON.",
                "question": question[:2_000],
                "evidence": evidence,
                "requirements": [
                    "cite one or more supplied refs exactly",
                    "label uncertainty",
                    "do not invent execution facts",
                ],
            },
            ensure_ascii=True,
            sort_keys=True,
        )
        payload = parse_answer_response(selected_provider.complete(prompt))
        unknown = {citation.ref for citation in payload.citations} - allowed_refs
        if unknown:
            raise ValueError(
                "provider cited evidence that was not supplied: "
                + ", ".join(sorted(unknown))
            )
        answer = payload.answer
        citations = [citation.model_dump() for citation in payload.citations]
        uncertainty = payload.uncertainty
        source = selected_provider.name
    except ProviderUnavailable as error:
        provider_error = str(error)
    except Exception as error:  # noqa: BLE001 - model output is an untrusted boundary
        provider_error = f"provider output rejected: {type(error).__name__}: {error}"

    result = {
        "schema": "organize-appai.assist-answer.v1",
        "source": source,
        "answer": answer,
        "citations": citations,
        "uncertainty": uncertainty,
        "provider_error": provider_error,
        "evidence_refs": sorted(allowed_refs),
        "trace_run_ids": [str(item["run_id"]) for item in trace_reports],
        "configuration": static,
    }
    # Shared Mantle 2 contract: keep the historical dictionary API for host
    # callers, while exposing an evidence-typed answer for resident integrations.
    try:
        from mantle.contracts import EvidenceRef, GroundedAnswer, GroundedClaim, ClaimStatus
        refs = tuple(
            EvidenceRef("organize", str(item), "assist.evidence")
            for item in sorted(allowed_refs)
        )
        status = ClaimStatus.INFERRED if source != "deterministic" else ClaimStatus.OBSERVED
        claim = GroundedClaim(
            "organize-assist-answer", str(answer), status, evidence=refs,
            limitations=(str(uncertainty),),
        )
        result["grounded_answer"] = GroundedAnswer(
            str(answer), (claim,), (str(uncertainty),), deterministic_fallback=str(
                _deterministic_answer(question, static, evidence, uncertainty)
            ),
        ).to_dict()
    except Exception:
        result["grounded_answer"] = None
    return result


def _bounded_candidates(config: Config, root: Path, *, limit: int) -> list[Path]:
    from organize.template import render

    candidates: list[Path] = []
    seen: set[Path] = set()
    for rule in config.rules:
        for location in rule.locations:
            for configured in location.path:
                expanded = _safe_resolve(
                    root, lambda configured=configured: render(configured)
                )
                if expanded is None:
                    continue
                if not expanded.is_dir():
                    continue
                try:
                    children = sorted(expanded.iterdir(), key=lambda item: item.name)
                except OSError:
                    continue
                for child in children:
                    safe_child = _safe_resolve(root, lambda child=child: child)
                    if safe_child is None:
                        continue
                    if safe_child in seen:
                        continue
                    seen.add(safe_child)
                    candidates.append(safe_child)
                    if len(candidates) >= limit:
                        return candidates
    return candidates


def _safe_resolve(root: Path, value) -> Path | None:
    try:
        return require_contained(root, value())
    except Exception:  # noqa: BLE001 - an untrusted path/template is omitted from evidence
        return None


def _deterministic_answer(
    question: str,
    static: dict[str, Any],
    evidence: list[dict[str, Any]],
    uncertainty: str,
) -> str:
    trace_facts = [item for item in evidence if item["kind"] == "trace"]
    lines = [f"Question: {question}", "", explain_human(static)]
    if trace_facts:
        lines.append("\nBounded diagnostic evidence:")
        for item in trace_facts[:20]:
            fact = item["fact"]
            lines.append(
                f"  [{item['ref']}] {fact['rule_name'] or 'pipeline'} / "
                f"{fact['reason_code']}: {fact['explanation']}"
            )
    lines.extend(["", f"Uncertainty: {uncertainty}"])
    return "\n".join(lines)


def proposal_human(report: dict[str, Any]) -> str:
    lines = [
        report["explanation"],
        f"Proposal: {report['proposal_path']}",
        f"Source: {report['source']}",
        f"Validation: {report['validation']}",
        "Execution: not performed",
    ]
    if report.get("provider_error"):
        lines.append(f"MIND fallback: {report['provider_error']}")
    if report["assumptions"]:
        lines.append("Assumptions:")
        lines.extend(f"  - {item}" for item in report["assumptions"])
    if report["diff"]:
        lines.append("Diff:")
        lines.extend(report["diff"])
    lines.extend(
        [
            "",
            "Proposed configuration:",
            report["config_yaml"],
            "Review with:",
            report["simulation_command"],
        ]
    )
    return "\n".join(lines)
