#!/usr/bin/env python3
"""
mantle.core.redact  --  the secret boundary (Mantle OS)

A deterministic, LLM-free redactor applied at the sense/immune logging boundary so that
secrets NEVER land in the VCW (HF-B20). The cube is append-only and inspectable as images --
a leaked secret there is permanent and visible. Redaction happens once, at the boundary,
before any append. Intentionally conservative (mask on suspicion): a false positive only
obscures a log line; a false negative permanently burns a secret into memory.
"""
from __future__ import annotations

import re
from typing import Any

MASK = "[REDACTED]"

# A dict key whose NAME matches this is a secret holder -- its whole value is masked.
_KEY_RE = re.compile(r"(?i)(api[_-]?key|secret|token|password|passwd|private[_-]?key|"
                     r"access[_-]?key|auth)")

_RULES = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
                re.DOTALL), MASK),
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._\-]{8,}"), "Bearer " + MASK),
    (re.compile(r"(?i)\b([\w-]*(?:api[_-]?key|secret|token|password|passwd|auth|access[_-]?key)"
                r"[\w-]*)\b\s*[:=]\s*[\"']?([^\s\"',;}]{4,})[\"']?"), r"\1=" + MASK),
    (re.compile(r"\bsk-[A-Za-z0-9]{16,}\b"), MASK),
    (re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{12,}\b"), MASK),
    (re.compile(r"\beyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\b"), MASK),
    (re.compile(r"\b[0-9a-fA-F]{32,}\b"), MASK),
    (re.compile(r"\b[A-Za-z0-9+/]{40,}={0,2}\b"), MASK),
]


def redact_str(s: str) -> str:
    for pat, repl in _RULES:
        s = pat.sub(repl, s)
    return s


def redact(obj: Any) -> Any:
    """Return a redacted deep copy. Strings are scrubbed; dict/list are walked; dict keys
    whose NAME looks secret have their whole value masked, regardless of shape."""
    if isinstance(obj, str):
        return redact_str(obj)
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if _KEY_RE.search(str(k)):
                out[k] = MASK
            else:
                out[k] = redact(v)
        return out
    if isinstance(obj, (list, tuple)):
        return type(obj)(redact(v) for v in obj)
    return obj


def contains_secret(obj: Any) -> bool:
    """True if redact(obj) would change anything. Used by audits to prove the boundary."""
    return redact(obj) != obj
