"""Stable addon-owned Action Execution Proof adapter."""

from __future__ import annotations

from typing import Any

from .vendor import vendored_symbol


def record_action_execution_proof(
    organism: Any,
    control_id: str,
    *,
    action_id: str,
    attempted: bool,
    ok: bool,
    method: str | None,
    ref: str,
    reason: str,
    actor: str,
    authorship: str,
    timestamp: float,
    evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    """Append a complete BODY-authored proof without using private Limbs methods."""
    proof = {
        "control": control_id,
        "action_id": action_id,
        "attempted": attempted,
        "ok": ok,
        "method": method,
        "ref": ref,
        "reason": reason,
        "actor": actor,
        "authorship": authorship,
        "timestamp": timestamp,
        "evidence": evidence,
    }
    make_entry = vendored_symbol("vcw.entry", "make_entry")
    entry = make_entry(
        {"action_proof": proof},
        opcode="PROOF",
        author="BODY",
        authorship="BODY",
    )
    organism.limbs.append("brain", entry)
    return proof
