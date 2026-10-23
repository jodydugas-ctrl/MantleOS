from __future__ import annotations

from pathlib import Path, PurePosixPath
import xml.etree.ElementTree as ET

from .base import Adapter
from ..inventory import FileRecord
from ..model import Edge, Evidence, ExtractionResult, Finding, Node, stable_id


class QtResourceAdapter(Adapter):
    name = "qt_resource"
    version = "1"

    def accepts(self, record: FileRecord) -> bool:
        return record.language == "Qt Resource XML" and not record.is_binary

    def extract(self, root: Path, record: FileRecord, text: str) -> ExtractionResult:
        out = ExtractionResult()
        file_node = stable_id("node", record.id, "qt_resource_collection")
        root_eid = stable_id("evidence", record.id, self.name, "resource-file")
        out.evidence.append(Evidence(root_eid, record.id, record.path, 1, 1, "DIRECT", self.name, record.path))
        out.nodes.append(Node(file_node, "resource_collection", record.path, record.id, record.path, "MAPPED",
                              {"framework": "Qt", "generator_family": "rcc"}, [root_eid]))
        try:
            root_xml = ET.fromstring(text)
        except ET.ParseError as exc:
            out.findings.append(Finding(stable_id("finding", record.id, "qrc-parse", str(exc)), "parser_gap",
                                        f"Unable to parse Qt resource XML: {record.path}", "BLOCKED",
                                        {"error": str(exc)}, [root_eid]))
            return out

        base = PurePosixPath(record.path).parent
        search_from = 0
        for qres in root_xml.findall(".//qresource"):
            prefix = qres.attrib.get("prefix", "")
            for file_el in qres.findall("file"):
                declared = (file_el.text or "").strip()
                if not declared:
                    continue
                alias = file_el.attrib.get("alias")
                resolved = (base / declared).as_posix() if str(base) != "." else PurePosixPath(declared).as_posix()
                # Best-effort exact line from the declaration text; deterministic even for duplicate names.
                pos = text.find(declared, search_from)
                if pos < 0:
                    pos = text.find(declared)
                line = text.count("\n", 0, max(pos, 0)) + 1 if pos >= 0 else None
                if pos >= 0:
                    search_from = pos + len(declared)
                eid = stable_id("evidence", record.id, self.name, "resource", prefix, declared, alias or "", line)
                out.evidence.append(Evidence(eid, record.id, record.path, line, line, "DIRECT", self.name,
                                             f"prefix={prefix!r} file={declared!r} alias={alias!r}"))
                nid = stable_id("node", "qt_resource_asset", resolved, prefix, alias or "")
                resource_leaf = alias or declared
                resource_url = ":" + (prefix.rstrip("/") + "/" if prefix not in {"", "/"} else "/") + resource_leaf.lstrip("/")
                out.nodes.append(Node(nid, "resource_asset", resolved, record.id, record.path, "MAPPED",
                                      {"framework": "Qt", "declared_path": declared, "resolved_path": resolved,
                                       "prefix": prefix, "alias": alias, "resource_url": resource_url}, [eid]))
                out.edges.append(Edge(stable_id("edge", file_node, nid, "contains_resource"), file_node, nid,
                                      "contains_resource", "MAPPED", {}, [eid]))
        return out
