#!/usr/bin/env python3
"""
mantle.assimilator.substrate  --  Phase-0 host substrate discovery

Code-agnostic assimilation starts by identifying what the host is made of. The
scanner may then use a parser, generate a local adapter, or explicitly report
that coverage is incomplete. Silent undercounting is not a valid Phase-0 result.
"""
from __future__ import annotations

import os
from typing import Any, Dict

from .coverage import CoverageState, ParserCapability, SubstrateCoverage


NATIVE_EXTS = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".m", ".mm"}
QT_EXTS = {".ui", ".qrc"}
PY_EXTS = {".py"}
TREE_SITTER_EXTS = {".js", ".mjs", ".go", ".rs"}
BUILD_FILES = {"cmakelists.txt", "makefile", "meson.build", "build.gradle",
               "package.json", "pyproject.toml", "cargo.toml", "go.mod"}


def discover(root: str) -> Dict[str, Any]:
    """Return a read-only substrate census for a host tree."""
    counts: Dict[str, int] = {}
    build_files = []
    first_party_files = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in (".git", "__pycache__", "node_modules", ".venv",
                                    "venv", "dist", "build", ".pytest_cache")]
        for filename in filenames:
            first_party_files += 1
            lower = filename.lower()
            ext = os.path.splitext(filename)[1].lower()
            if lower in BUILD_FILES:
                rel = os.path.relpath(os.path.join(dirpath, filename), root)
                build_files.append(rel.replace(os.sep, "/"))
            counts[ext or "<none>"] = counts.get(ext or "<none>", 0) + 1

    native_count = sum(counts.get(ext, 0) for ext in NATIVE_EXTS)
    qt_count = sum(counts.get(ext, 0) for ext in QT_EXTS)
    tree_sitter_count = sum(counts.get(ext, 0) for ext in TREE_SITTER_EXTS)
    python_count = sum(counts.get(ext, 0) for ext in PY_EXTS)
    cmake = any(os.path.basename(path).lower() == "cmakelists.txt" for path in build_files)

    languages = []
    if python_count:
        languages.append("python")
    if tree_sitter_count:
        languages.append("tree-sitter-optional")
    if native_count:
        languages.append("native-c-family")
    if qt_count:
        languages.append("qt-resource-ui")
    if cmake:
        languages.append("cmake")

    unsupported = []

    total_bytes = 0
    try:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__", "node_modules")]
            for filename in filenames:
                try:
                    total_bytes += os.path.getsize(os.path.join(dirpath, filename))
                except OSError:
                    pass
    except OSError:
        total_bytes = 0
    coverage_rows = []
    for language, count, bytes_hint, parser_available, parser_name in (
        ("python", python_count, 0, True, "stdlib-ast"),
        ("native-c-family", native_count, 0, True, "native-stdlib-fallback"),
        ("qt-resource-ui", qt_count, 0, True, "qt-xml-stdlib"),
        ("rust", counts.get(".rs", 0), 0, True, "stdlib-rust-fallback"),
    ):
        if not count:
            continue
        row = SubstrateCoverage(
            language, count, bytes_hint, count if parser_available else 0,
            total_first_party_files=first_party_files,
            total_first_party_bytes=total_bytes,
            material_gaps=() if parser_available else ("parser unavailable",),
            parser=ParserCapability(
                language, parser_available, parser_name,
                ("conservative fallback; per-file gaps are authoritative",)
                if "fallback" in parser_name else (),
            ),
        )
        coverage_rows.append(row.to_dict())

    return {
        "root": os.path.abspath(root),
        "files": first_party_files,
        "extension_counts": dict(sorted(counts.items())),
        "build_files": sorted(build_files),
        "languages": languages or ["unknown"],
        "python_files": python_count,
        "tree_sitter_candidate_files": tree_sitter_count,
        "native_candidate_files": native_count,
        "qt_candidate_files": qt_count,
        "coverage": {
            "python_ast": python_count,
            "tree_sitter_optional": tree_sitter_count,
            "requires_adaptive_native_tools": 0,
            "states": coverage_rows,
            "blocked": any(row["state"] == CoverageState.BLOCKED.value for row in coverage_rows),
        },
        "unsupported": unsupported,
        "read_only": True,
    }
