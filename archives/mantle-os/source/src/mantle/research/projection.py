"""Derived Grimoire v0.10 projections for canonical research receipts."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping, Optional

from ..vcw.grimoire_editions.v010 import decode_statement, parity_pixel


PROFILE = "grimoire-v0.10"
DEFAULT_STEPS = (
    "establish baseline", "propose one candidate", "materialize candidate",
    "run immutable evaluator", "measure", "compare with baseline or parent",
    "append receipt", "request keep, discard, or another bounded trial",
)


class ResearchProjectionError(ValueError):
    """A derived projection could not be structurally represented."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


def _procedure_raw(step_count: int) -> bytes:
    if not 1 <= step_count <= 16:
        raise ResearchProjectionError("a Grimoire procedure needs between 1 and 16 steps")
    records = [(index, 0x60 + index - 1, 0, 0) for index in range(1, step_count + 1)]
    records.append(parity_pixel(records))
    return b"".join(bytes(record) for record in records)


def _labels(receipt: Mapping[str, Any]) -> tuple[str, str]:
    kind = str(receipt.get("kind", receipt.get("event", ""))).lower()
    if "hypothesis" in kind or "proposal" in kind:
        return "INFERRED", "MAY"
    if "charter" in kind:
        return "STIPULATED", "WAY"
    if "safety" in kind or "prohibition" in kind:
        return "STIPULATED", "NEVER"
    if "evaluator" in kind:
        return "STIPULATED", "GATE"
    if "external" in kind or "source" in kind:
        return "CITED", "QUOTE"
    if "adoption" in kind:
        return "DIRECT", "GATE"
    return "MEASURED", "WAY"


def _adoption(receipt: Mapping[str, Any]) -> dict[str, Any]:
    # A score, eligibility flag, or projection itself can never mint governing authority.
    explicit = receipt.get("authority_event")
    if isinstance(explicit, Mapping) and explicit.get("operator_authorized") is True:
        return {"status": "authorized-recorded", "governing": True,
                "authority": "separate-operator-event"}
    return {"status": "data", "governing": False, "authority": "none"}


def project_receipt(receipt: Mapping[str, Any], *, frame_id: str,
                    container_evidence: Optional[str] = None,
                    container_force: Optional[str] = None,
                    procedure_steps: Optional[Iterable[str]] = None) -> dict[str, Any]:
    """Return a derived projection while retaining the canonical record unchanged."""
    if not isinstance(receipt, Mapping):
        raise ResearchProjectionError("research receipt must be an object")
    canonical_record = json.loads(json.dumps(dict(receipt), ensure_ascii=False, sort_keys=True))
    steps = list(DEFAULT_STEPS if procedure_steps is None else procedure_steps)
    base: dict[str, Any] = {
        "profile": PROFILE, "frame_id": frame_id,
        "canonical_record": canonical_record,
        "canonical_record_hash": _hash(canonical_record),
        "semantic_projection_status": "failed", "adoption": _adoption(receipt),
    }
    try:
        raw = _procedure_raw(len(steps))
        decoded = decode_statement(
            raw, profile=PROFILE, frame_id=frame_id,
            container_evidence=container_evidence, container_force=container_force,
            container_frame_id=frame_id + ":container",
        )
        evidence, force = _labels(receipt)
        base.update({
            "raw": raw.hex(), "raw_fingerprint": _hash({"frame_id": frame_id, "raw": raw.hex()}),
            "normalized_interpretation": {"steps": steps, "evidence": evidence, "force": force,
                                           "authority_source": "canonical-json"},
            "decoded": decoded, "semantic_projection_status": "ok",
        })
        return base
    except (TypeError, ValueError, KeyError, ResearchProjectionError) as exc:
        base["projection_error"] = str(exc)
        return base


def project_procedure(steps: Iterable[str], *, frame_id: str,
                      container_evidence: Optional[str] = None,
                      container_force: Optional[str] = None) -> dict[str, Any]:
    steps = list(steps)
    return project_receipt(
        {"kind": "research_procedure", "steps": steps}, frame_id=frame_id,
        container_evidence=container_evidence, container_force=container_force,
        procedure_steps=steps,
    )
