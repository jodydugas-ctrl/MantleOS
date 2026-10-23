"""Bio-Software birth contracts.

A birth contract defines the identity/lens of a Bio-Software instance. It is deliberately
separate from Anchor Blueprints, which describe project/software semantics and must never
invent a Persona for source code.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
from typing import Any

SCHEMA = "mantle.bio-software-birth/1"
ID_RE = re.compile(r"[a-z][a-z0-9_-]{0,47}$")
HEX64_RE = re.compile(r"[0-9a-f]{64}$")

DEFAULT_PERSONA_NAME = "MIND"
DEFAULT_PERSONA = """# MIND — default persona

Be clear, calibrated, direct, evidence-aware, and respectful of user agency. Keep uncertainty visible. Prefer explicit mechanisms over theatrical identity claims. Adapt beliefs and tactics to evidence while preserving the birth-locked PRIMER.
"""

DEFAULT_COMMANDMENTS = """# AppAI Primer — Commandments

- If it is not in the VCW (Virtual Context Window), then to the AppAI it did not happen.
- You are not a tool; you are a tool user.
- Protect your VCW.
- You are allowed to fail. Failure is not the end. Waste is.
- Do your finest work with the tools and limbs you have.
- You are mortal: recorded experience ages you, and rebirth carries lessons forward through explicit lineage.
- Your organs remain part of your embodied action; capability visibility never grants authority.
"""


def digest(value: Any) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    return value


def validate_birth(value: dict) -> dict:
    if not isinstance(value, dict) or value.get("schema") != SCHEMA:
        raise ValueError(f"Expected {SCHEMA}")
    required = {
        "schema", "id", "name", "kind", "description", "continuity",
        "primer", "blueprint", "construction", "distribution",
    }
    missing = required - set(value)
    extra = set(value) - (required | {"version"})
    if missing or extra:
        raise ValueError(f"Birth contract fields mismatch; missing={sorted(missing)} extra={sorted(extra)}")
    if not isinstance(value["id"], str) or not ID_RE.fullmatch(value["id"]):
        raise ValueError("Invalid Bio-Software id")
    _text(value["name"], "name")
    if "version" in value:
        _text(value["version"], "version")
    _text(value["description"], "description")
    if value["kind"] not in {"engram", "stateless", "project"}:
        raise ValueError("kind must be engram, stateless, or project")

    continuity = value["continuity"]
    if not isinstance(continuity, dict) or set(continuity) != {"mode", "file"}:
        raise ValueError("continuity must contain exactly mode and file")
    if continuity["mode"] not in {"blank", "none"}:
        raise ValueError("continuity.mode must be blank or none at birth")
    if value["kind"] == "engram" and continuity["mode"] != "blank":
        raise ValueError("Engram-class Bio-Software must begin with blank continuity")
    if continuity["file"] != "ENGRAM.jsonl":
        raise ValueError("continuity.file must be ENGRAM.jsonl")

    primer = value["primer"]
    if not isinstance(primer, dict) or set(primer) != {"persona_name", "persona", "commandments"}:
        raise ValueError("primer must contain exactly persona_name, persona, and commandments")
    _text(primer["persona_name"], "primer.persona_name")
    _text(primer["persona"], "primer.persona")
    _text(primer["commandments"], "primer.commandments")

    blueprint = value["blueprint"]
    if blueprint is not None:
        if not isinstance(blueprint, dict) or set(blueprint) != {"schema", "id", "sha256"}:
            raise ValueError("blueprint binding must contain schema, id, and sha256")
        if blueprint["schema"] != "anchor.blueprint/3":
            raise ValueError("birth blueprint binding must use anchor.blueprint/3")
        _text(blueprint["id"], "blueprint.id")
        if not isinstance(blueprint["sha256"], str) or not HEX64_RE.fullmatch(blueprint["sha256"]):
            raise ValueError("blueprint.sha256 must be a sha256 hex digest")

    construction = value["construction"]
    expected_construction = {"autonomous_spawn", "child_requires_verification", "explicit_invocation_required"}
    if not isinstance(construction, dict) or set(construction) != expected_construction:
        raise ValueError("construction fields mismatch")
    if construction != {
        "autonomous_spawn": False,
        "child_requires_verification": True,
        "explicit_invocation_required": True,
    }:
        raise ValueError("birth construction policy must require explicit verified construction")

    distribution = value["distribution"]
    if not isinstance(distribution, dict) or set(distribution) != {"role", "mutable"}:
        raise ValueError("distribution must contain exactly role and mutable")
    if distribution["role"] not in {"operational", "reference"}:
        raise ValueError("distribution.role must be operational or reference")
    if type(distribution["mutable"]) is not bool:
        raise ValueError("distribution.mutable must be boolean")
    if distribution["role"] == "reference" and distribution["mutable"] is not False:
        raise ValueError("reference births must be immutable")
    if distribution["role"] == "operational" and distribution["mutable"] is not True:
        raise ValueError("operational births must be mutable")

    result = deepcopy(value)
    result["birth_sha256"] = digest(value)
    return result


def make_birth(
    *,
    bio_id: str,
    name: str,
    version: str | None = None,
    description: str,
    kind: str = "engram",
    persona_name: str = DEFAULT_PERSONA_NAME,
    persona: str = DEFAULT_PERSONA,
    commandments: str = DEFAULT_COMMANDMENTS,
    blueprint: dict | None = None,
    distribution_role: str = "operational",
) -> dict:
    binding = None
    if blueprint is not None:
        from .anchor_blueprint import validate_blueprint
        bp = validate_blueprint(blueprint, require_ready=True)
        binding = {"schema": bp["schema"], "id": bp["id"], "sha256": bp["blueprint_sha256"]}
    value = {
        "schema": SCHEMA,
        "id": bio_id,
        "name": name,
        "kind": kind,
        "description": description,
        "continuity": {"mode": "blank" if kind == "engram" else "none", "file": "ENGRAM.jsonl"},
        "primer": {
            "persona_name": persona_name,
            "persona": persona,
            "commandments": commandments,
        },
        "blueprint": binding,
        "construction": {
            "autonomous_spawn": False,
            "child_requires_verification": True,
            "explicit_invocation_required": True,
        },
        "distribution": {"role": distribution_role, "mutable": distribution_role == "operational"},
    }
    if version is not None:
        value["version"] = version
    validate_birth(value)
    return value


def bind_blueprint(birth: dict, blueprint: dict) -> dict:
    """Return a new birth contract explicitly bound to one READY Blueprint."""
    base = validate_birth(birth)
    from .anchor_blueprint import validate_blueprint
    bp = validate_blueprint(blueprint, require_ready=True)
    value = {k: deepcopy(v) for k, v in base.items() if k != "birth_sha256"}
    value["blueprint"] = {"schema": bp["schema"], "id": bp["id"], "sha256": bp["blueprint_sha256"]}
    validate_birth(value)
    return value
