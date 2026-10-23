"""Anchor program qualification; no model or effect authority.

Only the exact, source-pinned EMIT_TEXT profiles are qualified for deterministic
non-effectful program output.  This module deliberately does not invent an Anchor
IR, dispatch arbitrary host commands, or turn a compiled target into source truth.
"""
from __future__ import annotations

import hashlib

from .anchor_language import verify_source_pins, source_directory
from .anchor_engine.tools.anchor_runtime import AnchorExecutionError, program_stdout
from .anchor_engine.tools.anchor_compile import translate

ARTIFACT_SCHEMA = "mantle.anchor-program-receipt/1"
_SUPPORTED = {
    "EMIT_TEXT/0.2": "templates/primer_emit_text_v0_2.txt",
}
MAX_SOURCE_BYTES = 65_536
MAX_STDOUT_BYTES = 131_072


def qualify_program(source: str, *, profile: str = "EMIT_TEXT/0.2") -> dict:
    """Verify a self-contained source program, producing a read-only receipt.

    This is local deterministic qualification, **not** permission to publish,
    write an Engram record, run Python, or claim independent model competence.
    """
    if profile not in _SUPPORTED:
        raise ValueError("UNSUPPORTED_PROFILE: no qualified native admission contract")
    if not isinstance(source, str):
        raise ValueError("Native Anchor source must be text")
    encoded = source.encode("utf-8")
    if not encoded or len(encoded) > MAX_SOURCE_BYTES:
        raise ValueError("Native Anchor source exceeds size budget or is empty")
    # Always verify the entire frozen implementation before interpreting a candidate.
    verify_source_pins()
    lines = source.splitlines()
    if len(lines) < 2 or not lines[0].startswith("ANCHOR BLUEPRINT: ") or lines[1] != f"STATUS: EXPERIMENTAL {profile}":
        raise ValueError("Anchor program profile does not match requested contract")
    try:
        stdout = program_stdout(source)
        target = translate(source)  # Compilation only. NEVER execute generated code here.
    except (AnchorExecutionError, UnicodeError) as exc:
        raise ValueError("Invalid native Anchor program") from exc
    output = stdout.encode("utf-8")
    if len(output) > MAX_STDOUT_BYTES:
        raise ValueError("Anchor program output exceeds size budget")
    template = source_directory() / _SUPPORTED[profile]
    return {
        "schema": ARTIFACT_SCHEMA,
        "language": "Anchor Coding",
        "profile": profile,
        "source_sha256": hashlib.sha256(encoded).hexdigest(),
        "profile_primer_sha256": hashlib.sha256(template.read_bytes()).hexdigest(),
        "stdout_sha256": hashlib.sha256(output).hexdigest(),
        "stdout_bytes": len(output),
        "compiled_target": "python-derived-non-authoritative",
        "compiled_sha256": hashlib.sha256(target.encode("utf-8")).hexdigest(),
        "scope": "local-deterministic-non-effectful-validation",
        "authority": "NONE_FROM_SOURCE_OR_RECEIPT",
    }
