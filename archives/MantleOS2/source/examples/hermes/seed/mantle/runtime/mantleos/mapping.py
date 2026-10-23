"""Deterministic, non-executing Body Genome mapping.

The mapper accounts for every first-party source file and every loop it can
see. Structural fallbacks are reported as partial coverage; they are useful
evidence, never a claim of complete semantic understanding.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import warnings
from collections import Counter
from itertools import chain
from pathlib import Path
from typing import Any

from .contracts import (
    BodyMap,
    CapabilitySpec,
    CoverageState,
    FileCoverage,
    HabitatSpec,
    LoopDisposition,
    LoopSpec,
    SourceKind,
    contract_dict,
)

IGNORED_PARTS = {
    ".git", ".mantle", ".venv", "venv", "node_modules", "__pycache__",
    ".pytest_cache", "dist", "build",
}
VENDORED_PARTS = {
    "vendor", "vendors", "thirdparty", "third_party", "external", "extern",
    "deps", "dependencies",
}
GENERATED_PARTS = {"generated", "gen", "autogen", "moc", "ui_generated"}
LANGUAGES = {
    ".py": "python", ".pyi": "python", ".js": "javascript",
    ".mjs": "javascript", ".cjs": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "typescript", ".java": "java",
    ".kt": "kotlin", ".rs": "rust", ".go": "go", ".cs": "csharp",
    ".c": "c", ".h": "c-cpp-header", ".hh": "c-cpp-header",
    ".hpp": "c-cpp-header", ".hxx": "c-cpp-header", ".cc": "cpp",
    ".cpp": "cpp", ".cxx": "cpp", ".m": "objective-c",
    ".mm": "objective-cpp", ".ui": "qt-ui", ".qrc": "qt-resource",
    ".html": "html", ".css": "css", ".sh": "shell", ".ps1": "powershell",
}
ENTRYPOINT_NAMES = {
    "main.py", "__main__.py", "cli.py", "app.py", "server.py", "index.js",
    "index.ts", "main.js", "main.ts", "main.cpp", "main.cc", "main.cxx",
    "index.html",
}
BUILD_MARKERS = {
    "pyproject.toml": "python-pyproject", "setup.py": "python-setuptools",
    "requirements.txt": "python-requirements", "package.json": "node-package",
    "Cargo.toml": "cargo", "go.mod": "go-modules", "pom.xml": "maven",
    "build.gradle": "gradle", "Makefile": "make", "CMakeLists.txt": "cmake",
}
SOURCE_LANGUAGES = {
    "python", "javascript", "typescript", "java", "kotlin", "rust", "go",
    "csharp", "c", "c-cpp-header", "cpp", "objective-c", "objective-cpp",
    "shell", "powershell",
}
STRUCTURAL_LANGUAGES = {
    "javascript", "typescript", "c", "c-cpp-header", "cpp", "objective-c",
    "objective-cpp",
}
LOOP_PATTERN = re.compile(r"\b(?P<kind>for|while)\s*\(|\b(?P<do>do)\s*\{")
JS_FUNCTION_PATTERN = re.compile(
    r"(?:async\s+)?function\s+([A-Za-z_$][\w$]*)|"
    r"(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>|"
    r"^\s*([A-Za-z_$][\w$]*)\s*\([^;{}]*\)\s*\{"
)
CPP_FUNCTION_PATTERN = re.compile(
    r"^\s*(?:[\w:<>,~*&]+\s+)+(?P<name>[~\w:]+)\s*\([^;]*\)\s*(?:const\s*)?(?:\{|$)"
)
QT_CONNECT_PATTERN = re.compile(r"\bconnect\s*\(")
MAX_ANALYZED_SOURCE_BYTES = 2 * 1024 * 1024

ROLE_HINTS = {
    "lifecycle": ("main", "run", "serve", "start", "stop", "close", "shutdown", "init"),
    "sensory-input": ("input", "receive", "read", "submit", "message", "event", "request"),
    "presentation": ("render", "display", "show", "view", "response", "output"),
    "state-transition": ("state", "update", "change", "transition", "set", "reset"),
    "persistence": ("save", "write", "store", "persist", "commit", "database", "session"),
    "external-effect": ("send", "execute", "dispatch", "tool", "open", "delete", "install"),
    "mind-boundary": ("llm", "model", "completion", "inference", "prompt", "mind"),
    "authority-boundary": ("authorize", "permission", "policy", "approve", "guard"),
    "error-recovery": ("retry", "recover", "error", "exception", "fallback", "cancel"),
    "heartbeat": ("heartbeat", "pulse", "tick", "scheduler"),
}
DIRECT_ARTERY_CLASSES = {
    "heartbeat", "lifecycle", "persistence", "sensory-input", "external-effect",
    "mind-boundary", "authority-boundary", "error-recovery",
}


def iter_body_files(root: Path):
    for current, directories, filenames in os.walk(root):
        directories[:] = sorted(name for name in directories if name not in IGNORED_PARTS)
        for filename in sorted(filenames):
            path = Path(current) / filename
            if not path.is_symlink():
                yield path


def _sha256_file(path: Path) -> str:
    return canonical_file_digest(path)[0]


def canonical_file_digest(path: Path) -> tuple[str, int]:
    """Hash LF-normalized text or exact binary bytes, returning hash and size."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        first = handle.read(1024 * 1024)
        if b"\0" in first:
            digest.update(first)
            size = len(first)
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
                size += len(chunk)
            return digest.hexdigest(), size

        size = 0
        carry = b""
        for chunk in chain((first,), iter(lambda: handle.read(1024 * 1024), b"")):
            value = carry + chunk
            carry = b"\r" if value.endswith(b"\r") else b""
            if carry:
                value = value[:-1]
            value = value.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
            digest.update(value)
            size += len(value)
        if carry:
            digest.update(b"\n")
            size += 1
    return digest.hexdigest(), size


def _ownership(relative: str) -> str:
    parts = {part.lower() for part in Path(relative).parts}
    return "vendored" if parts & VENDORED_PARTS else "first-party"


def _artifact_kind(path: Path, relative: str) -> str:
    parts = {part.lower() for part in Path(relative).parts}
    if parts & GENERATED_PARTS:
        return "generated"
    if path.name in BUILD_MARKERS:
        return "build"
    if path.suffix.lower() == ".ui":
        return "qt-ui"
    if path.suffix.lower() == ".qrc":
        return "resource"
    if path.suffix.lower() in {".md", ".rst", ".txt"}:
        return "documentation"
    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg"}:
        return "resource"
    return "source" if LANGUAGES.get(path.suffix.lower()) in SOURCE_LANGUAGES else "other"


def _read_source(path: Path) -> tuple[str | None, tuple[str, ...]]:
    try:
        size = path.stat().st_size
        if size > MAX_ANALYZED_SOURCE_BYTES:
            return None, (f"source-too-large:{size}>{MAX_ANALYZED_SOURCE_BYTES}",)
        raw = path.read_bytes()
    except OSError as exc:
        return None, (f"read-error:{type(exc).__name__}",)
    if b"\0" in raw[:8192]:
        return None, ("binary-content",)
    try:
        return raw.decode("utf-8-sig"), ()
    except UnicodeDecodeError:
        return None, ("unsupported-text-encoding",)


def _classify_terms(*values: str) -> tuple[str, ...]:
    haystack = " ".join(values).lower()
    roles = [role for role, hints in ROLE_HINTS.items() if any(hint in haystack for hint in hints)]
    return tuple(sorted(set(roles)))


def _python_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _python_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


class _PythonGenome(ast.NodeVisitor):
    def __init__(self, relative: str) -> None:
        self.relative = relative
        self.stack: list[str] = []
        self.symbols: list[dict[str, Any]] = []
        self.calls: list[dict[str, Any]] = []
        self.loops: list[LoopSpec] = []
        self.events: list[dict[str, Any]] = []

    @property
    def enclosing(self) -> str | None:
        return ".".join(self.stack) if self.stack else None

    def _function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        name = ".".join([*self.stack, node.name])
        called = sorted({
            call_name
            for child in ast.walk(node)
            if isinstance(child, ast.Call) and (call_name := _python_name(child.func))
        })
        roles = _classify_terms(name, *called)
        self.symbols.append({
            "path": self.relative,
            "symbol": name,
            "line": node.lineno,
            "kind": "async-function" if isinstance(node, ast.AsyncFunctionDef) else "function",
            "roles": list(roles or ("internal-utility",)),
            "evidence": ["python-ast", *[f"call:{item}" for item in called[:20]]],
        })
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._function(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        target = _python_name(node.func)
        if target:
            self.calls.append({
                "path": self.relative,
                "caller": self.enclosing or "<module>",
                "callee": target,
                "line": node.lineno,
            })
            if target.endswith(("add_handler", "add_listener", "connect", "subscribe", "on")):
                self.events.append({
                    "path": self.relative,
                    "container": self.enclosing or "<module>",
                    "operation": target,
                    "line": node.lineno,
                })
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self._loop(node, "for")

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._loop(node, "async-for")

    def visit_While(self, node: ast.While) -> None:
        syntax = "while-true" if isinstance(node.test, ast.Constant) and node.test.value is True else "while"
        self._loop(node, syntax)

    def _loop(self, node: ast.For | ast.AsyncFor | ast.While, syntax: str) -> None:
        calls = sorted({
            name
            for child in ast.walk(node)
            if isinstance(child, ast.Call) and (name := _python_name(child.func))
        })
        roles = set(_classify_terms(self.enclosing or "", *calls))
        if syntax in {"async-for", "while-true"}:
            roles.add("persistent-control-loop")
        artery = tuple(sorted(roles & (DIRECT_ARTERY_CLASSES | {"persistent-control-loop"})))
        # Recognition proposes an artery; only a recorded nerve may prove
        # direct or enclosing coverage in a later construction stage.
        disposition = LoopDisposition.BLOCKED if artery else LoopDisposition.LOCAL_UTILITY
        loop_id = hashlib.sha256(
            f"{self.relative}:{node.lineno}:{syntax}:{self.enclosing}".encode()
        ).hexdigest()[:20]
        self.loops.append(LoopSpec(
            loop_id=f"loop:{loop_id}",
            path=self.relative,
            line=node.lineno,
            language="python",
            syntax=syntax,
            enclosing_symbol=self.enclosing,
            artery_classes=artery,
            disposition=disposition,
            evidence=tuple(["python-ast", *[f"call:{item}" for item in calls[:12]]]),
        ))
        self.generic_visit(node)


def _analyze_python(relative: str, text: str) -> dict[str, Any]:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(text, filename=relative)
    except (SyntaxError, ValueError) as exc:
        return {
            "state": CoverageState.BLOCKED,
            "parser": "python-stdlib-ast",
            "limitations": (f"parse-error:{type(exc).__name__}:line-{getattr(exc, 'lineno', 0)}",),
            "symbols": [], "calls": [], "events": [], "loops": [],
        }
    visitor = _PythonGenome(relative)
    visitor.visit(tree)
    return {
        "state": CoverageState.COMPLETE,
        "parser": "python-stdlib-ast",
        "limitations": (),
        "symbols": visitor.symbols,
        "calls": visitor.calls,
        "events": visitor.events,
        "loops": visitor.loops,
    }


def _nearest_structural_symbol(symbols: list[dict[str, Any]], line: int) -> str | None:
    prior = [item for item in symbols if item["line"] <= line]
    return prior[-1]["symbol"] if prior else None


def _analyze_structural(relative: str, language: str, text: str) -> dict[str, Any]:
    symbols: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    pattern = JS_FUNCTION_PATTERN if language in {"javascript", "typescript"} else CPP_FUNCTION_PATTERN
    for number, line in enumerate(text.splitlines(), start=1):
        match = pattern.search(line)
        if match:
            name = next((item for item in match.groups() if item), None)
            if name and name not in {"if", "for", "while", "switch", "catch"}:
                roles = _classify_terms(name)
                symbols.append({
                    "path": relative,
                    "symbol": name,
                    "line": number,
                    "kind": "function-candidate",
                    "roles": list(roles or ("internal-utility",)),
                    "evidence": ["structural-fallback"],
                })
        if language in {"cpp", "c-cpp-header"} and QT_CONNECT_PATTERN.search(line):
            events.append({
                "path": relative,
                "container": _nearest_structural_symbol(symbols, number),
                "operation": "qt-connect",
                "line": number,
            })
    loops: list[LoopSpec] = []
    for number, line in enumerate(text.splitlines(), start=1):
        for match in LOOP_PATTERN.finditer(line):
            syntax = match.group("kind") or "do"
            enclosing = _nearest_structural_symbol(symbols, number)
            roles = set(_classify_terms(enclosing or "", line))
            if "while" in syntax and any(token in line.lower() for token in ("true", "running", "active")):
                roles.add("persistent-control-loop")
            artery = tuple(sorted(roles & (DIRECT_ARTERY_CLASSES | {"persistent-control-loop"})))
            loop_id = hashlib.sha256(
                f"{relative}:{number}:{syntax}:{enclosing}".encode()
            ).hexdigest()[:20]
            loops.append(LoopSpec(
                loop_id=f"loop:{loop_id}",
                path=relative,
                line=number,
                language=language,
                syntax=syntax,
                enclosing_symbol=enclosing,
                artery_classes=artery,
                disposition=LoopDisposition.BLOCKED,
                evidence=("structural-fallback", "requires-exact-parser-confirmation"),
            ))
    return {
        "state": CoverageState.PARTIAL,
        "parser": f"{language}-structural-fallback",
        "limitations": ("exact-parser-required-before-automatic-innervation",),
        "symbols": symbols,
        "calls": [],
        "events": events,
        "loops": loops,
    }


def _analyze_file(relative: str, language: str | None, text: str | None) -> dict[str, Any]:
    empty = {"symbols": [], "calls": [], "events": [], "loops": []}
    if language not in SOURCE_LANGUAGES:
        return {
            "state": CoverageState.NOT_APPLICABLE, "parser": None,
            "limitations": (), **empty,
        }
    if text is None:
        return {
            "state": CoverageState.BLOCKED, "parser": None,
            "limitations": ("source-not-readable-as-text",), **empty,
        }
    if language == "python":
        return _analyze_python(relative, text)
    if language in STRUCTURAL_LANGUAGES:
        return _analyze_structural(relative, language, text)
    return {
        "state": CoverageState.BLOCKED, "parser": None,
        "limitations": (f"no-parser-for-{language}",), **empty,
    }


def _behavior_baseline(build_systems: set[str], entrypoints: list[str]) -> dict[str, Any]:
    commands: list[dict[str, Any]] = []
    if "python-pyproject" in build_systems:
        commands.append({"purpose": "tests", "argv": ["python", "-m", "pytest"]})
    if "node-package" in build_systems:
        commands.append({"purpose": "tests", "argv": ["npm", "test"]})
    if "cmake" in build_systems:
        commands.extend([
            {"purpose": "configure", "argv": ["cmake", "-S", ".", "-B", "build"]},
            {"purpose": "build", "argv": ["cmake", "--build", "build"]},
            {"purpose": "tests", "argv": ["ctest", "--test-dir", "build"]},
        ])
    return {
        "execution": "not-run",
        "requires_foreign_execution_approval": True,
        "entrypoints": sorted(entrypoints),
        "candidate_commands": commands,
        "limitations": ["commands are discovery evidence until approved and isolated"],
    }


def map_body(root: Path, *, source_uri: str, source_fingerprint: str) -> dict[str, Any]:
    root = root.resolve()
    languages: Counter[str] = Counter()
    ownership_counts: Counter[str] = Counter()
    artifact_counts: Counter[str] = Counter()
    entrypoints: list[str] = []
    build_systems: set[str] = set()
    behavior: set[str] = set()
    capabilities: list[CapabilitySpec] = []
    coverage_rows: list[FileCoverage] = []
    symbols: list[dict[str, Any]] = []
    calls: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    loops: list[LoopSpec] = []
    limitations: list[str] = []
    relative_paths: set[str] = set()

    for path in iter_body_files(root):
        relative = path.relative_to(root).as_posix()
        relative_paths.add(relative)
        language = LANGUAGES.get(path.suffix.lower())
        ownership = _ownership(relative)
        artifact_kind = _artifact_kind(path, relative)
        ownership_counts[ownership] += 1
        artifact_counts[artifact_kind] += 1
        if language:
            languages[language] += 1
        if path.name in ENTRYPOINT_NAMES:
            entrypoints.append(relative)
        marker = BUILD_MARKERS.get(path.name)
        if marker:
            build_systems.add(marker)
        text, read_limits = _read_source(path) if artifact_kind == "source" else (None, ())
        analysis = _analyze_file(relative, language, text)
        row_limits = tuple([*read_limits, *analysis["limitations"]])
        state = analysis["state"]
        if ownership != "first-party" and state in {CoverageState.PARTIAL, CoverageState.BLOCKED}:
            state = CoverageState.NOT_APPLICABLE
            row_limits = ("vendored-source-not-part-of-default-anatomy",)
        digest, canonical_bytes = canonical_file_digest(path)
        coverage_rows.append(FileCoverage(
            path=relative,
            sha256=digest,
            bytes=canonical_bytes,
            language=language,
            ownership=ownership,
            artifact_kind=artifact_kind,
            parser=analysis["parser"],
            state=state,
            limitations=row_limits,
        ))
        if ownership == "first-party":
            symbols.extend(analysis["symbols"])
            calls.extend(analysis["calls"])
            events.extend(analysis["events"])
            loops.extend(analysis["loops"])

    role_counts: Counter[str] = Counter(
        role for symbol in symbols for role in symbol.get("roles", ())
    )
    behavior.update(role for role in role_counts if role != "internal-utility")
    if any(path.endswith(("index.html", ".tsx")) for path in relative_paths):
        behavior.add("graphical-interface")
    if any(language in languages for language in ("qt-ui", "cpp")) and "cmake" in build_systems:
        behavior.add("native-graphical-interface")

    hermes_markers = {"run_agent.py", "agent/conversation_loop.py", "agent/turn_context.py"}
    if hermes_markers.issubset(relative_paths):
        capabilities.extend([
            CapabilitySpec(
                "host.conversation", "agent.conversation_loop.run_conversation",
                "Run a native host conversation turn", "communicate",
                "mantle.host-conversation-input.v2", "native-turn-receipt",
            ),
            CapabilitySpec(
                "host.tool-dispatch", "agent.tool_executor",
                "Dispatch a registered host tool through native authority", "external-effect",
                "mantle.host-tool-input.v2", "native-tool-result",
            ),
        ])

    source_rows = [
        row for row in coverage_rows
        if row.ownership == "first-party" and row.artifact_kind == "source"
    ]
    state_counts = Counter(row.state.value for row in source_rows)
    if not source_rows:
        tier = "inventory-only"
        limitations.append("no-first-party-source-files")
    elif state_counts[CoverageState.BLOCKED.value]:
        tier = "mapping-blocked"
    elif state_counts[CoverageState.PARTIAL.value]:
        tier = "mapping-partial"
    else:
        tier = "mapping-complete"

    blocked_loops = sum(1 for loop in loops if loop.disposition is LoopDisposition.BLOCKED)
    undispositioned_major = sum(
        1 for loop in loops
        if loop.artery_classes and loop.disposition is LoopDisposition.BLOCKED
    )
    unknowns: list[str] = []
    if not languages:
        unknowns.append("No source language was identified")
    if not entrypoints:
        unknowns.append("No known application entrypoint was identified")
    if state_counts[CoverageState.PARTIAL.value]:
        unknowns.append(
            f"{state_counts[CoverageState.PARTIAL.value]} first-party source files "
            "have partial parser coverage"
        )
    if state_counts[CoverageState.BLOCKED.value]:
        unknowns.append(
            f"{state_counts[CoverageState.BLOCKED.value]} first-party source files are blocked"
        )
    if blocked_loops:
        unknowns.append(f"{blocked_loops} discovered loops require exact-parser disposition")
    if undispositioned_major:
        unknowns.append(f"{undispositioned_major} major arteries remain undispositioned")

    nerve_candidates = [{
        "candidate_id": loop.loop_id,
        "path": loop.path,
        "line": loop.line,
        "semantic_events": list(loop.artery_classes),
        "disposition": loop.disposition.value,
        "status": "candidate-not-inserted",
    } for loop in loops if loop.artery_classes]
    mapped = BodyMap(
        source_uri=source_uri,
        source_fingerprint=source_fingerprint,
        habitat=HabitatSpec(
            source_kind=(
                SourceKind.LOCAL_REPOSITORY
                if source_uri.startswith("file:")
                else SourceKind.GIT_REPOSITORY
            ),
            ecosystem="repository-filesystem",
            host_application=Path(source_uri.rstrip("/")).stem or None,
            native_surfaces=tuple(sorted(behavior)),
            limitations=(
                "runtime ecosystem and permissions require native verification",
            ),
        ),
        languages=dict(sorted(languages.items(), key=lambda item: (-item[1], item[0]))),
        entrypoints=tuple(sorted(entrypoints)),
        build_systems=tuple(sorted(build_systems)),
        behavior_surfaces=tuple(sorted(behavior)),
        capabilities=tuple(capabilities),
        file_coverage=tuple(coverage_rows),
        loops=tuple(loops),
        graphs={
            "symbols": symbols, "calls": calls, "events": events,
            "role_counts": dict(sorted(role_counts.items())),
        },
        surfaces={"nerve_candidates": nerve_candidates},
        coverage={
            "tier": tier,
            "source_files": len(source_rows),
            "states": dict(sorted(state_counts.items())),
            "ownership": dict(sorted(ownership_counts.items())),
            "artifact_kinds": dict(sorted(artifact_counts.items())),
            "loops": {
                "total": len(loops), "blocked": blocked_loops,
                "undispositioned_major_arteries": undispositioned_major,
                "dispositions": dict(sorted(Counter(
                    loop.disposition.value for loop in loops
                ).items())),
            },
            "limitations": limitations,
        },
        behavior_baseline=_behavior_baseline(build_systems, entrypoints),
        unknowns=tuple(unknowns),
    )
    result = contract_dict(mapped)
    result["genome_schema"] = "mantle.body-genome.v2"
    stable = json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    result["map_sha256"] = hashlib.sha256(stable.encode("utf-8")).hexdigest()
    return result
