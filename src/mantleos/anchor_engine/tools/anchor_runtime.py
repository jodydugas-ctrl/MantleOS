"""Strict standard-library reference interpreter for EMIT_TEXT/0.2.

The primer is authoritative for LLM cold reads; the interpreter implements this
one pinned profile only. Do not use this runtime to infer undefined Anchor rules.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIMER_PATH = ROOT / "templates" / "primer_emit_text_v0_2.txt"
PRIMER_PATHS = {"EMIT_TEXT/0.2": PRIMER_PATH}

NAME = r"[A-Za-z][A-Za-z0-9_]*"
ID = r"[A-Za-z][A-Za-z0-9_-]*"
ANCHOR_PATTERN = re.compile(rf"({ID}): (BlackHole|WhiteHole|Neutral) -([0-9A-F]{{2}}) -([0-9A-F]{{2}}) -(.*)")
DOC_PATTERN = re.compile(
    rf"ANCHOR BLUEPRINT: ({NAME})\n"
    r"STATUS: EXPERIMENTAL (EMIT_TEXT/0\.2)\n\n"
    r"(BEGIN ANCHOR EXECUTION PRIMER\n.*?\nEND ANCHOR EXECUTION PRIMER)\n\n"
    rf"BEGIN MOLECULE ({NAME})\n(.*?)\nEND MOLECULE\n\n"
    rf"BEGIN EXECUTION\nRUN ({NAME})\nEND EXECUTION\n?",
    re.DOTALL,
)


class AnchorExecutionError(ValueError):
    """Malformed, undefined, or contradictory Blueprint; no result emitted."""


def run_blueprint(source: str) -> list[str]:
    """Parse and execute a Blueprint, returning literal data units in order."""
    if not isinstance(source, str) or len(source.encode('utf-8')) > 1_048_576:
        raise AnchorExecutionError('Anchor source missing or oversized')
    if not source.endswith('\n') or '\r' in source:
        raise AnchorExecutionError('Anchor source needs LF line endings and final newline')
    match = DOC_PATTERN.fullmatch(source)
    if match is None:
        raise AnchorExecutionError("Invalid Blueprint structure or unsupported profile")
    header_name, profile, primer, molecule_name, body, run_name = match.groups()
    if not (header_name == molecule_name == run_name):
        raise AnchorExecutionError("RUN, Molecule, and Blueprint names must match")
    if profile not in PRIMER_PATHS or primer != PRIMER_PATHS[profile].read_text(encoding="utf-8").rstrip("\n"):
        raise AnchorExecutionError(f"Primer differs from pinned {profile} profile")
    lines = body.split("\n")
    if not lines or any(not line for line in lines):
        raise AnchorExecutionError("Molecule requires nonempty Anchor lines")
    emitted: list[str] = []
    seen: set[str] = set()
    for line in lines:
        anchor = ANCHOR_PATTERN.fullmatch(line)
        if anchor is None:
            raise AnchorExecutionError(f"Malformed Anchor: {line!r}")
        aid, kind, opcode, mass, variable = anchor.groups()
        if len(aid) > 64 or len(seen) >= 128:
            raise AnchorExecutionError('KPP profile Anchor count or identifier limit exceeded')
        if aid in seen:
            raise AnchorExecutionError(f"Duplicate Anchor ID: {aid}")
        seen.add(aid)
        if (kind, opcode, mass) != ("Neutral", "01", "00"):
            raise AnchorExecutionError(f"Undefined Anchor operation: {kind} -{opcode} -{mass}")
        if not variable.startswith("text="):
            raise AnchorExecutionError("EMIT_TEXT requires text=<JSON_STRING>")
        try:
            value = json.loads(variable[5:])
        except json.JSONDecodeError as exc:
            raise AnchorExecutionError("Invalid JSON string") from exc
        if not isinstance(value, str) or any(0xD800 <= ord(c) <= 0xDFFF for c in value):
            raise AnchorExecutionError("EMIT_TEXT must contain Unicode scalar text")
        emitted.append(value)
    if len(''.join(emitted).encode('utf-8')) > 1_048_576:
        raise AnchorExecutionError('Anchor output exceeds KPP profile limit')
    return emitted


def render_hello_world(name: str = "HelloWorld", text: str = "Hello, World!",
                       profile: str = "EMIT_TEXT/0.2") -> str:
    """Fast generator: reuse one tested primer, escape literals as JSON."""
    if re.fullmatch(NAME, name) is None:
        raise ValueError("Invalid Molecule name")
    if not isinstance(text, str) or any(0xD800 <= ord(c) <= 0xDFFF for c in text):
        raise ValueError("Text must contain Unicode scalar values")
    if profile not in PRIMER_PATHS:
        raise ValueError(f"Unsupported profile: {profile}")
    primer = PRIMER_PATHS[profile].read_text(encoding="utf-8").rstrip("\n")
    literal = json.dumps(text, ensure_ascii=False)
    return (f"ANCHOR BLUEPRINT: {name}\n"
            f"STATUS: EXPERIMENTAL {profile}\n\n"
            f"{primer}\n\n"
            f"BEGIN MOLECULE {name}\n"
            f"A: Neutral -01 -00 -text={literal}\n"
            "END MOLECULE\n\n"
            f"BEGIN EXECUTION\nRUN {name}\nEND EXECUTION\n")


def program_stdout(source: str) -> str:
    """Render exact program output for the pinned profile (no implicit UI prose)."""
    values = run_blueprint(source)
    return "".join(values)
