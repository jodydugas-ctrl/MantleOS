"""Resumable prebirth construction gates.

Approval is bound to an exact shell-free execution plan. This module does not
execute the foreign plan: an approved sandbox runner must do that and attach
native receipts before the host-behavior gate can become verified.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = "mantle.foreign-execution-plan.v2"


class ConstructionError(RuntimeError):
    """A prebirth workflow transition could not be proven safe."""


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _digest_payload(value: dict[str, Any]) -> str:
    payload = {key: item for key, item in value.items() if key != "plan_sha256"}
    return hashlib.sha256(_canonical(payload)).hexdigest()


def create_execution_plan(manifest: dict[str, Any]) -> dict[str, Any]:
    baseline = manifest["body_map"]["behavior_baseline"]
    commands = []
    for item in baseline.get("candidate_commands", []):
        argv = item.get("argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(arg, str) for arg in argv):
            continue
        commands.append(
            {
                "purpose": item.get("purpose", "host-verification"),
                "argv": argv,
                "working_directory": ".",
                "timeout_seconds": 900,
            }
        )
    plan = {
        "schema": SCHEMA,
        "source_commit": manifest["source"]["commit"],
        "source_tree": manifest["source"]["tree"],
        "body_map_sha256": manifest["body_map"]["map_sha256"],
        "commands": commands,
        "shell": False,
        "network": {
            "default": "disabled",
            "allowed_domains": [],
            "dependency_fetch_requires_reapproval": True,
        },
        "resources": {
            "max_command_seconds": 900,
            "max_output_bytes": 2_000_000,
            "max_artifact_bytes": 1_000_000_000,
        },
        "sandbox": {
            "required": True,
            "acceptable_backends": ["docker", "podman", "externally-attested"],
            "run_as_non_admin": True,
            "source_mount": "read-only-for-baseline",
            "generated_output": "outside-source-tree",
        },
        "approval": "required-before-any-command",
    }
    plan["plan_sha256"] = _digest_payload(plan)
    return plan


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConstructionError(f"Construction record is unreadable: {path.name}") from exc
    if not isinstance(value, dict):
        raise ConstructionError(f"Construction record is not an object: {path.name}")
    return value


def _sandbox_backend() -> str | None:
    for name in ("docker", "podman"):
        if shutil.which(name):
            return name
    return None


def approve_foreign_execution(nest: Path, *, approved: bool) -> dict[str, Any]:
    """Bind approval to the current source, Body Map, and execution plan."""
    if not approved:
        raise ConstructionError("Foreign execution requires explicit approval")
    nest = nest.resolve()
    plan_path = nest / "mantle" / "maps" / "EXECUTION_PLAN.json"
    prebirth_path = nest / ".mantle" / "prebirth.json"
    plan = _load_json(plan_path)
    prebirth = _load_json(prebirth_path)
    if plan.get("schema") != SCHEMA or plan.get("plan_sha256") != _digest_payload(plan):
        raise ConstructionError("The foreign execution plan changed or has an unknown schema")
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=nest,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ConstructionError("The NEST source revision cannot be verified") from exc
    if commit != plan.get("source_commit"):
        raise ConstructionError("The NEST source revision changed after the execution plan was made")
    backend = _sandbox_backend()
    receipt = {
        "schema": "mantle.foreign-execution-approval.v2",
        "approved_at": _now(),
        "plan_sha256": plan["plan_sha256"],
        "source_commit": commit,
        "sandbox_backend": backend,
        "authority": "user-approved",
        "executes_foreign_code": False,
    }
    approval_path = nest / ".mantle" / "construction" / "foreign-execution-approval.json"
    approval_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = approval_path.with_name(approval_path.name + ".tmp")
    temporary.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8", newline="\n")
    temporary.replace(approval_path)
    prebirth.setdefault("approvals", {})["foreign_code_execution"] = {
        "status": "approved",
        "plan_sha256": plan["plan_sha256"],
        "approved_at": receipt["approved_at"],
    }
    prebirth.setdefault("gates", {})["host_behavior"] = (
        "foreign-execution-approved" if backend else "sandbox-unavailable"
    )
    temporary = prebirth_path.with_name(prebirth_path.name + ".tmp")
    temporary.write_text(json.dumps(prebirth, indent=2) + "\n", encoding="utf-8", newline="\n")
    temporary.replace(prebirth_path)
    return {
        **receipt,
        "status": prebirth["gates"]["host_behavior"],
        "next": (
            "run the exact plan through the sandbox verifier"
            if backend
            else "provide a supported isolated runner; foreign code was not executed"
        ),
    }
