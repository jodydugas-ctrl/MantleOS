"""Conservative pure-stdlib C/C++/Qt/CMake scanner.

This is the shared form of the read-only NotepadNext bridge.  It recognizes
declarations and causal edges without compiling or executing host code.  Every
fallback limitation is emitted as a parser gap; absence of symbols is never treated
as evidence that a native host has no behavior.
"""
from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

NATIVE_EXTS = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".m", ".mm"}
MAX_BODY_LINES = 5000
CONTROL_NAMES = {"if", "for", "while", "switch", "catch"}
CALL_NAMES = {"connect", "disconnect", "singleShot", "invokeMethod", "qobject_cast",
              "static_cast", "dynamic_cast", "reinterpret_cast"}

CLASS_RE = re.compile(r"^\s*(?:class|struct)\s+([A-Za-z_]\w*)\b")
FUNC_RE = re.compile(
    r"^\s*(?!(?:if|for|while|switch|catch)\b)(?:template\s*<[^>]+>\s*)?"
    r"(?:[\w:<>,~*&\[\]\s]+\s+)?"
    r"((?:[A-Za-z_]\w*::)*(?:~?[A-Za-z_]\w*|operator[^\s(]+))"
    r"\s*\([^;{}]*\)\s*(?:const\b)?\s*(?:noexcept\b)?\s*(?:override\b)?"
    r"\s*(?:final\b)?\s*(?:->\s*[^{]+)?\{"
)
DECL_RE = re.compile(
    r"^\s*(?:virtual\s+|static\s+|inline\s+|explicit\s+|constexpr\s+)*"
    r"(?:[\w:<>,~*&\[\]\s]+\s+)?"
    r"((?:~?[A-Za-z_]\w*|operator[^\s(]+))\s*\([^;{}]*\)"
    r"\s*(?:const\b)?\s*(?:override\b)?\s*;"
)
MULTILINE_RE = re.compile(
    r"^\s*(?!(?:if|for|while|switch|catch)\b)(?:template\s*<[^>]+>\s*)?"
    r"(?:[\w:<>,~*&\[\]\s]+\s+)?"
    r"((?:[A-Za-z_]\w*::)*(?:~?[A-Za-z_]\w*|operator[^\s(]+))"
    r"\s*\([^;{}]*\)\s*(?:const\b)?\s*(?:noexcept\b)?\s*(?:override\b)?"
    r"\s*(?:final\b)?\s*(?:->\s*[^;{}]+)?\s*(?::\s*[^{};]+)?\s*\{", re.S,
)

NAME_HINTS = (
    ("HEARTBEAT", ("main", "exec", "event_loop", "timer_event", "poll")),
    ("SENSOR_EVENT", ("event", "handle", "on_", "slot", "triggered", "clicked", "changed")),
    ("PERSISTENCE_WRITE", ("settings", "session", "persist", "store", "restore", "geometry")),
    ("STATE_TRANSITION", ("set_", "update", "reset", "clear", "insert", "remove", "delete", "apply")),
    ("DISPLAY_RENDER", ("paint", "draw", "render", "show", "display", "dialog", "widget", "window")),
    ("ARM_ACTION", ("open", "save", "write", "print", "copy", "paste", "execute", "run", "launch")),
    ("SECRET_BOUNDARY", ("token", "password", "credential", "secret", "auth", "certificate")),
    ("ERROR_DEFENSE", ("validate", "verify", "check", "guard", "sanitize", "error", "retry")),
)
CALL_HINTS = (
    ("HEARTBEAT", ("qapplication::exec", "qcoreapplication::exec", "processevents", "qtimer::singleshot")),
    ("SENSOR_EVENT", ("qobject::connect", "connect(", "qevent", "qaction", "signal(", "slot(")),
    ("PERSISTENCE_WRITE", ("qsettings", "writsettings", "sessionmanager", "recentfiles")),
    ("ARM_ACTION", ("qdesktopservices", "qprocess", "qnetworkaccessmanager", "qfiledialog", ".write(")),
    ("DISPLAY_RENDER", ("qpainter", "qwidget", "qdialog", "qmainwindow", "settext(", "seticon(")),
    ("ERROR_DEFENSE", ("catch", "q_assert", "qwarning", "qcritical", "return false")),
    ("MIND_AFFORDANCE", ("openai", "anthropic", "chat.completions", "model_call")),
)


def ownership_for(relpath: str) -> str:
    low = relpath.replace("\\", "/").lower()
    if low.startswith(("thirdparty/", "third_party/", "vendor/", "vendored/", "external/")):
        return "vendored"
    base = low.rsplit("/", 1)[-1]
    if ("generated" in low or low.endswith((".gen.cpp", ".gen.h"))
            or (base.startswith("moc_") and base.endswith(".cpp"))):
        return "generated"
    return "first_party"


def artifact_kind_for(relpath: str) -> str:
    low = relpath.lower()
    if low.endswith(".ui"):
        return "qt_ui"
    if low.endswith(".qrc"):
        return "qt_resource"
    if low.endswith("cmakelists.txt") or low.endswith(".cmake"):
        return "build_system"
    if Path(low).suffix in NATIVE_EXTS:
        return "native_source"
    return "other"


def _fields(relpath: str) -> Dict[str, str]:
    ownership = ownership_for(relpath)
    return {"ownership": ownership, "scope": ownership,
            "artifact_kind": artifact_kind_for(relpath)}


def _roles(name: str, body: str) -> List[Dict[str, Any]]:
    low_name = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name.replace("::", "_")).lower()
    low_body = body.lower()
    found: Dict[str, Dict[str, Any]] = {}
    for role, hints in NAME_HINTS:
        for hint in hints:
            if hint in low_name:
                found.setdefault(role, {"role": role, "confidence": 0.62, "evidence": []})
                found[role]["evidence"].append("name contains `%s`" % hint)
    for role, hints in CALL_HINTS:
        for hint in hints:
            if hint in low_body:
                found.setdefault(role, {"role": role, "confidence": 0.74, "evidence": []})
                found[role]["confidence"] = max(found[role]["confidence"], 0.74)
                found[role]["evidence"].append("body contains `%s`" % hint)
    if not found:
        found["INTERNAL_UTILITY"] = {"role": "INTERNAL_UTILITY", "confidence": 0.5,
                                     "evidence": ["no organ evidence matched"]}
    priority = {"MIND_AFFORDANCE": 100, "SECRET_BOUNDARY": 90, "ERROR_DEFENSE": 80,
                "HEARTBEAT": 75, "SENSOR_EVENT": 70, "ARM_ACTION": 65,
                "PERSISTENCE_WRITE": 60, "STATE_TRANSITION": 55,
                "DISPLAY_RENDER": 50, "INTERNAL_UTILITY": 0}
    return sorted(found.values(), key=lambda item: (-priority.get(item["role"], 0),
                                                     -item["confidence"], item["role"]))


def split_top_level_args(text: str) -> List[str]:
    args, start, depth = [], 0, 0
    quote, escaped = "", False
    for index, char in enumerate(text):
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            continue
        if char in "'\"":
            quote = char
        elif char in "([{<":
            depth += 1
        elif char in ")]}>":
            depth = max(0, depth - 1)
        elif char == "," and depth == 0:
            args.append(text[start:index].strip()); start = index + 1
    tail = text[start:].strip()
    if tail:
        args.append(tail)
    return args


def parse_call_at(text: str, open_paren: int) -> Optional[Tuple[List[str], int, str]]:
    depth, quote, escaped = 0, "", False
    for index in range(open_paren, len(text)):
        char = text[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            continue
        if char in "'\"":
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                end = index + 1
                while end < len(text) and text[end].isspace():
                    end += 1
                if end < len(text) and text[end] == ";":
                    end += 1
                return split_top_level_args(text[open_paren + 1:index]), end, text[open_paren:end]
    return None


def qt_edges_for_body(module: str, symbol: str, body: str, start_line: int,
                      ownership: str) -> List[Dict[str, Any]]:
    edges, cursor = [], 0
    while True:
        match = re.search(r"\bconnect\s*\(", body[cursor:])
        if not match:
            break
        start = cursor + match.start(); open_paren = body.find("(", start)
        parsed = parse_call_at(body, open_paren)
        if not parsed:
            cursor = open_paren + 1; continue
        args, end, raw = parsed
        edge = {"module": module, "line": start_line + body[:start].count("\n"),
                "ownership": ownership, "scope": ownership, "container": symbol,
                "kind": "qt-connect", "raw": " ".join(raw.split()), "args": args,
                "split_ok": len(args) >= 3}
        if len(args) >= 4:
            edge.update(sender=args[0], signal=args[1], receiver=args[2], slot=args[3])
        elif len(args) >= 3:
            edge.update(sender=args[0], signal=args[1], slot=args[2])
        edges.append(edge); cursor = end
    for match in re.finditer(r"\b(connect[A-Za-z0-9_]*Action)\s*\(", body):
        parsed = parse_call_at(body, body.find("(", match.start()))
        if not parsed or not parsed[0]:
            continue
        args, end, raw = parsed
        edges.append({"module": module, "line": start_line + body[:match.start()].count("\n"),
                      "ownership": ownership, "scope": ownership, "container": symbol,
                      "kind": "qt-helper-action", "helper": match.group(1),
                      "raw": " ".join(raw.split()), "args": args,
                      "sender": args[0], "signal": "QAction::triggered",
                      "receiver": "active-editor" if "Editor" in match.group(1) else symbol,
                      "slot": args[1] if len(args) > 1 else ""})
    return edges


def _extract_body(lines: List[str], start: int) -> Tuple[str, Optional[Dict[str, Any]]]:
    body, depth, seen = [], 0, False
    end = min(len(lines), start + MAX_BODY_LINES)
    for line in lines[start:end]:
        body.append(line); depth += line.count("{") - line.count("}")
        seen = seen or "{" in line
        if seen and depth <= 0:
            break
    gap = None
    if seen and depth > 0:
        gap = {"body_truncated": True, "truncation_reason": "maximum scan span reached",
               "start_line": start + 1, "end_line": end}
    return "\n".join(body), gap


def _structured_native_symbols(path: str, rel: str, source: bytes) -> Tuple[List[Dict[str, Any]], str, List[Dict[str, Any]]]:
    """Use tree-sitter when installed; return the same evidence-bearing symbol schema."""
    try:
        from tree_sitter_language_pack import get_parser
    except ImportError:
        return [], "native-stdlib-fallback", []
    language = "c" if Path(path).suffix.lower() == ".c" else "cpp"
    try:
        tree = get_parser(language).parse(source)
    except Exception as exc:
        return [], "native-stdlib-fallback", [{
            "gap_type": "structured_parser_failure", "why": str(exc)[:240],
        }]
    fields = _fields(rel)
    symbols: List[Dict[str, Any]] = []

    def node_text(node: Any) -> str:
        return source[node.start_byte:node.end_byte].decode("utf-8", "replace")

    def declarator_name(node: Any) -> str:
        current = node
        for _ in range(12):
            nested = current.child_by_field_name("declarator")
            if nested is None:
                break
            current = nested
        return node_text(current).strip()

    def walk(node: Any) -> None:
        if node.type in {"class_specifier", "struct_specifier"}:
            name_node = node.child_by_field_name("name")
            if name_node is not None:
                name = node_text(name_node)
                symbols.append({
                    "symbol": name, "kind": "class", "line": node.start_point[0] + 1,
                    "role": "INTERNAL_UTILITY", "roles": [{
                        "role": "INTERNAL_UTILITY", "confidence": 0.8,
                        "evidence": ["tree-sitter %s declaration" % language],
                    }], "structured": True, **fields,
                })
        elif node.type == "function_definition":
            declarator = node.child_by_field_name("declarator")
            if declarator is not None:
                name = declarator_name(declarator)
                body = node_text(node)
                roles = _roles(name, body)
                symbols.append({
                    "symbol": name, "kind": "function", "line": node.start_point[0] + 1,
                    "role": roles[0]["role"], "roles": roles, "structured": True,
                    "qt_edges": qt_edges_for_body(
                        rel, name, body, node.start_point[0] + 1, fields["ownership"]
                    ), **fields,
                })
        for child in node.children:
            walk(child)

    walk(tree.root_node)
    gaps = []
    if tree.root_node.has_error:
        gaps.append({
            "gap_type": "structured_parse_error",
            "why": "tree-sitter reported error nodes; fallback evidence retained",
        })
    return symbols, "tree-sitter-%s+native-stdlib-fallback" % language, gaps


def scan_native(path: str, rel: str) -> Dict[str, Any]:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    lines, symbols, gaps = text.splitlines(), [], []
    fields = _fields(rel)
    for index, line in enumerate(lines, 1):
        class_match = CLASS_RE.match(line)
        if class_match:
            symbols.append({"symbol": class_match.group(1), "kind": "class", "line": index,
                            "role": "INTERNAL_UTILITY", "roles": [{"role": "INTERNAL_UTILITY",
                            "confidence": 0.5, "evidence": ["class/type declaration"]}], **fields})
        can_define = line == line.lstrip() or line.lstrip().startswith("template")
        match = FUNC_RE.match(line) if can_define else None
        if not match and can_define and "(" in line and not line.lstrip().startswith(tuple(CONTROL_NAMES)):
            snippet = "\n".join(lines[index - 1:min(len(lines), index + 40)])
            brace, semi = snippet.find("{"), snippet.find(";")
            if brace >= 0 and (semi < 0 or brace < semi):
                match = MULTILINE_RE.match(snippet[:brace + 1])
        if match:
            name = match.group(1).strip(); base = name.rsplit("::", 1)[-1]
            if base in CONTROL_NAMES or base in CALL_NAMES:
                continue
            body, truncation = _extract_body(lines, index - 1)
            roles = _roles(name, body)
            record = {"symbol": name, "kind": "function", "line": index,
                      "role": roles[0]["role"], "roles": roles,
                      "qt_edges": qt_edges_for_body(rel, name, body, index, fields["ownership"]),
                      **fields}
            if truncation:
                record.update(truncation); gaps.append({"line": index, **truncation})
            symbols.append(record)
        elif Path(path).suffix.lower() in {".h", ".hh", ".hpp", ".hxx"}:
            decl = DECL_RE.match(line)
            if decl:
                name = decl.group(1).split("(", 1)[0].strip()
                if name not in CONTROL_NAMES:
                    roles = _roles(name, line)
                    symbols.append({"symbol": name, "kind": "declaration", "line": index,
                                    "role": roles[0]["role"], "roles": roles, **fields})
    structured, parser, structured_gaps = _structured_native_symbols(
        path, rel, text.encode("utf-8", "replace")
    )
    if structured:
        by_identity = {(item["symbol"], item["kind"], item["line"]): item for item in symbols}
        for item in structured:
            existing = by_identity.get((item["symbol"], item["kind"], item["line"]))
            if existing is None:
                symbols.append(item)
            else:
                existing["structured"] = True
                existing["roles"] = item["roles"]
                existing["role"] = item["role"]
    gaps.extend(structured_gaps)
    if not symbols and text.strip():
        gaps.append({"line": 1, "gap_type": "native_zero_declarations",
                     "why": "no conservative declaration/definition matched"})
    return {"module": rel, "symbols": symbols, "parser": parser,
            "coverage": "partial" if gaps else "complete", "gaps": gaps}


def _property_text(node: ET.Element, name: str) -> str:
    prop = node.find("property[@name='%s']" % name)
    if prop is None:
        return ""
    for child_name in ("string", "cstring", "enum", "bool"):
        child = prop.find(child_name)
        if child is not None and child.text:
            return child.text.replace("&", "").strip()
    return ""


def scan_ui(path: str, rel: str) -> Dict[str, Any]:
    fields = _fields(rel); symbols, gaps = [], []
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        return {"module": rel, "symbols": [], "parser": "qt-ui-xml",
                "coverage": "blocked", "gaps": [{"gap_type": "ui_parse_failure", "why": str(exc)}]}
    placements: Dict[str, List[str]] = {}
    for container in tree.findall(".//widget"):
        cls, name = container.attrib.get("class", ""), container.attrib.get("name", "")
        if cls in {"QMenu", "QToolBar", "QMenuBar"}:
            for action in container.findall(".//addaction"):
                placements.setdefault(action.attrib.get("name", ""), []).append(name)
    for widget in tree.findall(".//widget"):
        name, cls = widget.attrib.get("name"), widget.attrib.get("class", "widget")
        if name:
            role = "SENSOR_EVENT" if cls in {"QMenu", "QToolBar", "QMenuBar"} else "DISPLAY_RENDER"
            symbols.append({"symbol": name, "surface_id": name, "class": cls,
                            "label": _property_text(widget, "title") or _property_text(widget, "text") or name,
                            "kind": "ui-widget", "line": 1, "role": role,
                            "roles": [{"role": role, "confidence": 0.82,
                                       "evidence": ["Qt Designer widget `%s`" % cls]}],
                            "placements": placements.get(name, []), **fields})
    for action in tree.findall(".//action"):
        name = action.attrib.get("name")
        if name:
            symbols.append({"symbol": name, "surface_id": name,
                            "label": _property_text(action, "text") or name,
                            "shortcut": _property_text(action, "shortcut"), "kind": "ui-action",
                            "line": 1, "role": "SENSOR_EVENT", "roles": [{"role": "SENSOR_EVENT",
                            "confidence": 0.86, "evidence": ["Qt Designer action"]}],
                            "placements": placements.get(name, []), **fields})
    for connection in tree.findall(".//connection"):
        sender, signal = connection.findtext("sender") or "", connection.findtext("signal") or ""
        receiver, slot = connection.findtext("receiver") or "", connection.findtext("slot") or ""
        edge = {"module": rel, "line": 1, "kind": "qt-ui-connection", "sender": sender,
                "signal": signal, "receiver": receiver, "slot": slot, "ownership": fields["ownership"]}
        symbols.append({"symbol": "%s.%s->%s.%s" % (sender, signal, receiver, slot),
                        "kind": "ui-connection", "line": 1, "role": "SENSOR_EVENT",
                        "roles": [{"role": "SENSOR_EVENT", "confidence": 0.9,
                                   "evidence": ["Qt Designer declared connection"]}],
                        "qt_edges": [edge], **fields})
    return {"module": rel, "symbols": symbols, "parser": "qt-ui-xml",
            "coverage": "complete", "gaps": gaps}


def scan_qrc(path: str, rel: str) -> Dict[str, Any]:
    fields = _fields(rel); symbols, gaps = [], []
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        return {"module": rel, "symbols": [], "parser": "qt-qrc-xml", "coverage": "blocked",
                "gaps": [{"gap_type": "qrc_parse_failure", "why": str(exc)}]}
    for resource in tree.findall(".//qresource"):
        prefix = resource.attrib.get("prefix", "/")
        for file_node in resource.findall("file"):
            source = (file_node.text or "").strip(); alias = file_node.attrib.get("alias", source)
            symbols.append({"symbol": "%s/%s" % (prefix.rstrip("/"), alias), "kind": "qt-resource",
                            "line": 1, "role": "DISPLAY_RENDER", "source": source,
                            "roles": [{"role": "DISPLAY_RENDER", "confidence": 0.7,
                                       "evidence": ["Qt resource declaration"]}], **fields})
            if source and not (Path(path).parent / source).exists():
                gaps.append({"gap_type": "missing_qrc_resource", "resource": source})
    return {"module": rel, "symbols": symbols, "parser": "qt-qrc-xml",
            "coverage": "partial" if gaps else "complete", "gaps": gaps}


def scan_cmake(path: str, rel: str) -> Dict[str, Any]:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    symbols = []
    for match in re.finditer(r"(?is)\b(add_executable|add_library|target_sources)\s*\((.*?)\)", text):
        args = re.split(r"\s+", match.group(2).strip())
        target = args[0] if args else "<unknown>"
        symbols.append({"symbol": target, "kind": "cmake-%s" % match.group(1).lower(),
                        "line": text[:match.start()].count("\n") + 1, "role": "INTERNAL_UTILITY",
                        "sources": [arg for arg in args[1:] if "." in arg and not arg.startswith("$")],
                        "roles": [{"role": "INTERNAL_UTILITY", "confidence": 0.85,
                                   "evidence": ["CMake target/source topology"]}], **_fields(rel)})
    gaps = [] if symbols else [{"gap_type": "cmake_no_targets", "why": "no supported target declaration found"}]
    return {"module": rel, "symbols": symbols, "parser": "cmake-stdlib-fallback",
            "coverage": "partial" if gaps else "complete", "gaps": gaps}


def scan_file(path: str, rel: str) -> Dict[str, Any]:
    suffix, name = Path(path).suffix.lower(), Path(path).name.lower()
    if suffix in NATIVE_EXTS:
        return scan_native(path, rel)
    if suffix == ".ui":
        return scan_ui(path, rel)
    if suffix == ".qrc":
        return scan_qrc(path, rel)
    if suffix == ".cmake" or name == "cmakelists.txt":
        return scan_cmake(path, rel)
    return {"module": rel, "symbols": [], "parser": "none", "coverage": "blocked",
            "gaps": [{"gap_type": "unsupported_native_artifact"}]}
