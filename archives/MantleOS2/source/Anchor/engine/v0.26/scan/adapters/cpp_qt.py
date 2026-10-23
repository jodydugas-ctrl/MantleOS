from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import bisect
import re

from .base import Adapter
from .qt_ui import INTERACTIVE_WIDGETS
from ..inventory import FileRecord
from ..model import Edge, Evidence, ExtractionResult, Finding, Node, stable_id
from ..cpp_structure import (find_function_regions, find_class_regions, containing_region, iter_calls,
                             iter_local_declarations, iter_member_declarations, iter_this_assignments, mask_cpp)


CONNECT_RE = re.compile(r"connect\s*\(\s*([^,\n]+)\s*,\s*&?([\w:<>]+)::([\w]+)", re.MULTILINE)
CONNECT_SLOT_RE = re.compile(
    r"connect\s*\(\s*([^,\n]+)\s*,\s*&([\w:<>]+)::([\w]+)\s*,\s*([^,\n]+)\s*,\s*&([\w:<>]+)::([\w]+)\s*\)",
    re.MULTILINE,
)
LEGACY_CONNECT_RE = re.compile(
    r"connect\s*\(\s*([^,\n]+)\s*,\s*SIGNAL\s*\(\s*([A-Za-z_]\w*)\s*\([^)]*\)\s*\)\s*,"
    r"\s*([^,\n]+)\s*,\s*SLOT\s*\(\s*([A-Za-z_~]\w*(?:::\w+)*)\s*\([^)]*\)\s*\)\s*\)",
    re.MULTILINE,
)
QTIMER_SINGLESHOT_SLOT_RE = re.compile(
    r"QTimer::singleShot\s*\(\s*([^,\n]+)\s*,\s*([^,\n]+)\s*,\s*SLOT\s*\(\s*([A-Za-z_~]\w*(?:::\w+)*)\s*\([^)]*\)\s*\)\s*\)",
    re.MULTILINE,
)

QTCONCURRENT_ASSIGN_RE = re.compile(
    r"(?:\bauto\s+|\bQFuture\s*<[^;=]+>\s+)([A-Za-z_]\w*)\s*=\s*"
    r"QtConcurrent::run\s*\(([^;]+)\)\s*;",
    re.MULTILINE,
)
QTCONCURRENT_RUN_RE = re.compile(r"QtConcurrent::run\s*\(", re.MULTILINE)
QFUTURE_SETFUTURE_RE = re.compile(
    r"\b([A-Za-z_]\w*)\s*(?:\.|->)\s*setFuture\s*\(\s*([A-Za-z_]\w*)\s*\)\s*;",
    re.MULTILINE,
)

CONNECT_LAMBDA_RE = re.compile(
    r"connect\s*\(\s*([^,\n]+)\s*,\s*&([\w:<>]+)::([\w]+)\s*,\s*([^,\n]+)\s*,\s*\[([^\]]*)\]\s*\(",
    re.MULTILINE,
)
TIMER_START_RE = re.compile(r"\b([A-Za-z_]\w*)\s*(?:\.|->)\s*start\s*\(([^;]+)\)\s*;")
TIMER_SINGLE_RE = re.compile(r"\b([A-Za-z_]\w*)\s*(?:\.|->)\s*setSingleShot\s*\(\s*(true|false)\s*\)\s*;", re.IGNORECASE)
EDITOR_ACTION_RE = re.compile(r"connectEditorAction\s*\(\s*ui->(action\w+)\s*,\s*&([\w:]+)::(\w+)(?:\s*,\s*([^\)]+))?\)")
UI_NAMED_RE = re.compile(r"ui->([A-Za-z_]\w*)")
NEW_QACTION_ASSIGN_RE = re.compile(
    r"(?:\bauto\s*\*?|\bQAction\s*\*?)\s*([A-Za-z_]\w*)\s*=\s*new\s+QAction\s*\(([^;\n]*)\)"
)
ADD_ACTION_ASSIGN_RE = re.compile(
    r"(?:\bauto\s*\*?|\bQAction\s*\*?)\s*([A-Za-z_]\w*)\s*=\s*[^;\n]*?(?:->|\.)addAction\s*\(([^;\n]*)\)"
)
NEW_QACTION_RE = re.compile(r"new\s+QAction\s*\(([^;\n]*)\)")
ADD_ACTION_RE = re.compile(r"(?:->|\.)addAction\s*\(([^;\n]*)\)")
QSHORTCUT_ASSIGN_RE = re.compile(
    r"(?:\bauto\s*\*?|\bQShortcut\s*\*?)\s*([A-Za-z_]\w*)\s*=\s*new\s+QShortcut\s*\(([^;\n]*)\)"
)

ACTION_REGISTRY_INSERT_RE = re.compile(
    r'\b([A-Za-z_]\w*)\s*\.\s*insert\s*\(\s*"([^"]+)"\s*,\s*([A-Za-z_]\w*)\s*\)'
)
ACTION_CLONE_CALL_RE = re.compile(
    r'(?:(\b[A-Za-z_]\w*)\s*(?:\.|->)\s*)?addCloneOfAction\s*\(\s*([^,\n]+)\s*,\s*"([^"]+)"\s*\)'
)
PAYLOAD_KEY_ASSIGN_RE = re.compile(
    r'\b(?:auto|QString)\s+([A-Za-z_]\w*)\s*=\s*([A-Za-z_]\w*)\s*->\s*data\s*\(\s*\)'
    r'\s*\.\s*toStringList\s*\(\s*\)\s*\.\s*first\s*\(\s*\)\s*;'
)
KEY_EQ_RE = re.compile(
    r'(?:if|else\s+if)\s*\(\s*([A-Za-z_]\w*)\s*==\s*"([^"]+)"\s*\)'
)
KEY_PREFIX_RE = re.compile(
    r'(?:if|else\s+if)\s*\(\s*([A-Za-z_]\w*)\s*\.\s*startsWith\s*\(\s*"([^"]+)"\s*\)\s*\)'
)
DYNAMIC_KEY_SETDATA_RE = re.compile(
    r'\b([A-Za-z_]\w*)\s*->\s*setData\s*\(\s*"([^"]+)"\s*\+\s*QString::number\s*\(\s*([A-Za-z_]\w*)\s*\)\s*\)'
)
FOR_BOUND_RE = re.compile(
    r'for\s*\(\s*int\s+([A-Za-z_]\w*)\s*=\s*0\s*;\s*\1\s*<\s*([A-Za-z_]\w*)\s*;[^)]*\)'
)

_PROGRAMMATIC_WIDGET_CLASS_RE = "|".join(sorted(map(re.escape, INTERACTIVE_WIDGETS), key=len, reverse=True))
PROGRAMMATIC_WIDGET_ASSIGN_RE = re.compile(
    rf"(?:\bauto\s*\*?|\b(?:{_PROGRAMMATIC_WIDGET_CLASS_RE})\s*\*+)\s*"
    rf"([A-Za-z_]\w*)\s*=\s*new\s+({_PROGRAMMATIC_WIDGET_CLASS_RE})\s*\(([^;\n]*)\)"
)
SET_READONLY_TRUE_RE = re.compile(r"\b([A-Za-z_]\w*)\s*(?:->|\.)\s*setReadOnly\s*\(\s*true\s*\)")
SET_SHORTCUT_RE = re.compile(r"ui->(action\w+)\s*->\s*setShortcuts?\s*\(([^;]+)\)")
INCLUDE_RE = re.compile(r"^\s*#\s*include\s*[<\"]([^>\"]+)[>\"]", re.MULTILINE)
IFDEF_RE = re.compile(r"^\s*#\s*(?:ifn?def|if)\s+(.+)$", re.MULTILINE)
DEFINE_RE = re.compile(r"^\s*#\s*define\s+([A-Za-z_]\w*)(?:\s*\(([^)]*)\))?", re.MULTILINE)
COND_DIRECTIVE_RE = re.compile(r"^\s*#\s*(if|ifdef|ifndef|elif|else|endif)\b(.*)$", re.MULTILINE)
QT_CODEGEN_RE = re.compile(r"\b(Q_OBJECT|Q_GADGET|Q_NAMESPACE|Q_PLUGIN_METADATA|Q_INTERFACES)\b")
FUNC_RE = re.compile(r"^[\t ]*(?:[\w:<>,~*&]+[\t ]+)+([\w:~]+)\s*\([^;{}]*\)\s*(?:const\s*)?\{", re.MULTILINE)

ADD_POSITIONAL_RE = re.compile(r"\b([A-Za-z_]\w*)\s*\.\s*addPositionalArgument\s*\(\s*\"([^\"]+)\"([^;]*)\)")
ADD_OPTIONS_BLOCK_RE = re.compile(r"\b([A-Za-z_]\w*)\s*\.\s*addOptions\s*\(\s*\{(.*?)\}\s*\)\s*;", re.DOTALL)
OPTION_ENTRY_RE = re.compile(r"\{\s*\"([^\"]+)\"\s*,\s*\"([^\"]*)\"")
ADD_OPTION_LITERAL_RE = re.compile(r"\b([A-Za-z_]\w*)\s*\.\s*addOption\s*\(\s*QCommandLineOption\s*\(\s*\"([^\"]+)\"")
CLI_USE_RE = re.compile(r"\b([A-Za-z_]\w*)\s*\.\s*(isSet|value)\s*\(\s*\"([^\"]+)\"\s*\)")
POSITIONAL_USE_RE = re.compile(r"\b([A-Za-z_]\w*)\s*\.\s*positionalArguments\s*\(\s*\)")
QCOMMANDLINE_PARSER_VAR_RE = re.compile(
    r"\bQCommandLineParser\s*(?:[*&]\s*)?([A-Za-z_]\w*)\b"
)

EVENT_METHOD_TYPES = {
    "dropEvent": "drag_drop",
    "dragEnterEvent": "drag_drop_acceptance",
    "dragMoveEvent": "drag_drop",
    "keyPressEvent": "keyboard_event",
    "keyReleaseEvent": "keyboard_event",
    "mousePressEvent": "pointer_event",
    "mouseReleaseEvent": "pointer_event",
    "mouseDoubleClickEvent": "pointer_event",
    "mouseMoveEvent": "pointer_event",
    "wheelEvent": "pointer_event",
    "contextMenuEvent": "context_menu",
    "closeEvent": "window_close",
    "focusInEvent": "focus_event",
    "focusOutEvent": "focus_event",
}
FILE_OPEN_RE = re.compile(r"QEvent::FileOpen")

DIALOG_PATTERNS = {
    "file_open_dialog": r"QFileDialog::getOpenFileNames?\s*\(",
    "file_save_dialog": r"QFileDialog::getSaveFileName\s*\(",
    "folder_dialog": r"QFileDialog::getExistingDirectory\s*\(",
    "input_dialog": r"QInputDialog::(?:getText|getItem|getInt|getDouble)\s*\(",
    "message_dialog": r"QMessageBox::(?:information|warning|critical|question|about)\s*\(",
    "color_dialog": r"QColorDialog::getColor\s*\(",
    "font_dialog": r"QFontDialog::getFont\s*\(",
}

BOUNDARY_PATTERNS = {
    "subprocess": [r"QProcess::startDetached", r"\bQProcess\b", r"\bsubprocess\b", r"\bsystem\s*\("],
    "filesystem": [r"\bQFile\b", r"\bQDir\b", r"\bQFileInfo\b", r"QStandardPaths", r"std::filesystem"],
    "clipboard": [r"QApplication::clipboard\s*\(", r"QGuiApplication::clipboard\s*\("],
    "settings": [r"\bQSettings\b", r"ApplicationSettings"],
    "network": [r"QNetwork", r"https?://", r"QSimpleUpdater"],
    "ipc": [r"SingleApplication", r"sendMessage", r"receivedMessage", r"QLocalSocket", r"QLocalServer"],
    "printing": [r"QPrinter", r"QPrintPreviewDialog", r"QPrintDialog"],
    "environment": [r"qEnvironmentVariable", r"getenv\s*\("],
    "desktop_service": [r"QDesktopServices::openUrl"],
}
EXTENSION_PATTERNS = [
    ("dynamic_library", r"QLibrary|dlopen\s*\(|LoadLibrary\s*\("),
    ("plugin", r"QPluginLoader|plugin|add-?on|extension"),
    ("script_engine", r"\bLua\b|lua_State|QJSEngine|Python"),
    ("registration", r"register(?:Tool|Command|Plugin|Extension)\s*\("),
]

# High-confidence effect/feedback APIs that can be recognized from call syntax without knowing
# application-specific semantics. Receiver-name heuristics are kept separate and marked PARTIAL.
QUALIFIED_EFFECTS = {
    ("QFile", "remove"): ("filesystem_write", "filesystem", "write"),
    ("QFile", "rename"): ("filesystem_write", "filesystem", "write"),
    ("QFile", "copy"): ("filesystem_write", "filesystem", "write"),
    ("QFile", "setPermissions"): ("filesystem_write", "filesystem", "write"),
    ("QDir", "remove"): ("filesystem_write", "filesystem", "write"),
    ("QDir", "rename"): ("filesystem_write", "filesystem", "write"),
    ("QDir", "mkpath"): ("filesystem_write", "filesystem", "write"),
    ("QDir", "rmpath"): ("filesystem_write", "filesystem", "write"),
    ("QProcess", "startDetached"): ("subprocess_launch", "subprocess", "outbound"),
    ("QProcess", "execute"): ("subprocess_launch", "subprocess", "outbound"),
    ("QProcess", "start"): ("subprocess_launch", "subprocess", "outbound"),
    ("QSettings", "setValue"): ("settings_write", "settings", "write"),
    ("QSettings", "remove"): ("settings_write", "settings", "write"),
    ("QSettings", "clear"): ("settings_write", "settings", "write"),
    ("QSettings", "sync"): ("settings_sync", "settings", "write"),
    ("QSettings", "value"): ("settings_read", "settings", "read"),
    ("QSettings", "contains"): ("settings_read", "settings", "read"),
    ("QClipboard", "setText"): ("clipboard_write", "clipboard", "write"),
    ("QClipboard", "setMimeData"): ("clipboard_write", "clipboard", "write"),
    ("QClipboard", "text"): ("clipboard_read", "clipboard", "read"),
    ("QClipboard", "mimeData"): ("clipboard_read", "clipboard", "read"),
    ("QLocalSocket", "write"): ("ipc_send", "ipc", "outbound"),
    ("QLocalSocket", "connectToServer"): ("ipc_connect", "ipc", "outbound"),
    ("QLocalServer", "listen"): ("ipc_listen", "ipc", "inbound"),
    ("QPrinter", "newPage"): ("print_job", "printing", "outbound"),
    ("QDesktopServices", "openUrl"): ("desktop_open", "desktop_service", "outbound"),
    ("QToolTip", "showText"): ("ui_feedback", "ui", "outbound"),
    ("QSound", "play"): ("audio_playback", "multimedia", "outbound"),
    ("QSoundEffect", "play"): ("audio_playback", "multimedia", "outbound"),
}

FEEDBACK_CALLS = {
    ("QMessageBox", "information"): "modal_message",
    ("QMessageBox", "warning"): "modal_message",
    ("QMessageBox", "critical"): "modal_message",
    ("QMessageBox", "question"): "modal_question",
    ("QMessageBox", "about"): "modal_message",
    ("QToolTip", "showText"): "tooltip",
    ("QSound", "play"): "audio_feedback",
    ("QSoundEffect", "play"): "audio_feedback",
}

RECEIVER_EFFECT_METHODS = {
    "write": ("write_candidate", "filesystem", "write"),
    "commit": ("commit_candidate", "persistence", "write"),
    "setValue": ("settings_write_candidate", "settings", "write"),
    "sync": ("settings_sync_candidate", "settings", "write"),
    "sendMessage": ("ipc_send_candidate", "ipc", "outbound"),
    "setText": ("clipboard_or_ui_write_candidate", "unknown", "write"),
    "setMimeData": ("clipboard_write_candidate", "clipboard", "write"),
    "connectToServer": ("ipc_connect_candidate", "ipc", "outbound"),
    "listen": ("ipc_listen_candidate", "ipc", "inbound"),
    "start": ("subprocess_launch_candidate", "subprocess", "outbound"),
}

FEEDBACK_METHOD_NAMES = {
    "showMessage": "status_message",
    "setWindowTitle": "window_title",
    "setStatusTip": "status_tip",
    "setToolTip": "tooltip_property",
    "update": "repaint_request",
    "repaint": "repaint_request",
}


class CppQtAdapter(Adapter):
    name = "cpp_qt"
    version = "16"

    def accepts(self, record: FileRecord) -> bool:
        return record.language in {"C", "C++", "C++ Header", "C/C++ Header"} and not record.is_binary

    def extract(self, root: Path, record: FileRecord, text: str) -> ExtractionResult:
        out = ExtractionResult()
        line_starts = [0]
        for m in re.finditer("\n", text):
            line_starts.append(m.end())

        def line_for(pos: int) -> int:
            return bisect.bisect_right(line_starts, pos)

        # Mask once per translation unit. Structural helper calls below reuse this same-length view;
        # recomputing it for every class/function made large vendored translation units quadratic.
        masked_text = mask_cpp(text)

        def evidence(tag: str, m: re.Match | None = None, excerpt: str | None = None) -> str:
            if m is not None:
                line = line_for(m.start())
                raw = text[m.start():m.end()].strip().replace("\n", " ")[:500]
            else:
                line = None
                raw = excerpt
            eid = stable_id("evidence", record.id, self.name, tag, line, raw)
            out.evidence.append(Evidence(eid, record.id, record.path, line, line, "DIRECT", self.name, raw))
            return eid

        file_node = stable_id("node", record.id, "translation_unit")
        out.nodes.append(Node(file_node, "translation_unit", record.path, record.id, record.path, "MAPPED", {"language": record.language}, []))

        for m in INCLUDE_RE.finditer(text):
            name = m.group(1)
            eid = evidence(f"include:{name}", m)
            dep = stable_id("node", "include", name)
            out.nodes.append(Node(dep, "dependency_reference", name, None, None, "MAPPED", {"mechanism": "include"}, [eid]))
            out.edges.append(Edge(stable_id("edge", file_node, dep, "includes"), file_node, dep, "includes", "MAPPED", {}, [eid]))

        # Preprocessor and Qt meta-object declarations are part of the static anatomy. The fallback
        # layer records them as provenance/conditions; it does not pretend to evaluate arbitrary macros.
        for m in DEFINE_RE.finditer(text):
            name = m.group(1)
            eid = evidence(f"macro:{name}", m)
            nid = stable_id("node", record.id, "macro_definition", name, line_for(m.start()))
            out.nodes.append(Node(nid, "preprocessor_macro", name, record.id, record.path, "MAPPED",
                                  {"macro": name, "parameters": m.group(2), "line": line_for(m.start())}, [eid]))
            out.edges.append(Edge(stable_id("edge", file_node, nid, "declares"), file_node, nid, "declares", "MAPPED", {}, [eid]))

        for m in COND_DIRECTIVE_RE.finditer(text):
            directive, expr = m.group(1), m.group(2).strip()
            eid = evidence(f"conditional:{directive}:{expr}", m)
            nid = stable_id("node", record.id, "conditional_compilation", directive, expr, line_for(m.start()))
            out.nodes.append(Node(nid, "conditional_compilation", directive, record.id, record.path, "PARTIAL",
                                  {"directive": directive, "expression": expr or None, "line": line_for(m.start()),
                                   "meaning": "branch presence recorded; branch truth not evaluated by fallback parser"}, [eid]))
            out.edges.append(Edge(stable_id("edge", file_node, nid, "contains_condition"), file_node, nid, "contains_condition", "MAPPED", {}, [eid]))

        for m in QT_CODEGEN_RE.finditer(text):
            macro = m.group(1)
            eid = evidence(f"qt-codegen:{macro}", m)
            nid = stable_id("node", record.id, "qt_codegen", macro, line_for(m.start()))
            out.nodes.append(Node(nid, "generated_code_receptor", macro, record.id, record.path, "PARTIAL",
                                  {"framework": "Qt", "generator_family": "moc", "macro": macro,
                                   "generated_code_not_executed": True}, [eid]))
            out.edges.append(Edge(stable_id("edge", file_node, nid, "requires_codegen"), file_node, nid, "requires_codegen", "PARTIAL", {}, [eid]))

        # Class member declarations provide conservative static receiver types for fallback member-call
        # resolution. They are direct source anatomy, not a guess about runtime object identity.
        for class_region in find_class_regions(text, masked_text=masked_text, line_starts=line_starts):
            for member in iter_member_declarations(
                text, class_region, masked_text=masked_text, line_starts=line_starts
            ):
                mm = _SpanMatch(member["start"], member["end"], text[member["start"]:member["end"]])
                eid = evidence(
                    f"member:{member['owner_class']}:{member['member']}:{member['declared_type']}:{member['line']}",
                    mm,
                )
                nid = stable_id(
                    "node", record.id, "member_symbol", member["owner_class"], member["member"], member["line"]
                )
                out.nodes.append(Node(
                    nid, "member_symbol", f"{member['owner_class']}::{member['member']}",
                    record.id, record.path, "MAPPED",
                    {"owner_class": member["owner_class"], "member_name": member["member"],
                     "declared_type": member["declared_type"], "static_type": member["static_type"],
                     "pointer": member["pointer"], "line": member["line"],
                     "parser": "brace_aware_cpp_fallback"}, [eid]
                ))
                out.edges.append(Edge(
                    stable_id("edge", file_node, nid, "declares"), file_node, nid, "declares", "MAPPED", {}, [eid]
                ))

        # Brace-aware function regions let later extraction associate calls/effects with the function
        # that contains them. This remains a conservative source parser, not a compiler AST.
        function_nodes: dict[str, list[str]] = {}
        function_region_nodes: dict[tuple[int, int], str] = {}
        event_function_nodes: list[tuple[_NamedSpanMatch, str, str]] = []
        function_regions = find_function_regions(text, masked_text=masked_text, line_starts=line_starts)
        for region in function_regions:
            name = region.name
            fm = _NamedSpanMatch(region.start, region.body_start, text[region.start:region.body_start], name)
            eid = evidence(f"function:{name}", fm)
            nid = stable_id("node", record.id, "function", name, region.start_line)
            function_nodes.setdefault(name, []).append(nid)
            function_region_nodes[(region.start, region.end)] = nid
            out.nodes.append(Node(
                nid, "symbol", name, record.id, record.path, "PARTIAL",
                {"symbol_type": "function", "qualified_name": name, "line": region.start_line,
                 "end_line": region.end_line, "parser": "brace_aware_cpp_fallback"}, [eid]
            ))
            bare = name.rsplit("::", 1)[-1]
            if bare in EVENT_METHOD_TYPES:
                event_function_nodes.append((fm, nid, EVENT_METHOD_TYPES[bare]))

        def enclosing_function(pos: int):
            region = containing_region(function_regions, pos)
            if region is None:
                return None, None
            return region, function_region_nodes.get((region.start, region.end))

        def _match_delim(open_pos: int, opener: str, closer: str) -> int | None:
            depth = 0
            for i in range(open_pos, len(masked_text)):
                c = masked_text[i]
                if c == opener:
                    depth += 1
                elif c == closer:
                    depth -= 1
                    if depth == 0:
                        return i + 1
            return None

        def _lambda_body_span(match_end: int) -> tuple[int, int] | None:
            # CONNECT_LAMBDA_RE ends just after the lambda parameter-list opening parenthesis.
            param_open = max(0, match_end - 1)
            param_end = _match_delim(param_open, "(", ")")
            if param_end is None:
                return None
            brace_open = masked_text.find("{", param_end, min(len(masked_text), param_end + 600))
            if brace_open < 0:
                return None
            brace_end = _match_delim(brace_open, "{", "}")
            if brace_end is None:
                return None
            return brace_open + 1, brace_end - 1

        # Dynamic human-facing objects must have identity before connect() parsing so wiring can target
        # the same node instead of an unrelated sender placeholder.
        dynamic_actions: dict[str, str] = {}
        claimed_new_action_starts: set[int] = set()
        claimed_add_action_starts: set[int] = set()
        for rx, mechanism in ((NEW_QACTION_ASSIGN_RE, "new_QAction"), (ADD_ACTION_ASSIGN_RE, "addAction_return")):
            for m in rx.finditer(text):
                var, args = m.group(1), m.group(2).strip()
                eid = evidence(f"dynamic-action:{var}:{mechanism}", m)
                nid = stable_id("node", record.id, "dynamic_qaction", var)
                dynamic_actions[var] = nid
                out.nodes.append(Node(nid, "surface_factory_output", var, record.id, record.path, "MAPPED",
                                      {"framework": "Qt", "surface_type": "QAction", "surface_role": "input",
                                       "variable": var, "constructor": args, "mechanism": mechanism}, [eid]))
                if mechanism == "new_QAction":
                    inner = text.find("new QAction", m.start(), m.end())
                    if inner >= 0:
                        claimed_new_action_starts.add(inner)
                else:
                    inner = text.find("addAction", m.start(), m.end())
                    if inner >= 0:
                        claimed_add_action_starts.add(inner)

        # Keyed QAction registries represent semantic behaviors independently of their physical
        # QAction instances.  A single semantic action may be cloned into a menu bar, context menu,
        # hidden shortcut carrier, or platform-native menu.  Keep that identity separate from each
        # route instance so coverage is not inflated by clones.
        semantic_actions: dict[str, str] = {}
        for m in ACTION_REGISTRY_INSERT_RE.finditer(text):
            registry, key, variable = m.group(1), m.group(2), m.group(3)
            eid = evidence(f"semantic-action:{registry}:{key}", m)
            aid = stable_id("node", "qt_semantic_action", key)
            semantic_actions[key] = aid
            out.nodes.append(Node(
                aid, "semantic_action", key, record.id, record.path, "MAPPED",
                {"framework": "Qt", "semantic_key": key, "registry": registry,
                 "registry_variable": variable, "mechanism": "keyed_qaction_registry"}, [eid],
            ))
            out.edges.append(Edge(
                stable_id("edge", file_node, aid, "declares_semantic_action"), file_node, aid,
                "declares_semantic_action", "MAPPED", {}, [eid],
            ))

        for m in ACTION_CLONE_CALL_RE.finditer(text):
            manager, parent_expr, key = m.group(1) or "this", m.group(2).strip(), m.group(3)
            eid = evidence(f"action-clone:{key}:{parent_expr}", m)
            aid = semantic_actions.get(key) or stable_id("node", "qt_semantic_action", key)
            if key not in semantic_actions:
                out.nodes.append(Node(
                    aid, "semantic_action", key, record.id, record.path, "PARTIAL",
                    {"framework": "Qt", "semantic_key": key,
                     "referenced_via": "addCloneOfAction"}, [eid],
                ))
            iid = stable_id("node", record.id, "qt_action_clone", key, parent_expr, line_for(m.start()))
            out.nodes.append(Node(
                iid, "surface_instance", key, record.id, record.path, "MAPPED",
                {"framework": "Qt", "surface_type": "QAction", "surface_role": "input",
                 "semantic_key": key, "parent_expression": parent_expr, "manager_expression": manager,
                 "mechanism": "addCloneOfAction"}, [eid],
            ))
            out.edges.append(Edge(
                stable_id("edge", aid, iid, "has_surface_instance"), aid, iid,
                "has_surface_instance", "MAPPED", {"route": parent_expr}, [eid],
            ))

        # Runtime-populated indexed QAction slots are bounded dynamic surface families.  Preserve the
        # family and its static bound expression without pretending that every slot is always visible.
        loop_bounds: list[tuple[str, str, int, int]] = []
        for fm in FOR_BOUND_RE.finditer(text):
            loop_var, bound_expr = fm.group(1), fm.group(2)
            brace_open = masked_text.find("{", fm.end(), min(len(masked_text), fm.end() + 300))
            if brace_open < 0:
                continue
            brace_end = _match_delim(brace_open, "{", "}")
            if brace_end is None:
                continue
            loop_bounds.append((loop_var, bound_expr, brace_open, brace_end))
        for m in DYNAMIC_KEY_SETDATA_RE.finditer(text):
            action_var, prefix, index_var = m.group(1), m.group(2), m.group(3)
            enclosing = next((x for x in loop_bounds if x[0] == index_var and x[2] <= m.start() < x[3]), None)
            if enclosing is None:
                continue
            _, bound_expr, loop_start, loop_end = enclosing
            eid = evidence(f"dynamic-action-family:{prefix}:{bound_expr}", m)
            fid = stable_id("node", "qt_dynamic_action_family", prefix, bound_expr)
            out.nodes.append(Node(
                fid, "dynamic_surface_family", prefix, record.id, record.path, "MAPPED",
                {"framework": "Qt", "surface_type": "QAction", "surface_role": "input",
                 "family_prefix": prefix, "bound_expression": bound_expr,
                 "index_variable": index_var, "action_variable": action_var,
                 "visibility": "runtime_populated", "mechanism": "indexed_payload_family"}, [eid],
            ))
            family_action = stable_id("node", "qt_semantic_action", prefix + "*")
            out.nodes.append(Node(
                family_action, "semantic_action", prefix + "*", record.id, record.path, "PARTIAL",
                {"framework": "Qt", "semantic_key": prefix + "*", "dynamic_family_id": fid,
                 "mechanism": "dynamic_payload_family"}, [eid],
            ))
            out.edges.append(Edge(
                stable_id("edge", family_action, fid, "has_surface_family"), family_action, fid,
                "has_surface_family", "MAPPED", {"bound_expression": bound_expr}, [eid],
            ))

        # Payload-key dispatch is the semantic bridge from a physical QAction instance to the
        # behavior selected by its data() discriminator.  This is intentionally source-derived and
        # does not infer unobserved keys.
        payload_assignments: list[tuple[str, str, int, int]] = []
        for m in PAYLOAD_KEY_ASSIGN_RE.finditer(text):
            key_var, action_var = m.group(1), m.group(2)
            region, _ = enclosing_function(m.start())
            if region is not None:
                payload_assignments.append((key_var, action_var, region.start, region.end))
        for key_var, action_var, region_start, region_end in payload_assignments:
            region_text = text[region_start:region_end]
            seen_dispatch_keys: dict[tuple[str, str], tuple[int, str]] = {}
            for rx, dispatch_kind, suffix in (
                (KEY_EQ_RE, "payload_key_equality", ""),
                (KEY_PREFIX_RE, "payload_key_prefix", "*"),
            ):
                for km in rx.finditer(region_text):
                    if km.group(1) != key_var:
                        continue
                    key = km.group(2) + suffix
                    abs_start = region_start + km.start()
                    abs_end = region_start + km.end()
                    fake = _SpanMatch(abs_start, abs_end, text[abs_start:abs_end])
                    eid = evidence(f"payload-dispatch:{dispatch_kind}:{key}", fake)
                    did = stable_id("node", record.id, "qt_payload_dispatch", key, line_for(abs_start))
                    out.nodes.append(Node(
                        did, "dispatch_case", key, record.id, record.path, "MAPPED",
                        {"framework": "Qt", "dispatch_kind": dispatch_kind, "semantic_key": key,
                         "key_variable": key_var, "action_variable": action_var}, [eid],
                    ))
                    aid = stable_id("node", "qt_semantic_action", key)
                    out.nodes.append(Node(
                        aid, "semantic_action", key, record.id, record.path, "PARTIAL",
                        {"framework": "Qt", "semantic_key": key,
                         "referenced_via": "payload_dispatch"}, [eid],
                    ))
                    out.edges.append(Edge(
                        stable_id("edge", aid, did, "dispatches_to"), aid, did, "dispatches_to",
                        "MAPPED", {"dispatch_kind": dispatch_kind}, [eid],
                    ))
                    duplicate_key = (dispatch_kind, key)
                    if duplicate_key in seen_dispatch_keys:
                        first_line, first_eid = seen_dispatch_keys[duplicate_key]
                        out.findings.append(Finding(
                            stable_id("finding", record.id, "duplicate-payload-dispatch", dispatch_kind, key, first_line, line_for(abs_start)),
                            "duplicate_dispatch_case",
                            f"Duplicate payload dispatch case: {key}",
                            "PARTIAL",
                            {"semantic_key": key, "dispatch_kind": dispatch_kind,
                             "first_line": first_line, "duplicate_line": line_for(abs_start),
                             "meaning": "same discriminator appears more than once in one keyed dispatch region; reachability/intent is not inferred"},
                            [first_eid, eid],
                        ))
                    else:
                        seen_dispatch_keys[duplicate_key] = (line_for(abs_start), eid)

        read_only_programmatic = {m.group(1) for m in SET_READONLY_TRUE_RE.finditer(text)}
        programmatic_surfaces: dict[str, str] = {}
        for m in PROGRAMMATIC_WIDGET_ASSIGN_RE.finditer(text):
            var, widget_class, args = m.group(1), m.group(2), m.group(3).strip()
            eid = evidence(f"programmatic-widget:{widget_class}:{var}", m)
            nid = stable_id("node", record.id, "programmatic_qt_widget", widget_class, var)
            programmatic_surfaces[var] = nid
            read_only = var in read_only_programmatic
            out.nodes.append(Node(
                nid, "human_surface", var, record.id, record.path, "MAPPED",
                {"framework": "Qt", "surface_type": widget_class,
                 "surface_role": "presented" if read_only else "input",
                 "read_only": read_only,
                 "variable": var, "constructor": args, "mechanism": "programmatic_new"}, [eid]
            ))

        shortcuts: dict[str, str] = {}
        for m in QSHORTCUT_ASSIGN_RE.finditer(text):
            var, args = m.group(1), m.group(2).strip()
            eid = evidence(f"qshortcut:{var}", m)
            nid = stable_id("node", record.id, "qshortcut", var)
            shortcuts[var] = nid
            out.nodes.append(Node(nid, "human_surface", var, record.id, record.path, "MAPPED",
                                  {"framework": "Qt", "surface_type": "QShortcut", "surface_role": "input",
                                   "variable": var, "constructor": args}, [eid]))

        def sender_node(sender: str, eid: str) -> tuple[str, str]:
            normalized = sender.lstrip("&").strip()
            if normalized.startswith("ui->"):
                object_name = normalized.split("ui->", 1)[1].strip()
                if object_name.startswith("action"):
                    nid = stable_id("node", "qt_action", object_name)
                else:
                    nid = stable_id("node", record.id, "qt_ui_ref", object_name)
                out.nodes.append(Node(nid, "surface_reference", object_name, record.id, record.path, "PARTIAL",
                                      {"framework": "Qt", "qt_object_name": object_name,
                                       "surface_type": "ui_object_reference", "surface_role": "input"}, [eid]))
                return nid, normalized
            if normalized in dynamic_actions:
                return dynamic_actions[normalized], normalized
            if normalized in programmatic_surfaces:
                return programmatic_surfaces[normalized], normalized
            if normalized in shortcuts:
                return shortcuts[normalized], normalized
            nid = stable_id("node", "qt_sender", normalized)
            out.nodes.append(Node(nid, "event_source", normalized, record.id, record.path, "PARTIAL", {"framework": "Qt"}, [eid]))
            return nid, normalized

        # Ordinary ui-> accesses are object references, not independent human entrances. They remain
        # graph-visible and uniqueness-resolvable to .ui declarations, while sender_node() separately
        # promotes references that are proven signal senders into the surface denominator.
        for object_name in sorted(set(UI_NAMED_RE.findall(text))):
            eid = evidence(f"ui-object-ref:{object_name}", excerpt=f"ui->{object_name}")
            if object_name.startswith("action"):
                nid = stable_id("node", "qt_action", object_name)
            else:
                nid = stable_id("node", record.id, "qt_ui_ref", object_name)
            out.nodes.append(Node(nid, "ui_object_reference", object_name, record.id, record.path, "PARTIAL",
                                  {"framework": "Qt", "qt_object_name": object_name,
                                   "reference_role": "object_access"}, [eid]))
            out.edges.append(Edge(stable_id("edge", file_node, nid, "references_ui_object"), file_node, nid,
                                  "references_ui_object", "MAPPED", {}, [eid]))

        lambda_spans: list[tuple[int, int, str, str]] = []
        timer_senders: set[str] = set()
        for m in CONNECT_RE.finditer(text):
            sender = m.group(1).strip()
            signal_owner, signal = m.group(2), m.group(3)
            eid = evidence(f"connect:{sender}:{signal}", m)
            src, normalized_sender = sender_node(sender, eid)
            event = stable_id("node", src, "qt_signal_instance", signal_owner, signal)
            out.nodes.append(Node(event, "event", f"{signal_owner}::{signal}", record.id, record.path, "MAPPED",
                                  {"framework": "Qt", "sender_id": src, "sender_expression": normalized_sender}, [eid]))
            out.edges.append(Edge(stable_id("edge", src, event, "emits"), src, event, "emits", "PARTIAL", {}, [eid]))
            if signal_owner == "QTimer" and signal == "timeout":
                timer_senders.add(normalized_sender)
                recurrence = stable_id("node", record.id, "qt_timer", normalized_sender)
                out.nodes.append(Node(recurrence, "recurrence_source", normalized_sender, record.id, record.path, "PARTIAL", {"framework": "Qt", "mechanism": "QTimer::timeout"}, [eid]))
                out.edges.append(Edge(stable_id("edge", recurrence, event, "emits"), recurrence, event, "emits", "PARTIAL", {"temporal": True}, [eid]))

        for m in CONNECT_SLOT_RE.finditer(text):
            sender, signal_owner, signal, receiver, slot_owner, slot = [g.strip() for g in m.groups()]
            eid = evidence(f"connect-slot:{sender}:{signal}:{slot_owner}:{slot}", m)
            src, _ = sender_node(sender, eid)
            event = stable_id("node", src, "qt_signal_instance", signal_owner, signal)
            # Signal events are sender-scoped. Sharing one QAction::triggered node across all senders
            # would create false cross-wiring between unrelated controls.
            out.nodes.append(Node(event, "event", f"{signal_owner}::{signal}", record.id, record.path, "MAPPED",
                                  {"framework": "Qt", "sender_id": src, "sender_expression": sender}, [eid]))
            # Ensure exact sender->event identity exists even if CONNECT_RE already produced it.
            out.edges.append(Edge(stable_id("edge", src, event, "emits"), src, event, "emits", "MAPPED", {}, [eid]))
            handler = stable_id("node", "method_ref", slot_owner, slot)
            out.nodes.append(Node(handler, "handler_reference", f"{slot_owner}::{slot}", record.id, record.path, "MAPPED", {"receiver": receiver, "binding": "qt_connect_method", "qualified_name": f"{slot_owner}::{slot}"}, [eid]))
            out.edges.append(Edge(stable_id("edge", event, handler, "dispatches_to"), event, handler, "dispatches_to", "MAPPED", {"receiver": receiver}, [eid]))

        # Legacy Qt4/Qt5 SIGNAL()/SLOT() syntax is still common in real applications.  Preserve
        # sender-scoped event identity exactly as for method-pointer connect() forms.
        for m in LEGACY_CONNECT_RE.finditer(text):
            sender, signal, receiver, slot = [g.strip() for g in m.groups()]
            eid = evidence(f"legacy-connect:{sender}:{signal}:{receiver}:{slot}", m)
            src, normalized_sender = sender_node(sender, eid)
            event = stable_id("node", src, "qt_signal_instance", "legacy", signal)
            out.nodes.append(Node(event, "event", f"SIGNAL::{signal}", record.id, record.path, "MAPPED",
                                  {"framework": "Qt", "syntax": "SIGNAL_SLOT", "signal": signal,
                                   "sender_id": src, "sender_expression": normalized_sender}, [eid]))
            out.edges.append(Edge(stable_id("edge", src, event, "emits"), src, event, "emits", "MAPPED", {}, [eid]))
            region, _ = enclosing_function(m.start())
            if "::" in slot:
                qualified_slot = slot
                handler_coverage = "MAPPED"
            elif receiver == "this" and region is not None and region.class_scope:
                qualified_slot = f"{region.class_scope}::{slot}"
                handler_coverage = "MAPPED"
            else:
                qualified_slot = slot
                handler_coverage = "PARTIAL"
            handler = stable_id("node", "method_ref", qualified_slot)
            out.nodes.append(Node(handler, "handler_reference", qualified_slot, record.id, record.path, handler_coverage,
                                  {"receiver": receiver, "binding": "qt_legacy_signal_slot",
                                   "qualified_name": qualified_slot, "slot": slot}, [eid]))
            out.edges.append(Edge(stable_id("edge", event, handler, "dispatches_to"), event, handler,
                                  "dispatches_to", handler_coverage, {"receiver": receiver, "legacy_qt_syntax": True}, [eid]))

        # QTimer::singleShot(..., receiver, SLOT(slot())) is an asynchronous control route.  It is not
        # periodic recurrence, but its delayed dispatch must remain visible to deep closure.
        for m in QTIMER_SINGLESHOT_SLOT_RE.finditer(text):
            interval, receiver, slot = [g.strip() for g in m.groups()]
            eid = evidence(f"qtimer-singleshot:{interval}:{receiver}:{slot}", m)
            region, fnid = enclosing_function(m.start())
            if "::" in slot:
                qualified_slot = slot
                handler_coverage = "MAPPED"
            elif receiver == "this" and region is not None and region.class_scope:
                qualified_slot = f"{region.class_scope}::{slot}"
                handler_coverage = "MAPPED"
            else:
                qualified_slot = slot
                handler_coverage = "PARTIAL"
            recurrence = stable_id("node", record.id, "qt_single_shot", line_for(m.start()), interval, qualified_slot)
            out.nodes.append(Node(recurrence, "recurrence_source", "QTimer::singleShot", record.id, record.path, "MAPPED",
                                  {"framework": "Qt", "mechanism": "QTimer::singleShot",
                                   "interval_expression": interval, "single_shot": True}, [eid]))
            handler = stable_id("node", "method_ref", qualified_slot)
            out.nodes.append(Node(handler, "handler_reference", qualified_slot, record.id, record.path, handler_coverage,
                                  {"receiver": receiver, "binding": "qt_timer_single_shot",
                                   "qualified_name": qualified_slot, "slot": slot}, [eid]))
            if fnid:
                out.edges.append(Edge(stable_id("edge", fnid, recurrence, "triggers"), fnid, recurrence,
                                      "triggers", "MAPPED", {"temporal": True}, [eid]))
            out.edges.append(Edge(stable_id("edge", recurrence, handler, "dispatches_to"), recurrence, handler,
                                  "dispatches_to", handler_coverage, {"temporal": True, "single_shot": True}, [eid]))

        # QtConcurrent/QFutureWatcher forms are asynchronous BODY control routes.  Preserve the launch
        # separately from the watcher continuation so deep closure can traverse launch -> watcher ->
        # finished/resultReady signal -> handler without pretending the work is synchronous.
        async_future_tasks: dict[str, str] = {}
        claimed_qtconcurrent_starts: set[int] = set()
        for m in QTCONCURRENT_ASSIGN_RE.finditer(text):
            future_name, args = m.group(1), m.group(2).strip()
            run_start = text.find("QtConcurrent::run", m.start(), m.end())
            if run_start >= 0:
                claimed_qtconcurrent_starts.add(run_start)
            eid = evidence(f"qtconcurrent:{future_name}:{m.start()}", m)
            task = stable_id("node", record.id, "qtconcurrent_task", future_name, line_for(m.start()))
            async_future_tasks[future_name] = task
            out.nodes.append(Node(
                task, "async_task", future_name, record.id, record.path, "MAPPED",
                {"framework": "Qt", "mechanism": "QtConcurrent::run", "future_variable": future_name,
                 "launch_expression": args, "line": line_for(m.start())}, [eid]
            ))
            _, fnid = enclosing_function(m.start())
            if fnid:
                out.edges.append(Edge(stable_id("edge", fnid, task, "triggers_async"), fnid, task,
                                      "triggers_async", "MAPPED", {"asynchronous": True}, [eid]))

        # Preserve unassigned/direct QtConcurrent launches too. Their continuation may be unresolved,
        # but dropping the asynchronous work would falsely imply synchronous closure.
        for m in QTCONCURRENT_RUN_RE.finditer(text):
            if m.start() in claimed_qtconcurrent_starts:
                continue
            eid = evidence(f"qtconcurrent:anonymous:{m.start()}", m)
            task = stable_id("node", record.id, "qtconcurrent_task", line_for(m.start()))
            out.nodes.append(Node(
                task, "async_task", "QtConcurrent::run", record.id, record.path, "PARTIAL",
                {"framework": "Qt", "mechanism": "QtConcurrent::run", "future_variable": None,
                 "line": line_for(m.start()), "continuation_known": False}, [eid]
            ))
            _, fnid = enclosing_function(m.start())
            if fnid:
                out.edges.append(Edge(stable_id("edge", fnid, task, "triggers_async"), fnid, task,
                                      "triggers_async", "PARTIAL", {"asynchronous": True}, [eid]))

        for m in QFUTURE_SETFUTURE_RE.finditer(text):
            watcher, future_name = m.group(1), m.group(2)
            eid = evidence(f"qfuture-set:{watcher}:{future_name}", m)
            watcher_node, normalized_watcher = sender_node(watcher, eid)
            task = async_future_tasks.get(future_name)
            if task is None:
                task = stable_id("node", record.id, "external_future", future_name)
                out.nodes.append(Node(
                    task, "async_task_reference", future_name, record.id, record.path, "PARTIAL",
                    {"framework": "Qt", "mechanism": "QFuture", "future_variable": future_name,
                     "launch_site_observed": False}, [eid]
                ))
            out.edges.append(Edge(
                stable_id("edge", task, watcher_node, "delivers_async_to"), task, watcher_node,
                "delivers_async_to", "MAPPED" if future_name in async_future_tasks else "PARTIAL",
                {"asynchronous": True, "watcher_expression": normalized_watcher,
                 "mechanism": "QFutureWatcher::setFuture"}, [eid]
            ))

        for m in CONNECT_LAMBDA_RE.finditer(text):
            sender, signal_owner, signal, receiver, capture = [g.strip() for g in m.groups()]
            eid = evidence(f"connect-lambda:{sender}:{signal}", m)
            src, _ = sender_node(sender, eid)
            event = stable_id("node", src, "qt_signal_instance", signal_owner, signal)
            out.nodes.append(Node(event, "event", f"{signal_owner}::{signal}", record.id, record.path, "MAPPED",
                                  {"framework": "Qt", "sender_id": src, "sender_expression": sender}, [eid]))
            out.edges.append(Edge(stable_id("edge", src, event, "emits"), src, event, "emits", "MAPPED", {}, [eid]))
            handler = stable_id("node", record.id, "lambda_handler", line_for(m.start()))
            lambda_name = f"lambda@{line_for(m.start())}"
            out.nodes.append(Node(handler, "handler_reference", lambda_name, record.id, record.path, "PARTIAL", {"receiver": receiver, "capture": capture, "binding": "qt_connect_lambda"}, [eid]))
            out.edges.append(Edge(stable_id("edge", event, handler, "dispatches_to"), event, handler, "dispatches_to", "PARTIAL", {"receiver": receiver}, [eid]))
            body_span = _lambda_body_span(m.end())
            if body_span is not None:
                lambda_spans.append((body_span[0], body_span[1], handler, lambda_name))

        timer_single: dict[str, bool] = {}
        for m in TIMER_SINGLE_RE.finditer(text):
            timer_single[m.group(1)] = m.group(2).lower() == "true"
        for m in TIMER_START_RE.finditer(text):
            timer_name, interval = m.group(1), m.group(2).strip()
            if timer_name not in timer_senders:
                continue
            eid = evidence(f"timer-start:{timer_name}", m)
            recurrence = stable_id("node", record.id, "qt_timer", timer_name)
            out.nodes.append(Node(recurrence, "recurrence_source", timer_name, record.id, record.path, "MAPPED",
                                  {"framework": "Qt", "mechanism": "QTimer", "interval_expression": interval,
                                   "single_shot": timer_single.get(timer_name)}, [eid]))

        for m in EDITOR_ACTION_RE.finditer(text):
            action, owner, method, arg = m.group(1), m.group(2), m.group(3), m.group(4)
            eid = evidence(f"editor-action:{action}:{method}", m)
            surface = stable_id("node", "qt_action", action)
            handler = stable_id("node", "method_ref", owner, method, arg or "")
            out.nodes.append(Node(surface, "surface_reference", action, record.id, record.path, "MAPPED", {"framework": "Qt", "qt_object_name": action}, [eid]))
            out.nodes.append(Node(handler, "handler_reference", f"{owner}::{method}", record.id, record.path, "MAPPED", {"argument": arg.strip() if arg else None, "binding": "connectEditorAction", "qualified_name": f"{owner}::{method}"}, [eid]))
            out.edges.append(Edge(stable_id("edge", surface, handler, "dispatches_to"), surface, handler, "dispatches_to", "MAPPED", {"helper_mediated": True}, [eid]))

        # Preserve dynamic factory outputs even when no variable captures the result.
        for m in NEW_QACTION_RE.finditer(text):
            if m.start() in claimed_new_action_starts:
                continue
            eid = evidence("dynamic-qaction-anonymous", m)
            nid = stable_id("node", record.id, "dynamic_qaction", line_for(m.start()))
            out.nodes.append(Node(nid, "surface_factory_output", "dynamic QAction", record.id, record.path, "PARTIAL", {"framework": "Qt", "surface_type": "QAction", "surface_role": "input", "constructor": m.group(1).strip()}, [eid]))

        for m in ADD_ACTION_RE.finditer(text):
            if m.start() in claimed_add_action_starts:
                continue
            eid = evidence("add-action", m)
            nid = stable_id("node", record.id, "dynamic_add_action", line_for(m.start()))
            out.nodes.append(Node(nid, "dynamic_registration", "addAction", record.id, record.path, "PARTIAL", {"arguments": m.group(1).strip()}, [eid]))

        for m in SET_SHORTCUT_RE.finditer(text):
            action, seq = m.group(1), m.group(2).strip()
            eid = evidence(f"shortcut:{action}", m)
            surface = stable_id("node", "qt_action", action)
            shortcut = stable_id("node", record.id, "shortcut", action, seq)
            out.nodes.append(Node(shortcut, "human_surface", seq, record.id, record.path, "MAPPED", {"framework": "Qt", "surface_type": "keyboard_shortcut", "surface_role": "input", "action": action}, [eid]))
            out.edges.append(Edge(stable_id("edge", shortcut, surface, "alternate_route_to"), shortcut, surface, "alternate_route_to", "MAPPED", {}, [eid]))

        # Command-line options are human control surfaces too. Parse declared options/positionals and
        # link literal isSet/value consumers so the denominator is mechanically visible.
        cli_surfaces: dict[str, str] = {}
        cli_parser_vars = set(QCOMMANDLINE_PARSER_VAR_RE.findall(text))
        for m in ADD_OPTIONS_BLOCK_RE.finditer(text):
            block = m.group(2)
            base = m.start(2)
            cli_parser_vars.add(m.group(1))
            for em in OPTION_ENTRY_RE.finditer(block):
                name, description = em.group(1), em.group(2)
                pos = base + em.start()
                fake = _SpanMatch(pos, pos + len(em.group(0)), em.group(0))
                eid = evidence(f"cli-option:{name}", fake)
                nid = stable_id("node", "cli_option", name)
                cli_surfaces[name] = nid
                out.nodes.append(Node(nid, "human_surface", f"--{name}", record.id, record.path, "MAPPED",
                                      {"surface_type": "cli_option", "surface_role": "input", "option": name,
                                       "description": description, "parser_variable": m.group(1)}, [eid]))
        for m in ADD_OPTION_LITERAL_RE.finditer(text):
            name = m.group(2)
            cli_parser_vars.add(m.group(1))
            eid = evidence(f"cli-option:{name}", m)
            nid = stable_id("node", "cli_option", name)
            cli_surfaces[name] = nid
            out.nodes.append(Node(nid, "human_surface", f"--{name}", record.id, record.path, "MAPPED",
                                  {"surface_type": "cli_option", "surface_role": "input", "option": name,
                                   "parser_variable": m.group(1)}, [eid]))
        cli_positionals: dict[str, list[tuple[str, str]]] = {}
        for m in ADD_POSITIONAL_RE.finditer(text):
            parser_var, name = m.group(1), m.group(2)
            cli_parser_vars.add(parser_var)
            eid = evidence(f"cli-positional:{name}", m)
            nid = stable_id("node", record.id, "cli_positional", name)
            cli_positionals.setdefault(parser_var, []).append((name, nid))
            out.nodes.append(Node(nid, "human_surface", name, record.id, record.path, "MAPPED",
                                  {"surface_type": "cli_positional", "surface_role": "input", "argument": name,
                                   "parser_variable": parser_var}, [eid]))
        for m in CLI_USE_RE.finditer(text):
            parser_var, use_kind, name = m.group(1), m.group(2), m.group(3)
            if parser_var not in cli_parser_vars:
                continue
            eid = evidence(f"cli-use:{name}:{use_kind}", m)
            surface = cli_surfaces.get(name) or stable_id("node", "cli_option", name)
            if name not in cli_surfaces:
                out.nodes.append(Node(surface, "surface_reference", f"--{name}", record.id, record.path, "PARTIAL",
                                      {"surface_type": "cli_option", "surface_role": "input", "option": name,
                                       "parser_variable": parser_var}, [eid]))
            consumer = stable_id("node", record.id, "cli_consumer", name, use_kind, line_for(m.start()))
            out.nodes.append(Node(consumer, "input_consumer", f"{parser_var}.{use_kind}({name})", record.id, record.path, "MAPPED",
                                  {"input_type": "cli_option", "option": name, "use": use_kind}, [eid]))
            out.edges.append(Edge(stable_id("edge", surface, consumer, "routes_to"), surface, consumer, "routes_to", "MAPPED", {"use": use_kind}, [eid]))
            _, fnid = enclosing_function(m.start())
            if fnid:
                out.edges.append(Edge(stable_id("edge", consumer, fnid, "handled_in"), consumer, fnid, "handled_in", "MAPPED", {}, [eid]))
        for m in POSITIONAL_USE_RE.finditer(text):
            parser_var = m.group(1)
            if parser_var not in cli_parser_vars:
                continue
            eid = evidence(f"cli-positional-use:{parser_var}", m)
            consumer = stable_id("node", record.id, "cli_positional_consumer", parser_var, line_for(m.start()))
            out.nodes.append(Node(consumer, "input_consumer", f"{parser_var}.positionalArguments()", record.id, record.path, "MAPPED",
                                  {"input_type": "cli_positional", "parser_variable": parser_var}, [eid]))
            for name, surface in cli_positionals.get(parser_var, []):
                out.edges.append(Edge(stable_id("edge", surface, consumer, "routes_to"), surface, consumer, "routes_to", "MAPPED",
                                      {"use": "positionalArguments", "argument": name}, [eid]))
            _, fnid = enclosing_function(m.start())
            if fnid:
                out.edges.append(Edge(stable_id("edge", consumer, fnid, "handled_in"), consumer, fnid, "handled_in", "MAPPED", {}, [eid]))

        # M3B deep structural layer: collect direct call syntax inside brace-aware function regions.
        # Calls are first-class references so later cross-file resolution can distinguish a syntactic
        # call from a resolved project-local target. Receiver-typed dispatch remains PARTIAL without AST.
        for region in function_regions:
            caller = function_region_nodes.get((region.start, region.end))
            if not caller:
                continue
            declared_receiver_types: dict[str, set[str]] = {}
            for declaration in iter_local_declarations(
                text, region, masked_text=masked_text, line_starts=line_starts
            ):
                declared_receiver_types.setdefault(declaration["name"], set()).add(declaration["static_type"])
            for call in iter_calls(text, region, masked_text=masked_text):
                cm = _SpanMatch(call["start"], call["end"], text[call["start"]:call["end"]])
                name = call["name"]
                scope = call.get("scope")
                receiver = call.get("receiver")
                qualified = f"{scope}::{name}" if scope else None
                context_qualified = None
                if region.class_scope and (receiver is None or receiver.startswith("this")):
                    context_qualified = f"{region.class_scope}::{name}"
                lambda_ctx = next((x for x in lambda_spans if x[0] <= call["start"] < x[1]), None)
                effective_caller = lambda_ctx[2] if lambda_ctx else caller
                effective_caller_name = lambda_ctx[3] if lambda_ctx else region.name
                receiver_name = re.sub(r"(?:->|\.)\s*$", "", receiver or "").strip()
                receiver_types = declared_receiver_types.get(receiver_name, set()) if receiver_name else set()
                receiver_static_type = next(iter(receiver_types)) if len(receiver_types) == 1 else None
                eid = evidence(f"call:{effective_caller_name}:{qualified or receiver or ''}:{name}:{call['start']}", cm)
                call_id = stable_id("node", record.id, "call", effective_caller_name, line_for(call["start"]), qualified or receiver or "", name)
                out.nodes.append(Node(
                    call_id, "call_reference", qualified or ((receiver or "") + name), record.id, record.path, "PARTIAL",
                    {"callee_name": name, "qualified_name": qualified, "context_qualified_name": context_qualified,
                     "receiver": receiver, "caller_qualified_name": effective_caller_name, "line": line_for(call["start"]),
                     "parser": "brace_aware_cpp_fallback", "receiver_static_type": receiver_static_type,
                     "receiver_type_source": "direct_local_or_parameter_declaration" if receiver_static_type else None}, [eid]
                ))
                out.edges.append(Edge(stable_id("edge", effective_caller, call_id, "calls"), effective_caller, call_id, "calls", "MAPPED", {}, [eid]))

                # High-confidence framework/NEST effects. Receiver-only effects are explicitly candidates.
                effect_spec = None
                effect_status = "MAPPED"
                if scope:
                    effect_spec = QUALIFIED_EFFECTS.get((scope.split("::")[-1], name))
                    if effect_spec is None and scope.startswith("QNetworkAccessManager") and name in {"get", "post", "put", "deleteResource", "sendCustomRequest"}:
                        effect_spec = ("network_io", "network", "outbound")
                    elif effect_spec is None and scope == "QSettings" and name in {"setValue", "sync", "remove", "clear"}:
                        effect_spec = ("settings_write", "settings", "write")
                elif name == "sendMessage" and receiver is None:
                    effect_spec = ("ipc_send_candidate", "ipc", "outbound")
                    effect_status = "PARTIAL"
                elif receiver and name in RECEIVER_EFFECT_METHODS:
                    effect_spec = RECEIVER_EFFECT_METHODS[name]
                    effect_status = "PARTIAL"

                if effect_spec:
                    effect_type, capability, direction = effect_spec
                    effect_id = stable_id("node", record.id, "effect", effective_caller_name, effect_type, line_for(call["start"]), qualified or receiver or name)
                    out.nodes.append(Node(
                        effect_id, "effect", effect_type, record.id, record.path, effect_status,
                        {"effect_type": effect_type, "capability": capability, "direction": direction,
                         "api": qualified or ((receiver or "") + name), "line": line_for(call["start"]),
                         "classification": "qualified_api" if effect_status == "MAPPED" else "receiver_or_name_candidate"}, [eid]
                    ))
                    out.edges.append(Edge(stable_id("edge", effective_caller, effect_id, "produces_effect"), effective_caller, effect_id, "produces_effect", effect_status, {}, [eid]))
                    out.edges.append(Edge(stable_id("edge", call_id, effect_id, "has_effect"), call_id, effect_id, "has_effect", effect_status, {}, [eid]))

                feedback_type = None
                feedback_status = "MAPPED"
                if scope and (scope.split("::")[-1], name) in FEEDBACK_CALLS:
                    feedback_type = FEEDBACK_CALLS[(scope.split("::")[-1], name)]
                elif name in FEEDBACK_METHOD_NAMES:
                    feedback_type = FEEDBACK_METHOD_NAMES[name]
                    feedback_status = "PARTIAL"
                if feedback_type:
                    feedback_id = stable_id("node", record.id, "feedback", effective_caller_name, feedback_type, line_for(call["start"]), qualified or receiver or name)
                    out.nodes.append(Node(
                        feedback_id, "feedback", feedback_type, record.id, record.path, feedback_status,
                        {"feedback_type": feedback_type, "api": qualified or ((receiver or "") + name),
                         "line": line_for(call["start"])}, [eid]
                    ))
                    out.edges.append(Edge(stable_id("edge", effective_caller, feedback_id, "produces_feedback"), effective_caller, feedback_id, "produces_feedback", feedback_status, {}, [eid]))
                    out.edges.append(Edge(stable_id("edge", call_id, feedback_id, "has_feedback"), call_id, feedback_id, "has_feedback", feedback_status, {}, [eid]))

            # Explicit member assignments are direct state-mutation evidence. Unqualified assignments
            # are intentionally not promoted because the fallback parser cannot prove member identity.
            for assign in iter_this_assignments(text, region, masked_text=masked_text):
                am = _SpanMatch(assign["start"], assign["end"], text[assign["start"]:assign["end"]])
                lambda_ctx = next((x for x in lambda_spans if x[0] <= assign["start"] < x[1]), None)
                effective_caller = lambda_ctx[2] if lambda_ctx else caller
                effective_caller_name = lambda_ctx[3] if lambda_ctx else region.name
                eid = evidence(f"state-change:{effective_caller_name}:{assign['member']}:{assign['start']}", am)
                state_id = stable_id("node", record.id, "state_change", effective_caller_name, assign["member"], line_for(assign["start"]))
                out.nodes.append(Node(
                    state_id, "state_change", f"this->{assign['member']}", record.id, record.path, "MAPPED",
                    {"member": assign["member"], "operator": assign["operator"], "line": line_for(assign["start"]),
                     "mechanism": "explicit_this_assignment"}, [eid]
                ))
                out.edges.append(Edge(stable_id("edge", effective_caller, state_id, "changes_state"), effective_caller, state_id, "changes_state", "MAPPED", {}, [eid]))

        # Event override methods are direct human/OS entry surfaces. They are deliberately separate from
        # framework interpretation so gestures remain visible even before deeper semantic analysis.
        for m, function_id, surface_type in event_function_nodes:
            name = m.group(1)
            eid = evidence(f"event-surface:{name}", m)
            sid = stable_id("node", record.id, "event_surface", name, line_for(m.start()))
            out.nodes.append(Node(sid, "human_surface", name, record.id, record.path, "MAPPED",
                                  {"framework": "Qt", "surface_type": surface_type, "surface_role": "input",
                                   "entry_mechanism": "event_override"}, [eid]))
            out.edges.append(Edge(stable_id("edge", sid, function_id, "dispatches_to"), sid, function_id, "dispatches_to", "MAPPED", {"framework_dispatch": True}, [eid]))

        for m in FILE_OPEN_RE.finditer(text):
            eid = evidence("os-file-open", m)
            sid = stable_id("node", record.id, "os_file_open", line_for(m.start()))
            out.nodes.append(Node(sid, "human_surface", "QEvent::FileOpen", record.id, record.path, "MAPPED",
                                  {"framework": "Qt", "surface_type": "os_file_open", "surface_role": "input"}, [eid]))
            # Link to the nearest containing event() function when possible.
            candidates = [(fm.start(), fid) for fm, fid, _ in event_function_nodes if fm.start() <= m.start()]
            if candidates:
                _, fid = max(candidates)
                out.edges.append(Edge(stable_id("edge", sid, fid, "dispatches_to"), sid, fid, "dispatches_to", "PARTIAL", {"nearest_event_override": True}, [eid]))

        # Dialog calls are human interaction surfaces presented by an already-running handler. They are
        # kept as bidirectional/response surfaces and are not mistaken for initial command entry points.
        for dtype, pattern in DIALOG_PATTERNS.items():
            for m in re.finditer(pattern, text):
                eid = evidence(f"dialog:{dtype}:{m.start()}", m)
                sid = stable_id("node", record.id, "dialog_surface", dtype, line_for(m.start()))
                out.nodes.append(Node(sid, "human_surface", dtype, record.id, record.path, "PARTIAL",
                                      {"framework": "Qt", "surface_type": "dialog", "surface_role": "presented",
                                       "dialog_type": dtype}, [eid]))
                _, fnid = enclosing_function(m.start())
                if fnid:
                    out.edges.append(Edge(stable_id("edge", fnid, sid, "opens_surface"), fnid, sid, "opens_surface", "MAPPED", {}, [eid]))
                    if dtype == "message_dialog":
                        out.edges.append(Edge(stable_id("edge", fnid, sid, "produces_feedback"), fnid, sid, "produces_feedback", "MAPPED", {}, [eid]))

        for branch in IFDEF_RE.finditer(text):
            expr = branch.group(1).strip()
            if any(tok in expr for tok in ("Q_OS_", "WIN32", "_WIN32", "APPLE", "UNIX", "linux")):
                eid = evidence(f"platform:{expr}", branch)
                nid = stable_id("node", record.id, "platform_guard", expr, line_for(branch.start()))
                out.nodes.append(Node(nid, "nest_condition", expr, record.id, record.path, "MAPPED", {"condition_type": "compile_time"}, [eid]))

        for kind, patterns in BOUNDARY_PATTERNS.items():
            matches: list[re.Match] = []
            seen_matches: set[tuple[int, int, str]] = set()
            for pattern in patterns:
                # Boundary identifiers must occur in executable/source structure. Comments and literal
                # bodies are masked; literal URLs remain available to the generic text adapter, which
                # records their runtime-vs-reference context without duplicating a Qt boundary.
                for m in re.finditer(pattern, masked_text, re.IGNORECASE):
                    match_key = (m.start(), m.end(), m.group(0).lower())
                    if match_key not in seen_matches:
                        seen_matches.add(match_key)
                        matches.append(m)
            if not matches:
                continue
            nid = stable_id("node", record.id, "nest_boundary", kind)
            evidence_ids: list[str] = []
            function_evidence: dict[str, list[str]] = defaultdict(list)
            for m in matches:
                eid = evidence(f"boundary:{kind}:{m.start()}", m)
                evidence_ids.append(eid)
                _, fnid = enclosing_function(m.start())
                if fnid:
                    function_evidence[fnid].append(eid)
            lines = sorted({line_for(m.start()) for m in matches})
            tokens = sorted({m.group(0) for m in matches}, key=lambda token: (token.lower(), token))
            out.nodes.append(Node(
                nid, "nest_boundary", kind, record.id, record.path, "PARTIAL",
                {"boundary_type": kind, "occurrence_count": len(matches), "tokens": tokens,
                 "lines": lines, "aggregation": "translation_unit_capability"}, evidence_ids,
            ))
            out.edges.append(Edge(
                stable_id("edge", file_node, nid, "touches_nest"), file_node, nid,
                "touches_nest", "PARTIAL", {"occurrence_count": len(matches)}, evidence_ids,
            ))
            for fnid, fn_evidence_ids in function_evidence.items():
                out.edges.append(Edge(
                    stable_id("edge", fnid, nid, "crosses_boundary"), fnid, nid,
                    "crosses_boundary", "PARTIAL", {"occurrence_count": len(fn_evidence_ids)},
                    fn_evidence_ids,
                ))

        for ekind, pattern in EXTENSION_PATTERNS:
            matches = list(re.finditer(pattern, masked_text, re.IGNORECASE))
            if not matches:
                continue
            nid = stable_id("node", record.id, "extension", ekind)
            evidence_ids = []
            function_evidence: dict[str, list[str]] = defaultdict(list)
            for m in matches:
                eid = evidence(f"extension:{ekind}:{m.start()}", m)
                evidence_ids.append(eid)
                _, fnid = enclosing_function(m.start())
                if fnid:
                    function_evidence[fnid].append(eid)
            lines = sorted({line_for(m.start()) for m in matches})
            tokens = sorted({m.group(0) for m in matches}, key=lambda token: (token.lower(), token))
            out.nodes.append(Node(
                nid, "extension_receptor_candidate", ekind, record.id, record.path, "PARTIAL",
                {"occurrence_count": len(matches), "tokens": tokens, "lines": lines,
                 "aggregation": "translation_unit_capability"}, evidence_ids,
            ))
            for fnid, fn_evidence_ids in function_evidence.items():
                out.edges.append(Edge(
                    stable_id("edge", fnid, nid, "reaches_extension"), fnid, nid,
                    "reaches_extension", "PARTIAL", {"occurrence_count": len(fn_evidence_ids)},
                    fn_evidence_ids,
                ))

        return out


class _SpanMatch:
    """Tiny Match-like adapter for evidence line accounting from nested regex blocks."""
    def __init__(self, start: int, end: int, raw: str):
        self._start = start
        self._end = end
        self._raw = raw

    def start(self):
        return self._start

    def end(self):
        return self._end


class _NamedSpanMatch(_SpanMatch):
    """Match-like adapter with one capture group for brace-aware function regions."""
    def __init__(self, start: int, end: int, raw: str, name: str):
        super().__init__(start, end, raw)
        self._name = name

    def group(self, index: int = 0):
        if index == 0:
            return self._raw
        if index == 1:
            return self._name
        raise IndexError(index)
