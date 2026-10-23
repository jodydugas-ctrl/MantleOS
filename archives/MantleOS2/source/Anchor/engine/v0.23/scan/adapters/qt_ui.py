from __future__ import annotations

from pathlib import Path
import re
import xml.etree.ElementTree as ET

from .base import Adapter
from ..inventory import FileRecord
from ..model import Edge, Evidence, ExtractionResult, Finding, Node, stable_id


# Widgets that are direct human affordances rather than passive layout containers.
INTERACTIVE_WIDGETS = {
    "QPushButton", "QToolButton", "QLineEdit", "QTextEdit", "QPlainTextEdit",
    "QComboBox", "QCheckBox", "QRadioButton", "QTreeView", "QTreeWidget",
    "QListView", "QListWidget", "QTableView", "QTableWidget", "QTabWidget",
    "QSpinBox", "QDoubleSpinBox", "QSlider", "QDial", "QDateEdit", "QTimeEdit",
    "QDateTimeEdit", "QDialogButtonBox", "QFontComboBox", "QKeySequenceEdit",
}
SURFACE_CONTAINERS = {"QMenu", "QMenuBar", "QToolBar"}


class QtUiAdapter(Adapter):
    name = "qt_ui"
    version = "4"

    def accepts(self, record: FileRecord) -> bool:
        return record.path.endswith(".ui") and not record.is_binary

    def extract(self, root: Path, record: FileRecord, text: str) -> ExtractionResult:
        out = ExtractionResult()
        try:
            tree = ET.fromstring(text)
        except ET.ParseError as exc:
            out.findings.append(Finding(
                id=stable_id("finding", record.id, "qt-ui-parse"), kind="parser_gap",
                title=f"Qt UI parse failure: {record.path}", status="BLOCKED",
                attributes={"error": str(exc), "adapter": self.name},
            ))
            return out

        node_by_name: dict[str, str] = {}
        class_by_name: dict[str, str] = {}
        lines = text.splitlines()
        ui_class = (tree.findtext("class") or "").strip()

        def find_line(pattern: str) -> int | None:
            rx = re.compile(pattern)
            for i, line in enumerate(lines, 1):
                if rx.search(line):
                    return i
            return None

        def evidence_for(name: str, excerpt: str, pattern: str | None = None) -> str:
            line = find_line(pattern) if pattern else None
            eid = stable_id("evidence", record.id, self.name, name, line, excerpt)
            out.evidence.append(Evidence(eid, record.id, record.path, line, line, "DIRECT", self.name, excerpt))
            return eid

        for elem in tree.iter():
            name = elem.attrib.get("name")
            cls = elem.attrib.get("class")
            if not name:
                continue
            if elem.tag == "action":
                props = self._properties(elem)
                eid = evidence_for(
                    f"action:{name}", f"<action name={name!r}>",
                    rf'<action\s+name=["\']{re.escape(name)}["\']',
                )
                # QAction IDs intentionally unify declaration and C++ ui->action references.
                nid = stable_id("node", "qt_action", name)
                node_by_name[name] = nid
                class_by_name[name] = "QAction"
                out.nodes.append(Node(
                    nid, "human_surface", name, record.id, record.path, "MAPPED",
                    {"framework": "Qt", "surface_type": "QAction", "surface_role": "input",
                     "qt_object_name": name, "ui_class": ui_class, **props}, [eid]
                ))
                shortcut = props.get("shortcut")
                if shortcut:
                    sid = stable_id("node", record.id, "ui_shortcut", name, shortcut)
                    seid = evidence_for(
                        f"shortcut:{name}:{shortcut}", f"{name} shortcut {shortcut}",
                        rf'<property\s+name=["\']shortcut["\']',
                    )
                    out.nodes.append(Node(
                        sid, "human_surface", str(shortcut), record.id, record.path, "MAPPED",
                        {"framework": "Qt", "surface_type": "keyboard_shortcut", "surface_role": "input",
                         "action": name, "qt_object_name": name}, [seid]
                    ))
                    out.edges.append(Edge(
                        stable_id("edge", sid, nid, "alternate_route_to"), sid, nid,
                        "alternate_route_to", "MAPPED", {"route_type": "shortcut"}, [seid]
                    ))
            elif elem.tag == "widget" and cls:
                props = self._properties(elem)
                kind = "human_surface_container" if cls in SURFACE_CONTAINERS else "ui_widget"
                if cls in INTERACTIVE_WIDGETS:
                    kind = "human_surface"
                eid = evidence_for(
                    f"widget:{cls}:{name}", f"<widget class={cls!r} name={name!r}>",
                    rf'<widget\s+class=["\']{re.escape(cls)}["\']\s+name=["\']{re.escape(name)}["\']',
                )
                nid = stable_id("node", record.id, cls, name)
                node_by_name[name] = nid
                class_by_name[name] = cls
                attrs = {"framework": "Qt", "class": cls, "qt_object_name": name, "ui_class": ui_class, **props}
                if kind == "human_surface":
                    attrs.update({"surface_type": cls, "surface_role": "input"})
                out.nodes.append(Node(nid, kind, name, record.id, record.path, "MAPPED", attrs, [eid]))

        # Menu/toolbar membership is anatomy, not merely presentation metadata.
        for parent in tree.iter():
            parent_name = parent.attrib.get("name")
            if parent_name not in node_by_name:
                continue
            for add in parent.findall("addaction"):
                child_name = add.attrib.get("name")
                if not child_name or child_name == "separator":
                    continue
                child_id = node_by_name.get(child_name)
                if not child_id:
                    continue
                eid = evidence_for(
                    f"membership:{parent_name}:{child_name}", f"{parent_name} addaction {child_name}",
                    rf'<addaction\s+name=["\']{re.escape(child_name)}["\']',
                )
                out.edges.append(Edge(
                    stable_id("edge", node_by_name[parent_name], child_id, "contains"),
                    node_by_name[parent_name], child_id, "contains", "MAPPED", {}, [eid]
                ))

        # Designer-authored <connections> are executable wiring and must participate in closure.
        connections = tree.find("connections")
        if connections is not None:
            for idx, conn in enumerate(connections.findall("connection")):
                sender = (conn.findtext("sender") or "").strip()
                signal = (conn.findtext("signal") or "").strip()
                receiver = (conn.findtext("receiver") or "").strip()
                slot = (conn.findtext("slot") or "").strip()
                if not sender or not signal or sender not in node_by_name:
                    continue
                excerpt = f"{sender}.{signal} -> {receiver}.{slot}"
                eid = evidence_for(f"connection:{idx}:{sender}:{signal}:{receiver}:{slot}", excerpt)
                event = stable_id("node", record.id, "qt_ui_signal", sender, signal)
                out.nodes.append(Node(
                    event, "event", f"{sender}::{signal}", record.id, record.path, "MAPPED",
                    {"framework": "Qt", "binding": "ui_connection", "sender": sender}, [eid]
                ))
                out.edges.append(Edge(
                    stable_id("edge", node_by_name[sender], event, "emits"), node_by_name[sender], event,
                    "emits", "MAPPED", {"binding": "ui_connection"}, [eid]
                ))
                if slot:
                    slot_name = slot.split("(", 1)[0].strip()
                    if receiver == ui_class and ui_class:
                        label = f"{ui_class}::{slot_name}"
                    else:
                        label = f"{receiver}::{slot_name}" if receiver else slot_name
                    handler = stable_id("node", record.id, "qt_ui_slot_ref", receiver, slot)
                    out.nodes.append(Node(
                        handler, "handler_reference", label, record.id, record.path, "PARTIAL",
                        {"framework": "Qt", "binding": "ui_connection", "receiver": receiver,
                         "slot": slot, "framework_native_possible": receiver != ui_class}, [eid]
                    ))
                    out.edges.append(Edge(
                        stable_id("edge", event, handler, "dispatches_to"), event, handler,
                        "dispatches_to", "PARTIAL" if receiver != ui_class else "MAPPED",
                        {"receiver": receiver}, [eid]
                    ))

        return out

    @staticmethod
    def _properties(elem: ET.Element) -> dict:
        props: dict[str, object] = {}
        for prop in elem.findall("property"):
            pname = prop.attrib.get("name")
            if not pname or len(prop) == 0:
                continue
            child = prop[0]
            value = child.text or ""
            if child.tag == "bool":
                props[pname] = value.strip().lower() == "true"
            elif child.tag in {"string", "cstring", "enum", "number"}:
                props[pname] = value
        return props
