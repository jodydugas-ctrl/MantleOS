from __future__ import annotations

from pathlib import Path
import re

from .base import Adapter
from ..inventory import FileRecord
from ..model import Edge, Evidence, ExtractionResult, Node, stable_id


ASSIGN_RE = re.compile(r"(?m)^\s*([A-Za-z_][A-Za-z0-9_.]*)\s*(\+=|-=|=)\s*(.*)$")
COND_RE = re.compile(r"(?m)^\s*([A-Za-z_][A-Za-z0-9_]*(?:\([^\n]*\))?)\s*:\s*(.+)$")


def _logical_lines(text: str):
    """Yield qmake logical lines with starting physical line numbers."""
    raw = text.splitlines()
    buf = ""
    start = 1
    for idx, line in enumerate(raw, 1):
        stripped = line.rstrip()
        if not buf:
            start = idx
        if stripped.endswith("\\"):
            buf += stripped[:-1] + " "
            continue
        logical = (buf + stripped).strip()
        buf = ""
        if logical:
            yield start, logical
    if buf.strip():
        yield start, buf.strip()


def _tokens(value: str) -> list[str]:
    # qmake lists are whitespace separated for the common build-declaration forms.
    # Preserve variable expressions rather than attempting expansion.
    value = re.sub(r"\s+#.*$", "", value).strip()
    return [x for x in re.split(r"\s+", value) if x]


class QMakeAdapter(Adapter):
    name = "qmake"
    version = "1"

    def accepts(self, record: FileRecord) -> bool:
        return record.language == "QMake" and not record.is_binary

    def extract(self, root: Path, record: FileRecord, text: str) -> ExtractionResult:
        out = ExtractionResult()
        file_node = stable_id("node", record.id, "build_file")
        root_ev = stable_id("evidence", record.id, self.name, "file")
        out.evidence.append(Evidence(root_ev, record.id, record.path, 1, 1, "DIRECT", self.name, record.path))
        out.nodes.append(Node(file_node, "build_file", record.path, record.id, record.path, "MAPPED",
                              {"system": "qmake"}, [root_ev]))

        for line_no, logical in _logical_lines(text):
            m = ASSIGN_RE.match(logical)
            if not m:
                # Preserve common qmake conditions without trying to evaluate their truth.
                cm = COND_RE.match(logical)
                if cm:
                    cond, body = cm.groups()
                    eid = stable_id("evidence", record.id, self.name, "condition", line_no, logical)
                    out.evidence.append(Evidence(eid, record.id, record.path, line_no, line_no, "DIRECT", self.name, logical[:500]))
                    nid = stable_id("node", record.id, "qmake_condition", line_no, cond)
                    out.nodes.append(Node(nid, "conditional_build", cond, record.id, record.path, "PARTIAL",
                                          {"system": "qmake", "condition": cond, "body": body[:1000],
                                           "meaning": "condition recorded; truth not evaluated"}, [eid]))
                    out.edges.append(Edge(stable_id("edge", file_node, nid, "contains_condition"), file_node, nid,
                                          "contains_condition", "MAPPED", {}, [eid]))
                    inner = ASSIGN_RE.match(body.strip())
                    if inner:
                        ikey, iop, ivalue = inner.groups()
                        ivals = _tokens(ivalue)
                        if ikey in {"QT", "LIBS", "PKGCONFIG"}:
                            for val in ivals:
                                dep = stable_id("node", record.id, "qmake_dependency", ikey, val, cond)
                                out.nodes.append(Node(dep, "dependency_registration", val, record.id, record.path, "PARTIAL",
                                                      {"system": "qmake", "variable": ikey, "operator": iop,
                                                       "dependency": val, "condition": cond,
                                                       "condition_truth": "UNKNOWN"}, [eid]))
                                out.edges.append(Edge(stable_id("edge", nid, dep, "conditionally_declares"), nid, dep,
                                                      "conditionally_declares", "PARTIAL", {"condition": cond}, [eid]))
                        elif ikey in {"SOURCES", "HEADERS", "FORMS", "RESOURCES", "TRANSLATIONS"}:
                            family = {"FORMS": "uic", "RESOURCES": "rcc"}.get(ikey)
                            for val in ivals:
                                inp = stable_id("node", "qmake_input", record.path, ikey, val, cond)
                                kind = "generated_input" if family else "build_input"
                                attrs = {"system": "qmake", "variable": ikey, "operator": iop, "path": val,
                                         "condition": cond, "condition_truth": "UNKNOWN"}
                                if family:
                                    attrs.update({"framework": "Qt", "generator_family": family})
                                out.nodes.append(Node(inp, kind, val, record.id, record.path, "PARTIAL", attrs, [eid]))
                                out.edges.append(Edge(stable_id("edge", nid, inp, "conditionally_declares"), nid, inp,
                                                      "conditionally_declares", "PARTIAL", {"condition": cond}, [eid]))
                continue

            key, op, value = m.groups()
            vals = _tokens(value)
            eid = stable_id("evidence", record.id, self.name, key, line_no, logical)
            out.evidence.append(Evidence(eid, record.id, record.path, line_no, line_no, "DIRECT", self.name, logical[:500]))

            if key == "TARGET":
                nid = stable_id("node", record.id, "qmake_target", " ".join(vals))
                out.nodes.append(Node(nid, "build_target", " ".join(vals) or "TARGET", record.id, record.path, "MAPPED",
                                      {"system": "qmake", "variable": key, "operator": op, "values": vals}, [eid]))
                out.edges.append(Edge(stable_id("edge", file_node, nid, "declares"), file_node, nid, "declares", "MAPPED", {}, [eid]))
            elif key in {"QT", "LIBS", "PKGCONFIG"}:
                for val in vals:
                    nid = stable_id("node", record.id, "qmake_dependency", key, val)
                    out.nodes.append(Node(nid, "dependency_registration", val, record.id, record.path, "MAPPED",
                                          {"system": "qmake", "variable": key, "operator": op, "dependency": val}, [eid]))
                    out.edges.append(Edge(stable_id("edge", file_node, nid, "declares_dependency"), file_node, nid,
                                          "declares_dependency", "MAPPED", {}, [eid]))
            elif key in {"SOURCES", "HEADERS", "FORMS", "RESOURCES", "TRANSLATIONS"}:
                family = {"FORMS": "uic", "RESOURCES": "rcc"}.get(key)
                for val in vals:
                    nid = stable_id("node", "qmake_input", record.path, key, val)
                    kind = "generated_input" if family else "build_input"
                    attrs = {"system": "qmake", "variable": key, "operator": op, "path": val}
                    if family:
                        attrs.update({"framework": "Qt", "generator_family": family})
                    out.nodes.append(Node(nid, kind, val, record.id, record.path, "MAPPED", attrs, [eid]))
                    out.edges.append(Edge(stable_id("edge", file_node, nid, "references_build_input"), file_node, nid,
                                          "references_build_input", "MAPPED", {}, [eid]))
            elif key in {"TEMPLATE", "CONFIG", "DEFINES", "INCLUDEPATH"}:
                nid = stable_id("node", record.id, "qmake_setting", key, line_no)
                out.nodes.append(Node(nid, "build_setting", key, record.id, record.path, "MAPPED",
                                      {"system": "qmake", "variable": key, "operator": op, "values": vals}, [eid]))
                out.edges.append(Edge(stable_id("edge", file_node, nid, "declares_setting"), file_node, nid,
                                      "declares_setting", "MAPPED", {}, [eid]))
        return out
