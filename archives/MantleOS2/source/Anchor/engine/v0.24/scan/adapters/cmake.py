from __future__ import annotations

from pathlib import Path
import re

from .base import Adapter
from ..inventory import FileRecord
from ..model import Edge, Evidence, ExtractionResult, Finding, Node, stable_id


CMD_RE = re.compile(
    r"(?im)^\s*(find_package|add_subdirectory|add_executable|add_library|qt_add_executable|qt_add_library|"
    r"target_link_libraries|target_sources|CPMAddPackage|FetchContent_Declare)\s*\((.*?)\)", re.DOTALL
)
AUTOGEN_RE = re.compile(r"(?im)^\s*(?:set\s*\(\s*CMAKE_(AUTOMOC|AUTOUIC|AUTORCC)\s+(ON|TRUE|1)|set_target_properties\s*\([^\)]*\b(AUTOMOC|AUTOUIC|AUTORCC)\s+(ON|TRUE|1))")
UI_QRC_RE = re.compile(r"(?i)([^\s\)\(\"']+\.(?:ui|qrc))")
TARGET_COMPILE_DEFS_RE = re.compile(r"(?is)\btarget_compile_definitions\s*\((.*?)\)")
IF_NOT_RE = re.compile(r"(?i)^\s*if\s*\(\s*NOT\s+([A-Za-z_]\w*)\s*\)\s*$")
IF_ANY_RE = re.compile(r"(?i)^\s*if\s*\((.*?)\)\s*$")
ENDIF_RE = re.compile(r"(?i)^\s*endif(?:\s*\([^)]*\))?\s*$")


class CMakeAdapter(Adapter):
    name = "cmake"
    version = "4"

    def accepts(self, record: FileRecord) -> bool:
        return record.language == "CMake" and not record.is_binary

    def extract(self, root: Path, record: FileRecord, text: str) -> ExtractionResult:
        out = ExtractionResult()
        file_node = stable_id("node", record.id, "build_file")
        out.nodes.append(Node(file_node, "build_file", record.path, record.id, record.path, "MAPPED", {"system": "CMake"}, []))
        for m in CMD_RE.finditer(text):
            command = m.group(1)
            args = " ".join(m.group(2).split())[:1000]
            line = text.count("\n", 0, m.start()) + 1
            eid = stable_id("evidence", record.id, self.name, command, line, args)
            out.evidence.append(Evidence(eid, record.id, record.path, line, line, "DIRECT", self.name, f"{command}({args})"))
            nid = stable_id("node", record.id, "cmake_command", command, line)
            kind = "dependency_registration" if command in {"find_package", "CPMAddPackage", "FetchContent_Declare", "target_link_libraries", "add_subdirectory"} else "build_target"
            out.nodes.append(Node(nid, kind, command, record.id, record.path, "PARTIAL", {"arguments": args}, [eid]))
            out.edges.append(Edge(stable_id("edge", file_node, nid, "declares"), file_node, nid, "declares", "MAPPED", {}, [eid]))

        for m in AUTOGEN_RE.finditer(text):
            generator = (m.group(1) or m.group(3) or "QT_AUTOGEN").upper()
            line = text.count("\n", 0, m.start()) + 1
            raw = " ".join(m.group(0).split())[:500]
            eid = stable_id("evidence", record.id, self.name, "qt-autogen", generator, line)
            out.evidence.append(Evidence(eid, record.id, record.path, line, line, "DIRECT", self.name, raw))
            nid = stable_id("node", record.id, "qt_autogen", generator, line)
            family = {"AUTOMOC": "moc", "AUTOUIC": "uic", "AUTORCC": "rcc"}.get(generator, "qt_autogen")
            out.nodes.append(Node(
                nid, "generated_build_contract", generator, record.id, record.path, "MAPPED",
                {"framework": "Qt", "generator_family": family, "enabled": True,
                 "execution_policy": "recorded_from_build_definition_not_executed"}, [eid],
            ))
            out.edges.append(Edge(stable_id("edge", file_node, nid, "declares_codegen"), file_node, nid, "declares_codegen", "MAPPED", {}, [eid]))

        for m in UI_QRC_RE.finditer(text):
            artifact = m.group(1)
            line = text.count("\n", 0, m.start()) + 1
            eid = stable_id("evidence", record.id, self.name, "generated-input", artifact, line)
            out.evidence.append(Evidence(eid, record.id, record.path, line, line, "DIRECT", self.name, artifact))
            nid = stable_id("node", "qt_generated_input", artifact)
            family = "uic" if artifact.lower().endswith(".ui") else "rcc"
            out.nodes.append(Node(nid, "generated_input", artifact, record.id, record.path, "MAPPED",
                                  {"framework": "Qt", "generator_family": family}, [eid]))
            out.edges.append(Edge(stable_id("edge", file_node, nid, "references_generated_input"), file_node, nid,
                                  "references_generated_input", "MAPPED", {}, [eid]))

        # Preserve contradictory build-state evidence without repairing or guessing intent.  A compile
        # definition for SYMBOL nested inside if(NOT SYMBOL) is mechanically inconsistent with the
        # guard that admitted it.  The finding is PARTIAL because only an actual configured build can
        # establish the resulting effective target state.
        lines = text.splitlines(keepends=True)
        stack: list[tuple[str | None, int, int]] = []
        negative_spans: list[tuple[str, int, int, int, int]] = []
        offset = 0
        for line_no, raw_line in enumerate(lines, start=1):
            stripped = raw_line.strip()
            m_not = IF_NOT_RE.match(stripped)
            if m_not:
                stack.append((m_not.group(1), offset, line_no))
            elif IF_ANY_RE.match(stripped):
                stack.append((None, offset, line_no))
            elif ENDIF_RE.match(stripped) and stack:
                symbol, start_off, start_line = stack.pop()
                if symbol:
                    negative_spans.append((symbol, start_off, offset + len(raw_line), start_line, line_no))
            offset += len(raw_line)

        for m in TARGET_COMPILE_DEFS_RE.finditer(text):
            args = m.group(1)
            tokens = set(re.findall(r"\b[A-Za-z_]\w*\b", args))
            for symbol, start_off, end_off, start_line, end_line in negative_spans:
                if not (start_off <= m.start() < end_off) or symbol not in tokens:
                    continue
                line = text.count("\n", 0, m.start()) + 1
                excerpt = " ".join(m.group(0).split())[:700]
                eid = stable_id("evidence", record.id, self.name, "contradictory-compile-definition", symbol, line)
                out.evidence.append(Evidence(eid, record.id, record.path, line, line, "DIRECT", self.name, excerpt))
                guard_id = stable_id("node", record.id, "cmake_guard", "NOT", symbol, start_line)
                out.nodes.append(Node(
                    guard_id, "build_guard", f"NOT {symbol}", record.id, record.path, "MAPPED",
                    {"condition": f"NOT {symbol}", "symbol": symbol, "start_line": start_line,
                     "end_line": end_line}, [eid],
                ))
                out.findings.append(Finding(
                    stable_id("finding", record.id, "cmake-contradictory-definition", symbol, line),
                    "build_condition_contradiction",
                    f"Compile definition {symbol} is asserted inside if(NOT {symbol})",
                    "PARTIAL",
                    {"symbol": symbol, "condition": f"NOT {symbol}", "definition_line": line,
                     "guard_start_line": start_line, "guard_end_line": end_line,
                     "meaning": "direct contradictory build-state evidence; intent/effective runtime state not inferred"},
                    [eid],
                ))
        return out
