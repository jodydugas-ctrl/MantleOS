from __future__ import annotations

from html import unescape
from pathlib import Path
import re
from typing import Any

from .base import Adapter
from ..inventory import FileRecord
from ..model import Edge, Evidence, ExtractionResult, Node, stable_id


_HTML_SUFFIXES = {".html", ".htm"}
_INTERACTIVE_TAGS = {"button", "input", "select", "textarea", "a", "summary", "canvas"}
_INPUT_TYPES = {"button", "checkbox", "color", "date", "datetime-local", "email", "file", "number", "password", "radio", "range", "reset", "search", "submit", "tel", "text", "time", "url", "week"}
_HUMAN_DOM_EVENTS = {
    "keydown", "keyup", "keypress", "click", "dblclick", "mousedown", "mouseup", "pointerdown", "pointerup",
    "contextmenu", "drop", "dragenter", "dragover", "paste", "cut", "copy", "wheel", "touchstart", "touchend",
    "input", "change", "submit",
}


def _attrs(raw: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for match in re.finditer(r'''([:\w-]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>\x60]+)))?''', raw):
        key = match.group(1).lower()
        value = next((g for g in match.groups()[1:] if g is not None), "")
        attrs[key] = unescape(value)
    return attrs


def _visible_text(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw, flags=re.DOTALL)
    return " ".join(unescape(text).split())[:300]


def _css_declarations(raw: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for chunk in raw.split(";"):
        if ":" not in chunk:
            continue
        key, value = chunk.split(":", 1)
        key = key.strip().lower()
        value = " ".join(value.strip().split())
        if key and value:
            values[key] = value
    return values


class WebFrontendAdapter(Adapter):
    """Static browser-surface and stylesheet reconstruction evidence.

    This adapter deliberately does not execute HTML, CSS, or JavaScript. It turns
    declared browser controls and stylesheet rules into the generic human-surface /
    visual-contract vocabulary already used by React and Qt.
    """

    name = "web-frontend"
    version = "3"

    def accepts(self, record: FileRecord) -> bool:
        return Path(record.path).suffix.lower() in _HTML_SUFFIXES | {".css"} and not record.is_binary

    def extract(self, root: Path, record: FileRecord, text: str) -> ExtractionResult:
        out = ExtractionResult()
        suffix = Path(record.path).suffix.lower()
        lines = text.splitlines()

        def ev(line: int | None, purpose: str, excerpt: str | None = None) -> str:
            eid = stable_id("evidence", record.id, self.name, self.version, line, purpose)
            if excerpt is None and line and 0 < line <= len(lines):
                excerpt = lines[line - 1].strip()[:500]
            out.evidence.append(Evidence(eid, record.id, record.path, line, line, "DIRECT", f"{self.name}/{self.version}", excerpt))
            return eid

        def node(kind: str, name: str, *, line: int | None, coverage: str = "MAPPED",
                 attrs: dict[str, Any] | None = None, evidence_ids: list[str] | None = None,
                 key: str | None = None) -> str:
            nid = stable_id(kind, key if key is not None else record.id, name, line)
            out.nodes.append(Node(nid, kind, name, record.id, record.path, coverage, attrs or {}, evidence_ids or []))
            return nid

        def edge(src: str, dst: str, kind: str, *, line: int | None, coverage: str = "MAPPED",
                 attrs: dict[str, Any] | None = None, evidence_ids: list[str] | None = None) -> None:
            out.edges.append(Edge(stable_id("edge", src, kind, dst, record.id, line), src, dst, kind, coverage, attrs or {}, evidence_ids or []))

        if suffix in _HTML_SUFFIXES:
            labels_by_for: dict[str, str] = {}
            label_rx = re.compile(r"<label\b(?P<attrs>[^>]*)>(?P<body>.*?)</label\s*>", re.IGNORECASE | re.DOTALL)
            for label_match in label_rx.finditer(text):
                label_attrs = _attrs(label_match.group("attrs"))
                target = label_attrs.get("for")
                label_text = _visible_text(label_match.group("body"))
                if target and label_text and target not in labels_by_for:
                    labels_by_for[target] = label_text

            paired = re.compile(r"<(?P<tag>button|select|textarea|a|summary|canvas)\b(?P<attrs>[^>]*)>(?P<body>.*?)</(?P=tag)\s*>", re.IGNORECASE | re.DOTALL)
            consumed: list[tuple[int, int]] = []
            for match in paired.finditer(text):
                consumed.append((match.start(), match.end()))
                tag = match.group("tag").lower()
                attrs = _attrs(match.group("attrs"))
                line = text.count("\n", 0, match.start()) + 1
                self._surface(out, record, tag, attrs, line, _visible_text(match.group("body")), labels_by_for, ev, node, edge)

            tag_rx = re.compile(r"<(?P<tag>input|button|select|textarea|a|summary|canvas)\b(?P<attrs>[^>]*)>", re.IGNORECASE)
            for match in tag_rx.finditer(text):
                if any(start <= match.start() < end for start, end in consumed):
                    continue
                tag = match.group("tag").lower()
                attrs = _attrs(match.group("attrs"))
                line = text.count("\n", 0, match.start()) + 1
                self._surface(out, record, tag, attrs, line, "", labels_by_for, ev, node, edge)
        else:
            def blank_comment(m: re.Match[str]) -> str:
                return "".join("\n" if ch == "\n" else " " for ch in m.group(0))

            cleaned = re.sub(r"/\*.*?\*/", blank_comment, text, flags=re.DOTALL)
            for match in re.finditer(r"(?P<selector>[^{}]+)\{(?P<body>[^{}]*)\}", cleaned, re.DOTALL):
                selector = " ".join(match.group("selector").split())
                if not selector or selector.startswith("@"):
                    continue
                declarations = _css_declarations(match.group("body"))
                if not declarations:
                    continue
                line = cleaned.count("\n", 0, match.start()) + 1
                excerpt = f"{selector} {{ " + "; ".join(f"{k}: {v}" for k, v in declarations.items()) + " }"
                evid = ev(line, f"css-rule:{selector}", excerpt[:500])
                class_tokens = sorted(set(re.findall(r"\.([A-Za-z_][\w-]*)", selector)))
                id_tokens = sorted(set(re.findall(r"#([A-Za-z_][\w-]*)", selector)))
                node("visual_contract", selector, line=line, attrs={
                    "tag": selector,
                    "selector": selector,
                    "class_tokens": class_tokens,
                    "id_tokens": id_tokens,
                    "style": "; ".join(f"{k}: {v}" for k, v in declarations.items()),
                    "css_properties": declarations,
                    "mechanism": "stylesheet_rule",
                    "line": line,
                }, evidence_ids=[evid], key=f"css:{record.path}:{selector}:{line}")
        return out

    def _surface(self, out: ExtractionResult, record: FileRecord, tag: str, attrs: dict[str, str], line: int,
                 human_text: str, labels_by_for: dict[str, str], ev, node, edge) -> None:
        element_id = attrs.get("id") or None
        role = attrs.get("role") or None
        input_type = attrs.get("type", "text").lower() if tag == "input" else None
        if tag == "input" and input_type not in _INPUT_TYPES:
            input_type = attrs.get("type") or "text"
        associated_label = labels_by_for.get(element_id) if element_id else None
        label = (
            attrs.get("aria-label") or associated_label or human_text or attrs.get("title") or attrs.get("placeholder") or
            element_id or attrs.get("name") or attrs.get("value") or f"<{tag}>@{line}"
        )
        surface_type = f"html:{tag}" if tag != "input" else f"html:input:{input_type}"
        inline_human_events = sorted(
            event_name for key in attrs
            if key.startswith("on") and len(key) > 2
            for event_name in [key[2:].lower()]
            if event_name in _HUMAN_DOM_EVENTS
        )
        # A plain declarative hyperlink proves that navigation markup exists, but not that the
        # document belongs to the application's reachable control surface. Repositories frequently
        # contain vendored/reference HTML documentation; admitting every <a> directly into A7 can
        # turn documentation navigation into thousands of false application controls. Preserve the
        # link as first-class evidence and let stronger event/runtime reachability promote it later.
        application_link_roles = {"button", "menuitem", "menuitemcheckbox", "menuitemradio", "tab", "switch", "checkbox", "radio"}
        if tag == "a" and not inline_human_events and role not in application_link_roles:
            evid = ev(line, f"html-navigation-candidate:{element_id or label}")
            node("web_navigation_reference", label, line=line, coverage="PARTIAL", attrs={
                "surface_type": "html:a",
                "surface_role": "navigation_candidate",
                "tag": tag,
                "role": role,
                "dom_id": element_id,
                "element_id": element_id,
                "href": attrs.get("href"),
                "target": attrs.get("target"),
                "human_text": human_text or None,
                "aria_label": attrs.get("aria-label"),
                "title": attrs.get("title"),
                "line": line,
                "classification": "declarative_hyperlink_candidate",
                "admission_rule": "requires_event_semantics_or_runtime_document_reachability_for_A7_denominator",
            }, evidence_ids=[evid], key=f"html-navigation:{record.path}:{element_id or line}:{tag}")
            return

        surface_role = "presented" if tag == "canvas" and not inline_human_events else "input"
        evid = ev(line, f"html-surface:{tag}:{element_id or label}")
        surface = node("human_surface", label, line=line, attrs={
            "surface_type": surface_type,
            "surface_role": surface_role,
            "tag": tag,
            "role": role,
            "dom_id": element_id,
            "element_id": element_id,
            "name": attrs.get("name"),
            "href": attrs.get("href"),
            "target": attrs.get("target"),
            "control_type": input_type,
            "human_text": human_text or None,
            "aria_label": attrs.get("aria-label"),
            "associated_label": associated_label,
            "title": attrs.get("title"),
            "placeholder": attrs.get("placeholder"),
            "value": attrs.get("value"),
            "min": attrs.get("min"), "max": attrs.get("max"), "step": attrs.get("step"),
            "line": line,
            "classification": "static_html_canvas" if tag == "canvas" else "static_html_control",
        }, evidence_ids=[evid], key=f"html-surface:{record.path}:{element_id or line}:{tag}")

        for key, expression in sorted(attrs.items()):
            if not key.startswith("on") or len(key) <= 2:
                continue
            event_name = key[2:].lower()
            hev = ev(line, f"inline-handler:{element_id or label}:{event_name}")
            handler = node("handler_reference", expression or f"inline {event_name}", line=line,
                           coverage="PARTIAL", attrs={
                               "framework": "web_dom", "dom_id": element_id, "event_name": event_name,
                               "expression": expression, "role": "inline_dom_handler", "line": line,
                           }, evidence_ids=[hev], key=f"inline-handler:{record.path}:{element_id or line}:{event_name}")
            edge(surface, handler, "dispatches_to", line=line, coverage="PARTIAL", evidence_ids=[evid, hev])
