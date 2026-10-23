"""Deterministic, model-free configuration explanation."""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from organize.config import Config, should_execute

from .events import component_inputs, component_name
from .privacy import redact_text, sanitize

SCHEMA_VERSION = "organize-appai.explain.v1"
HIGH_RISK_ACTIONS = {"delete", "trash", "shell", "python", "write", "symlink"}
MUTATIONS = {
    "move": "moves and may rename a resource",
    "copy": "creates a copy and may create directories",
    "rename": "renames a resource",
    "delete": "permanently deletes a resource",
    "trash": "moves a resource to the operating-system trash",
    "shell": "invokes an external command",
    "python": "executes inline Python",
    "write": "writes content to a file",
    "symlink": "creates a symbolic link",
    "hardlink": "creates a hard link",
    "macos_tags": "changes macOS filesystem tags",
    "echo": "prints a message only",
    "confirm": "asks for confirmation and may stop the pipeline",
}
PLACEHOLDER = re.compile(r"\{\s*([A-Za-z_][A-Za-z0-9_.]*)")


def _templates(values: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for field, value in sorted(values.items()):
        if isinstance(value, str) and "{" in value and "}" in value:
            required = sorted(
                {
                    match.group(1).split(".", 1)[0]
                    for match in PLACEHOLDER.finditer(value)
                }
                - {"env", "now", "utcnow", "today"}
            )
            found.append(
                {
                    "field": field,
                    "template": redact_text(value),
                    "required_values": required,
                }
            )
    return found


def _optional_dependencies(filter_names: Iterable[str]) -> list[dict[str, Any]]:
    if "filecontent" not in set(filter_names):
        return []
    return [
        {
            "feature": "PDF text extraction command",
            "dependency": "pdftotext",
            "available": shutil.which("pdftotext") is not None,
        },
        {
            "feature": "PDF text extraction fallback",
            "dependency": "pdfminer",
            "available": importlib.util.find_spec("pdfminer") is not None,
        },
        {
            "feature": "DOCX text extraction",
            "dependency": "docx2txt",
            "available": importlib.util.find_spec("docx2txt") is not None,
        },
    ]


def explain_config(
    config: Config,
    *,
    tags: Iterable[str] = (),
    skip_tags: Iterable[str] = (),
    working_dir: str | Path = ".",
) -> dict[str, Any]:
    """Return a stable JSON-compatible explanation built from parsed host objects."""

    selected_tags = set(tags)
    excluded_tags = set(skip_tags)
    rules: list[dict[str, Any]] = []
    all_filter_names: list[str] = []
    global_risks: set[str] = set()

    for index, rule in enumerate(config.rules):
        rule_name = rule.name or f"rule {index + 1}"
        tag_eligible = should_execute(rule.tags, selected_tags, excluded_tags)
        locations: list[dict[str, Any]] = []
        for location in rule.locations:
            for configured_path in location.path:
                locations.append(
                    {
                        "path": redact_text(configured_path),
                        "min_depth": location.min_depth,
                        "max_depth": (
                            None
                            if location.max_depth == "inherit" and rule.subfolders
                            else 0
                            if location.max_depth == "inherit"
                            else location.max_depth
                        ),
                        "recursive": bool(
                            rule.subfolders
                            if location.max_depth == "inherit"
                            else location.max_depth is None or location.max_depth > 0
                        ),
                        "file_globs": sorted(location.filter or []),
                        "directory_globs": sorted(location.filter_dirs or []),
                        "excluded_files": sorted(location.exclude_files),
                        "excluded_directories": sorted(location.exclude_dirs),
                    }
                )

        filters: list[dict[str, Any]] = []
        for order, filter_item in enumerate(rule.filters, start=1):
            name = component_name(filter_item, "filter")
            base_name = name.removeprefix("not ")
            all_filter_names.append(base_name)
            values = component_inputs(filter_item)
            filters.append(
                {
                    "order": order,
                    "name": name,
                    "options": sanitize(values),
                    "templates": _templates(values),
                }
            )

        actions: list[dict[str, Any]] = []
        for order, action in enumerate(rule.actions, start=1):
            name = component_name(action, "action")
            values = component_inputs(action)
            risks: list[str] = []
            if name in HIGH_RISK_ACTIONS:
                risks.append("high-risk action")
            if values.get("on_conflict") in {"overwrite", "trash"}:
                risks.append(f"destructive conflict policy: {values['on_conflict']}")
            if name in {"shell", "python"} and values.get("run_in_simulation"):
                risks.append("configured to execute during simulation")
            global_risks.update(risks)
            actions.append(
                {
                    "order": order,
                    "name": name,
                    "mutation": MUTATIONS.get(
                        name, "may change resource or application state"
                    ),
                    "conflict_policy": values.get("on_conflict"),
                    "options": sanitize(values),
                    "templates": _templates(values),
                    "risks": risks,
                }
            )

        suspicious: list[str] = []
        if not rule.enabled:
            suspicious.append("rule is disabled")
        if rule.locations and not rule.filters:
            suspicious.append("no filters: every selected target can reach the actions")
        if rule.subfolders:
            suspicious.append("recursive traversal is enabled")
        if any(".." in Path(item["path"]).parts for item in locations):
            suspicious.append("a location contains parent traversal")
        if any(
            item["path"].startswith(("/", "\\"))
            or re.match(r"^[A-Za-z]:", item["path"])
            for item in locations
        ):
            suspicious.append("an absolute location is configured")

        rules.append(
            {
                "index": index,
                "name": rule_name,
                "enabled": rule.enabled,
                "eligible": rule.enabled and tag_eligible,
                "eligibility_reason": (
                    "disabled"
                    if not rule.enabled
                    else "selected_by_tags"
                    if tag_eligible
                    else "excluded_by_tags"
                ),
                "tags": sorted(rule.tags),
                "targets": rule.targets,
                "locations": locations,
                "filter_mode": rule.filter_mode,
                "filters": filters,
                "actions": actions,
                "suspicious": suspicious,
            }
        )

    return {
        "schema": SCHEMA_VERSION,
        "config_path": str(config._config_path) if config._config_path else None,
        "working_directory": redact_text(str(working_dir)),
        "included_tags": sorted(selected_tags),
        "skipped_tags": sorted(excluded_tags),
        "rules": rules,
        "optional_dependencies": _optional_dependencies(all_filter_names),
        "risk_summary": sorted(global_risks),
        "limitations": [
            "Static explanation does not traverse locations or evaluate filters.",
            "Template values derived from a resource cannot be predicted until evaluation.",
            "External command, inline Python, filesystem permissions, races, and free space cannot be predicted statically.",
        ],
    }


def explain_json(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True)


def explain_human(report: dict[str, Any]) -> str:
    lines = [f"Configuration: {report['config_path'] or '[stdin]'}"]
    lines.append(f"Working directory: {report['working_directory']}")
    for rule in report["rules"]:
        state = (
            "ELIGIBLE"
            if rule["eligible"]
            else f"SKIPPED ({rule['eligibility_reason']})"
        )
        lines.append(f"\nRule {rule['index'] + 1}: {rule['name']} [{state}]")
        lines.append(
            f"  Targets: {rule['targets']} | filter mode: {rule['filter_mode']}"
        )
        if rule["tags"]:
            lines.append(f"  Tags: {', '.join(rule['tags'])}")
        for location in rule["locations"]:
            recursion = "recursive" if location["recursive"] else "top level only"
            lines.append(f"  Location: {location['path']} ({recursion})")
        for item in rule["filters"]:
            lines.append(f"  Filter {item['order']}: {item['name']} {item['options']}")
        for item in rule["actions"]:
            suffix = f" [RISK: {', '.join(item['risks'])}]" if item["risks"] else ""
            lines.append(
                f"  Action {item['order']}: {item['name']} - {item['mutation']}{suffix}"
            )
            if item["conflict_policy"]:
                lines.append(f"    Conflict policy: {item['conflict_policy']}")
        for warning in rule["suspicious"]:
            lines.append(f"  WARNING: {warning}")
    unavailable = [
        item["dependency"]
        for item in report["optional_dependencies"]
        if not item["available"]
    ]
    if unavailable:
        lines.append(f"\nUnavailable optional dependencies: {', '.join(unavailable)}")
    lines.append("\nStatic limitations:")
    lines.extend(f"  - {item}" for item in report["limitations"])
    return "\n".join(lines)
