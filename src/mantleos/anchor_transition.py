"""Proposed, implementation-independent Anchor transition-trace validator.

Data-only: cannot execute Anchors, authenticate provenance, authorize host
effects, measure model accuracy, or grant Baker acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

SCHEMA = "anchor.transition-trace/1"
MAX_BYTES = 2_000_000
IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,95}$")
DECISIONS = {"admit", "reject", "undetermined"}
TRANSITIONS = {"changed", "unchanged", "undetermined"}
EFFECT_STATUSES = {"predicted", "observed-success", "observed-failure", "unknown"}
EVIDENCE = {"reference", "model", "host", "reviewer", "none"}


class TraceError(ValueError):
    """The supplied trace is not a valid data-only transition record."""


def _exact(value, fields, where):
    if type(value) is not dict or set(value) != set(fields):
        raise TraceError(f"{where}: expected exactly {', '.join(fields)}")
    return value


def _id(value, where):
    if type(value) is not str or not IDENTIFIER.fullmatch(value):
        raise TraceError(f"{where}: invalid identifier")


def _pairs(items):
    output = {}
    for key, entry in items:
        if key in output:
            raise TraceError(f"duplicate JSON member: {key}")
        output[key] = entry
    return output


def loads(raw: bytes | str):
    if type(raw) is str:
        raw = raw.encode("utf-8")
    if len(raw) > MAX_BYTES:
        raise TraceError("trace exceeds 2 MB")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                          parse_constant=lambda x: (_ for _ in ()).throw(TraceError(f"invalid constant {x}")))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise TraceError("invalid UTF-8 JSON") from error


def fingerprint(value):
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _same(left, right):
    """JSON-aware equality distinguishes booleans from numeric values."""
    return fingerprint(left) == fingerprint(right)


def validate(value):
    """Validate the envelope and declared state continuity, not semantic truth."""
    _exact(value, ("schema", "authority", "baker_acceptance", "contract_ref",
                   "initial_state", "steps", "final_state"), "trace")
    if (value["schema"], value["authority"], value["baker_acceptance"]) != (
        SCHEMA, "NONE", "NOT_GRANTED"
    ):
        raise TraceError("unsupported schema or authority claim")
    if type(value["contract_ref"]) is not str or not value["contract_ref"]:
        raise TraceError("contract_ref must identify a proposed source contract")
    if type(value["initial_state"]) is not dict or type(value["final_state"]) is not dict:
        raise TraceError("initial_state and final_state must be objects")
    steps = value["steps"]
    if type(steps) is not list or not 1 <= len(steps) <= 256:
        raise TraceError("steps must contain 1..256 entries")

    previous = value["initial_state"]
    seen = set()
    for n, step in enumerate(steps):
        where = f"steps[{n}]"
        _exact(step, ("id", "stimulus", "before", "gate", "transition",
                      "after", "effects", "output", "evidence"), where)
        _id(step["id"], where + ".id")
        if step["id"] in seen:
            raise TraceError(where + ": duplicate id")
        seen.add(step["id"])
        _exact(step["stimulus"], ("action", "payload"), where + ".stimulus")
        _id(step["stimulus"]["action"], where + ".stimulus.action")
        if type(step["stimulus"]["payload"]) is not dict:
            raise TraceError(where + ".stimulus.payload must be an object")
        _exact(step["gate"], ("family", "decision", "clauses"), where + ".gate")
        _id(step["gate"]["family"], where + ".gate.family")
        if step["gate"]["decision"] not in DECISIONS:
            raise TraceError(where + ".gate.decision is invalid")
        clauses = step["gate"]["clauses"]
        if (type(clauses) is not list or not clauses
            or any(type(x) is not str or not IDENTIFIER.fullmatch(x) for x in clauses)
            or len(clauses) != len(set(clauses))):
            raise TraceError(where + ".gate.clauses must be distinct IDs")
        if type(step["before"]) is not dict or not _same(step["before"], previous):
            raise TraceError(where + ": state-continuity mismatch")
        if step["transition"] not in TRANSITIONS:
            raise TraceError(where + ".transition is invalid")
        unknown = (step["gate"]["decision"] == "undetermined"
                   or step["transition"] == "undetermined")
        if unknown:
            if (step["gate"]["decision"] != "undetermined"
                or step["transition"] != "undetermined"
                or step["after"] is not None):
                raise TraceError(where + ": undetermined needs null after and matching labels")
            if n != len(steps) - 1 or not _same(value["final_state"], previous):
                raise TraceError(where + ": undetermined must terminate at last known state")
        else:
            if type(step["after"]) is not dict:
                raise TraceError(where + ".after must be an object")
            changed = not _same(step["after"], step["before"])
            if changed != (step["transition"] == "changed"):
                raise TraceError(where + ": transition label disagrees with snapshots")
            if step["gate"]["decision"] == "reject" and changed:
                raise TraceError(where + ": rejected command cannot commit state")
            previous = step["after"]
        if type(step["effects"]) is not list or len(step["effects"]) > 32:
            raise TraceError(where + ".effects must be a list of at most 32")
        for effect in step["effects"]:
            _exact(effect, ("id", "status", "evidence_ref"), where + ".effect")
            _id(effect["id"], where + ".effect.id")
            if effect["status"] not in EFFECT_STATUSES:
                raise TraceError(where + ".effect.status is invalid")
            ref = effect["evidence_ref"]
            if ref is not None and (type(ref) is not str or not ref):
                raise TraceError(where + ".effect.evidence_ref is invalid")
            if effect["status"].startswith("observed-") and ref is None:
                raise TraceError(where + ": observed effect needs evidence_ref")
        if step["output"] is not None and type(step["output"]) is not dict:
            raise TraceError(where + ".output must be an object or null")
        _exact(step["evidence"], ("kind", "ref"), where + ".evidence")
        if step["evidence"]["kind"] not in EVIDENCE:
            raise TraceError(where + ".evidence.kind is invalid")
        ref = step["evidence"]["ref"]
        if ref is not None and (type(ref) is not str or not ref):
            raise TraceError(where + ".evidence.ref is invalid")
        if step["evidence"]["kind"] == "none" and ref is not None:
            raise TraceError(where + ".evidence.none cannot reference evidence")
    if not _same(previous, value["final_state"]):
        raise TraceError("final_state differs from the last known state")
    return {"status": "passed", "kind": SCHEMA, "steps": len(steps),
            "source_sha256": fingerprint(value), "authority": "NONE",
            "baker_acceptance": "NOT_GRANTED", "semantic_execution": "NOT_PERFORMED"}


def validate_bytes(raw: bytes):
    return validate(loads(raw))


def main():
    parser = argparse.ArgumentParser(description="Validate proposed Anchor trace data")
    parser.add_argument("trace", type=Path)
    args = parser.parse_args()
    try:
        result = validate_bytes(args.trace.read_bytes())
    except (OSError, TraceError, ValueError, TypeError) as error:
        print(json.dumps({"status": "rejected", "message": str(error), "authority": "NONE"}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
