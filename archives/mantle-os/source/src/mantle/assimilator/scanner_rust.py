"""Pure-stdlib Rust fallback scanner.

This is intentionally conservative: it reports declarations and obvious runtime
evidence, while recording syntax it cannot parse instead of claiming completeness.
"""
from __future__ import annotations

import re
from typing import Any, Dict

_FN = re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*)")
_MOD = re.compile(r"^\s*(?:pub\s+)?mod\s+([A-Za-z_][A-Za-z0-9_]*)")
_IMPL = re.compile(r"^\s*impl(?:<[^>]+>)?\s+([A-Za-z_][A-Za-z0-9_:<>]*)")


def _role(name: str, body: str) -> str:
    low = (name + " " + body).lower()
    if name == "main" or "loop {" in low or "tokio::" in low:
        return "HEARTBEAT"
    if any(token in low for token in ("std::process", "command::new", "reqwest", "send(")):
        return "ARM_ACTION"
    if any(token in low for token in ("serde_json", "fs::write", "file::create", "sqlite")):
        return "PERSISTENCE_WRITE"
    if any(token in low for token in ("stdin", "args()", "clap::", "axum", "actix")):
        return "SENSOR_EVENT"
    if any(token in low for token in ("error", "result<", "unwrap_or", "validate")):
        return "ERROR_DEFENSE"
    return "INTERNAL_UTILITY"


def scan_file(path: str, rel: str) -> Dict[str, Any]:
    source = open(path, "r", encoding="utf-8", errors="replace").read()
    lines = source.splitlines()
    symbols = []
    gaps = []
    for index, line in enumerate(lines, 1):
        for matcher, kind in ((_MOD, "module"), (_IMPL, "impl"), (_FN, "function")):
            match = matcher.match(line)
            if match:
                name = match.group(1)
                body = "\n".join(lines[index - 1:index + 40])
                symbols.append({"symbol": name, "kind": kind, "line": index,
                                "role": _role(name, body), "evidence": ["stdlib-rust-regex"]})
                break
    if "macro_rules!" in source or "unsafe" in source:
        gaps.append("macro/unsafe semantics are not structurally expanded by fallback scanner")
    if not symbols and source.strip():
        gaps.append("no declarations recognized by conservative fallback")
    return {"module": rel, "symbols": symbols, "parser": "rust-stdlib-fallback",
            "coverage": "partial" if gaps else "complete", "gaps": gaps}

