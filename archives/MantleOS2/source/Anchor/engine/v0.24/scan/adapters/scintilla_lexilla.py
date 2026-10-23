from __future__ import annotations

from pathlib import Path
import bisect
import re

from .base import Adapter
from ..inventory import FileRecord
from ..model import Edge, Evidence, ExtractionResult, Node, stable_id


SCI_TOKEN_RE = re.compile(r"\b(SCI_[A-Z0-9_]+)\b")
SCN_TOKEN_RE = re.compile(r"\b(SCN_[A-Z0-9_]+)\b")
LEXILLA_RE = re.compile(r"\b(?:Lexilla::|CreateLexer\s*\(|MakeLexer\s*\(|LexerCatalogue|ILexer\b)")
SCINTILLA_REF_RE = re.compile(r"\b(?:Scintilla(?:Next)?|Scintilla::|ScintillaEdit|ScintillaCall)\b")

# Framework-specific semantic catalog. These are stable Scintilla message names, not specimen names.
COMMAND_CATEGORIES = {
    "SCI_UNDO": ("undo", "editing_history", "state"),
    "SCI_REDO": ("redo", "editing_history", "state"),
    "SCI_CUT": ("cut", "clipboard", "state_and_nest"),
    "SCI_COPY": ("copy", "clipboard", "nest"),
    "SCI_PASTE": ("paste", "clipboard", "state_and_nest"),
    "SCI_CLEAR": ("delete_selection", "editing", "state"),
    "SCI_SELECTALL": ("select_all", "selection", "state"),
    "SCI_SETSEL": ("set_selection", "selection", "state"),
    "SCI_SETSELECTION": ("set_selection", "selection", "state"),
    "SCI_GOTOPOS": ("move_caret", "navigation", "state"),
    "SCI_GOTOLINE": ("move_caret", "navigation", "state"),
    "SCI_REPLACESEL": ("replace_selection", "editing", "state"),
    "SCI_SETTEXT": ("set_document_text", "editing", "state"),
    "SCI_GETTEXT": ("read_document_text", "editing", "read"),
    "SCI_FINDTEXT": ("find_text", "search", "read"),
    "SCI_SEARCHINTARGET": ("search_target", "search", "read"),
    "SCI_REPLACETARGET": ("replace_target", "search", "state"),
    "SCI_REPLACETARGETRE": ("replace_target_regex", "search", "state"),
    "SCI_SETSAVEPOINT": ("set_save_point", "document_state", "state"),
    "SCI_SETREADONLY": ("set_read_only", "document_state", "state"),
    "SCI_SETLEXER": ("set_lexer", "lexing", "state"),
    "SCI_SETLEXERLANGUAGE": ("set_lexer_language", "lexing", "state"),
    "SCI_COLOURISE": ("colourise", "lexing", "feedback"),
    "SCI_STYLECLEARALL": ("reset_styles", "styling", "feedback"),
    "SCI_SETFOCUS": ("set_focus", "focus", "feedback"),
}

NOTIFICATION_CATEGORIES = {
    "SCN_MODIFIED": ("document_modified", "editing"),
    "SCN_UPDATEUI": ("ui_update", "feedback"),
    "SCN_CHARADDED": ("character_added", "editing"),
    "SCN_SAVEPOINTREACHED": ("save_point_reached", "document_state"),
    "SCN_SAVEPOINTLEFT": ("save_point_left", "document_state"),
    "SCN_MARGINCLICK": ("margin_click", "pointer"),
    "SCN_DOUBLECLICK": ("double_click", "pointer"),
    "SCN_HOTSPOTCLICK": ("hotspot_click", "pointer"),
    "SCN_AUTOCSELECTION": ("autocomplete_selection", "completion"),
}


class ScintillaLexillaAdapter(Adapter):
    """Framework-aware static recognizer for Scintilla/Lexilla integration.

    The adapter does not claim that every Scintilla capability is exposed to the human by the specimen.
    It records exact message/notification use as BODY<->framework coupling evidence and leaves generic
    references PARTIAL. This gives later control-surface closure a framework vocabulary without pretending
    the framework implementation lives in the application's source tree.
    """

    name = "scintilla_lexilla"
    version = "1"

    def accepts(self, record: FileRecord) -> bool:
        return record.language in {"C", "C++", "C++ Header", "C/C++ Header"} and not record.is_binary

    def extract(self, root: Path, record: FileRecord, text: str) -> ExtractionResult:
        out = ExtractionResult()
        if not (SCI_TOKEN_RE.search(text) or SCN_TOKEN_RE.search(text) or LEXILLA_RE.search(text) or SCINTILLA_REF_RE.search(text)):
            return out

        starts = [0]
        for m in re.finditer("\n", text):
            starts.append(m.end())

        def line_for(pos: int) -> int:
            return bisect.bisect_right(starts, pos)

        framework = stable_id("node", "framework", "Scintilla_Lexilla")
        out.nodes.append(Node(
            framework, "nest_provider", "Scintilla/Lexilla", None, None, "MAPPED",
            {"provider_type": "editor_framework", "capability_provenance": "BORROWED_OR_COUPLED"}, [],
        ))

        seen: set[tuple[str, int]] = set()
        for rx, token_kind in ((SCI_TOKEN_RE, "command"), (SCN_TOKEN_RE, "notification")):
            for m in rx.finditer(text):
                token = m.group(1)
                key = (token, m.start())
                if key in seen:
                    continue
                seen.add(key)
                line = line_for(m.start())
                eid = stable_id("evidence", record.id, self.name, token, line)
                out.evidence.append(Evidence(eid, record.id, record.path, line, line, "DIRECT", self.name, token))
                if token_kind == "command":
                    semantic, category, effect = COMMAND_CATEGORIES.get(token, (token.lower(), "unknown", "unknown"))
                    coverage = "MAPPED" if token in COMMAND_CATEGORIES else "PARTIAL"
                    nid = stable_id("node", "scintilla_command", token)
                    out.nodes.append(Node(
                        nid, "framework_capability", token, record.id, record.path, coverage,
                        {"framework": "Scintilla", "message": token, "semantic": semantic,
                         "category": category, "effect_class": effect,
                         "capability_provenance": "COUPLED", "surface_role": "framework_native"}, [eid],
                    ))
                    out.edges.append(Edge(stable_id("edge", nid, framework, "requires"), nid, framework,
                                          "requires", "MAPPED", {"provider": "Scintilla"}, [eid]))
                else:
                    semantic, category = NOTIFICATION_CATEGORIES.get(token, (token.lower(), "unknown"))
                    coverage = "MAPPED" if token in NOTIFICATION_CATEGORIES else "PARTIAL"
                    nid = stable_id("node", "scintilla_notification", token)
                    out.nodes.append(Node(
                        nid, "framework_event", token, record.id, record.path, coverage,
                        {"framework": "Scintilla", "notification": token, "semantic": semantic,
                         "category": category, "capability_provenance": "COUPLED"}, [eid],
                    ))
                    out.edges.append(Edge(stable_id("edge", framework, nid, "emits"), framework, nid,
                                          "emits", "MAPPED", {"provider": "Scintilla"}, [eid]))

        for m in LEXILLA_RE.finditer(text):
            line = line_for(m.start())
            raw = m.group(0)
            eid = stable_id("evidence", record.id, self.name, "lexilla", raw, line)
            out.evidence.append(Evidence(eid, record.id, record.path, line, line, "DIRECT", self.name, raw))
            nid = stable_id("node", record.id, "lexilla_receptor", line, raw)
            out.nodes.append(Node(
                nid, "extension_receptor_candidate", "Lexilla lexer receptor", record.id, record.path, "PARTIAL",
                {"framework": "Lexilla", "receptor_type": "lexer_factory_or_catalogue",
                 "capability_provenance": "COUPLED", "token": raw}, [eid],
            ))
            out.edges.append(Edge(stable_id("edge", nid, framework, "requires"), nid, framework, "requires", "PARTIAL", {}, [eid]))

        # A generic Scintilla reference with no exact messages still matters, but it does not prove a capability.
        if not seen and SCINTILLA_REF_RE.search(text):
            m = SCINTILLA_REF_RE.search(text)
            assert m is not None
            line = line_for(m.start())
            raw = m.group(0)
            eid = stable_id("evidence", record.id, self.name, "generic-ref", raw, line)
            out.evidence.append(Evidence(eid, record.id, record.path, line, line, "DIRECT", self.name, raw))
            nid = stable_id("node", record.id, "scintilla_integration", line)
            out.nodes.append(Node(nid, "framework_coupling", "Scintilla integration", record.id, record.path, "PARTIAL",
                                  {"framework": "Scintilla", "token": raw}, [eid]))
            out.edges.append(Edge(stable_id("edge", nid, framework, "requires"), nid, framework, "requires", "PARTIAL", {}, [eid]))
        return out
