#!/usr/bin/env python3
"""
mantle.assimilator.scanner  --  read-only AST dissection of a host codebase (Mantle OS)

Path B, Phase 0/1: BEFORE any hook is inserted, the host is dissected READ-ONLY. The
scanner walks a Python project, parses every module, and classifies every meaningful
symbol (function, method, class) into exactly one ORGAN ROLE:

  REFLEX             Senses   a pure, deterministic reaction
  SENSOR_EVENT       Senses   receives external input (routes, handlers, listeners)
  ARM_ACTION         Limbs    performs an external action/effect (API calls, sends, motors)
  DISPLAY_RENDER     Limbs    renders human-visible output
  STATE_TRANSITION   Memory   mutates app state
  PERSISTENCE_WRITE  Memory   writes durable storage
  HEARTBEAT          Heart    the main loop / scheduler / clock
  MIND_AFFORDANCE    Brain    a judgment point (LLM/model call) -- dormant until Phase 2
  SECRET_BOUNDARY    Immune   crosses a credential/secret edge
  ERROR_DEFENSE      Immune   validation / error handling / retries
  INTERNAL_UTILITY   --       pure helper (instrument only if it touches the above)
  DEPRECATED         --       dead code (never instrumented)

Classification is deterministic: name patterns + call-graph evidence (which stdlib /
framework calls the body makes), no LLM, no execution of host code. The scanner NEVER
writes anything; its output feeds organ_map + report.

This module is the single canonical scanner/classifier for the whole framework: anchor,
graft, and the egg/RESURGERE reconstruct path all reuse it (no second copy exists). The
Grimoire is the VCW semantic software profile; scanner behavior is defined here and in the
Mantle assimilation docs.
"""
from __future__ import annotations

import ast
import os
from typing import Any, Dict, List

from .substrate import discover as discover_substrate

ROLES = ("REFLEX", "SENSOR_EVENT", "ARM_ACTION", "DISPLAY_RENDER", "STATE_TRANSITION",
         "PERSISTENCE_WRITE", "HEARTBEAT", "MIND_AFFORDANCE", "SECRET_BOUNDARY",
         "ERROR_DEFENSE", "INTERNAL_UTILITY", "DEPRECATED")

# ---- deterministic evidence tables ------------------------------------------------
_NAME_HINTS = [
    ("HEARTBEAT",        ("main_loop", "run_loop", "event_loop", "scheduler", "heartbeat",
                          "tick", "poll_loop", "mainloop", "run_forever")),
    ("SENSOR_EVENT",     ("handle", "on_", "webhook", "route", "listen", "receive",
                          "callback", "endpoint", "inbound", "consume")),
    ("ARM_ACTION",       ("send", "post", "publish", "dispatch", "notify", "call_api",
                          "execute", "actuate", "push", "upload", "emit")),
    ("DISPLAY_RENDER",   ("render", "draw", "display", "print_", "show", "format_output",
                          "view")),
    ("PERSISTENCE_WRITE",("save", "persist", "write_", "store", "insert", "update_db",
                          "flush", "dump", "commit")),
    ("STATE_TRANSITION", ("set_", "update_", "mutate", "transition", "apply_", "reset")),
    ("SECRET_BOUNDARY",  ("auth", "login", "credential", "token", "secret", "api_key",
                          "password", "keyfile")),
    ("ERROR_DEFENSE",    ("validate", "verify", "check_", "retry", "sanitize", "guard")),
    ("MIND_AFFORDANCE",  ("llm", "gpt", "claude", "model_call", "complete", "decide",
                          "judge", "infer", "prompt")),
]

_CALL_HINTS = [
    ("ARM_ACTION",        ("requests.", "urllib", "httpx", "socket.", "subprocess",
                           "smtplib", "boto3")),
    ("PERSISTENCE_WRITE", ("open(", "json.dump", "pickle.dump", "sqlite3", "cursor.execute",
                           ".write(", "shutil.")),
    ("DISPLAY_RENDER",    ("print(",)),
    ("HEARTBEAT",         ("while True", "time.sleep", "sched.", "asyncio.run")),
    ("MIND_AFFORDANCE",   ("openai", "anthropic", "langchain", "chat.completions")),
    ("SECRET_BOUNDARY",   ("os.environ", "getpass", "keyring")),
]


def _src_of(node: ast.AST, source_lines: List[str]) -> str:
    try:
        return "\n".join(source_lines[node.lineno - 1:node.end_lineno])
    except Exception:
        return ""


def classify_symbol(name: str, body_src: str, decorators: List[str]) -> str:
    """Deterministic role for one symbol: decorators, then name hints, then call hints."""
    low = name.lower()
    decos = " ".join(decorators).lower()
    if "deprecated" in low or "deprecated" in decos:
        return "DEPRECATED"
    if any(d in decos for d in ("route", "get(", "post(", "websocket", "on_event",
                                "listener", "subscribe")):
        return "SENSOR_EVENT"
    for role, hints in _NAME_HINTS:
        if any(h in low for h in hints):
            return role
    src = body_src.lower()
    for role, hints in _CALL_HINTS:
        if any(h.lower() in src for h in hints):
            return role
    return "INTERNAL_UTILITY"


def scan_file(path: str, rel: str) -> Dict[str, Any]:
    """Scan one Python file READ-ONLY. Returns {module, symbols, error?}."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        source = f.read()
    out: Dict[str, Any] = {"module": rel, "symbols": []}
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        out["error"] = "syntax: %s" % e
        return out
    lines = source.splitlines()

    def walk(node: ast.AST, prefix: str = "") -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                decos = [ast.dump(d) for d in child.decorator_list]
                role = classify_symbol(child.name, _src_of(child, lines), decos)
                out["symbols"].append({
                    "symbol": prefix + child.name, "kind": "function",
                    "line": child.lineno, "role": role})
                walk(child, prefix + child.name + ".")
            elif isinstance(child, ast.ClassDef):
                out["symbols"].append({
                    "symbol": prefix + child.name, "kind": "class",
                    "line": child.lineno, "role": "INTERNAL_UTILITY"})
                walk(child, prefix + child.name + ".")

    walk(tree)
    return out


def scan_project(root: str) -> Dict[str, Any]:
    """Scan a host project directory READ-ONLY. Returns the raw dissection: every
    Python module's symbols with deterministic organ roles, plus any .js/.mjs/.go/.rs
    modules if the optional tree-sitter scanner (scanner_ts) is installed. Modifies
    NOTHING."""
    try:
        from . import scanner_ts
        multilang = scanner_ts.available()
    except ImportError:
        scanner_ts = None
        multilang = False

    substrate = discover_substrate(root)
    files: List[Dict[str, Any]] = []
    py_count = 0
    native_count = 0
    gap_count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in (".git", "__pycache__", "node_modules", ".venv", "venv")]
        for fn in sorted(filenames):
            full = os.path.join(dirpath, fn)
            if fn.endswith(".py"):
                py_count += 1
                files.append(scan_file(full, os.path.relpath(full, root)))
            elif multilang and os.path.splitext(fn)[1].lower() in scanner_ts.LANGS:
                files.append(scanner_ts.scan_file(full, os.path.relpath(full, root)))
            elif os.path.splitext(fn)[1].lower() == ".rs":
                # Rust remains inspectable when tree-sitter is unavailable; the
                # fallback reports its limitations explicitly in the result.
                from . import scanner_rust
                files.append(scanner_rust.scan_file(full, os.path.relpath(full, root)))
            elif (os.path.splitext(fn)[1].lower() in
                  {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".m", ".mm",
                   ".ui", ".qrc", ".cmake"} or fn.lower() == "cmakelists.txt"):
                from . import scanner_native
                scanned = scanner_native.scan_file(full, os.path.relpath(full, root))
                files.append(scanned)
                native_count += 1
                gap_count += len(scanned.get("gaps", []))
    syntax_gaps = sum(1 for item in files if item.get("error"))
    blocked = bool(substrate.get("coverage", {}).get("blocked")) or any(
        item.get("coverage") == "blocked" for item in files
    )
    coverage_state = "blocked" if blocked else (
        "partial" if gap_count or syntax_gaps or any(
            item.get("coverage") == "partial" for item in files
        ) else "complete"
    )
    return {"schema": "mantle-host-evidence-v3", "root": os.path.abspath(root),
            "python_files": py_count, "native_qt_files": native_count,
            "parser_gap_count": gap_count + syntax_gaps,
            "coverage_state": coverage_state, "files": files,
            "read_only": True, "multilang": multilang, "substrate": substrate}
