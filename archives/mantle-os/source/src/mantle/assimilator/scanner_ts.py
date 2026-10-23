#!/usr/bin/env python3
"""
mantle.assimilator.scanner_ts  --  multi-language READ-ONLY dissection (assimilation,
language-agnostic path)

Proves and ships the language-agnostic claim recorded in the doctrine: the Mantle
role/organ model is language-NEUTRAL, so a non-Python host can be dissected by
SWAPPING ONLY THE PARSER (tree-sitter) while REUSING the existing deterministic
classifier (scanner.classify_symbol) unchanged.

Emits the SAME record shape as scanner.scan_file: {module, symbols:[{symbol, kind,
line, role}]}. Read-only: opens files for reading; never writes to the host.

Optional dependency:
    pip install "tree-sitter-language-pack==1.3.1"
Without it, scan_project falls back to Python-only (no behavior change).
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict

from .scanner import classify_symbol

# extension -> (tree-sitter language, function node types, class/type node types)
LANGS = {
    ".js":  ("javascript", {"function_declaration", "function_expression",
                            "generator_function_declaration", "method_definition"},
             {"class_declaration"}),
    ".mjs": ("javascript", {"function_declaration", "method_definition"},
             {"class_declaration"}),
    ".go":  ("go", {"function_declaration", "method_declaration"}, {"type_declaration"}),
    ".rs":  ("rust", {"function_item"}, {"struct_item", "impl_item"}),
}


def available() -> bool:
    """True if the optional tree-sitter stack is installed."""
    try:
        import tree_sitter_language_pack  # noqa: F401
    except ImportError:
        try:
            import tree_sitter_languages  # noqa: F401
        except ImportError:
            return False
    return True


def _norm(name: str) -> str:
    """camelCase/PascalCase -> snake so the snake_case name-hints fire on any language."""
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name).lower()


def _parser(lang: str):
    try:
        from tree_sitter_language_pack import get_parser
    except ImportError:
        # Compatibility for environments created before the cross-minor package switch.
        from tree_sitter_languages import get_parser
    return get_parser(lang)


def _node_name(node, src: bytes) -> str:
    c = node.child_by_field_name("name")
    if c is not None:
        return src[c.start_byte:c.end_byte].decode("utf-8", "replace")
    for c in node.children:
        if c.type in ("identifier", "property_identifier", "type_identifier",
                      "field_identifier"):
            return src[c.start_byte:c.end_byte].decode("utf-8", "replace")
    return "<anonymous>"


def scan_file(path: str, rel: str) -> Dict[str, Any]:
    """Scan one non-Python file READ-ONLY. Same return shape as scanner.scan_file."""
    ext = os.path.splitext(path)[1].lower()
    if ext not in LANGS:
        return {"module": rel, "symbols": [], "skipped": "unsupported ext %s" % ext}
    lang, fn_types, cls_types = LANGS[ext]
    with open(path, "rb") as f:
        src = f.read()
    out: Dict[str, Any] = {"module": rel, "symbols": []}
    try:
        tree = _parser(lang).parse(src)
    except Exception as e:                       # parser/tooling failure is non-fatal
        out["error"] = "parse: %s" % e
        return out

    def walk(node) -> None:
        for child in node.children:
            if child.type in fn_types:
                name = _node_name(child, src)
                if name in ("<anonymous>", "constructor"):   # skip noise nodes
                    continue
                body = src[child.start_byte:child.end_byte].decode("utf-8", "replace")
                role = classify_symbol(_norm(name), body, [])   # reuse neutral classifier
                out["symbols"].append({"symbol": name, "kind": "function",
                                       "line": child.start_point[0] + 1, "role": role})
            elif child.type in cls_types:
                name = _node_name(child, src)
                out["symbols"].append({"symbol": name, "kind": "class",
                                       "line": child.start_point[0] + 1,
                                       "role": "INTERNAL_UTILITY"})
            walk(child)

    walk(tree.root_node)
    return out
