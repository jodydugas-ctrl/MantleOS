from __future__ import annotations

from pathlib import Path
import bisect
import re

from .base import Adapter
from ..cpp_structure import find_function_regions, mask_cpp
from ..inventory import FileRecord
from ..model import Edge, Evidence, ExtractionResult, Node, stable_id


CONTROL_HEAD_RE = re.compile(r"\b(if|switch|while|for|catch)\s*\(")
EXIT_RE = re.compile(r"\b(return|throw)\b([^;{}]*);", re.MULTILINE)
TRY_RE = re.compile(r"\btry\s*\{")
RETRY_TOKEN_RE = re.compile(r"\b(?:retry\w*|retries|attempt\w*|backoff\w*|reconnect\w*)\b", re.IGNORECASE)
PERMISSION_GUARD_RE = re.compile(
    r"\b(?:isReadable|isWritable|isExecutable|permissions|exists|isOpen|status|error|canRead|canWrite|hasPermission)\b"
)
CANCEL_GUARD_RE = re.compile(r"\b(?:cancel\w*|abort\w*|rejected|dismissed)\b", re.IGNORECASE)

# High-confidence source-level receptors. These do not require executing the specimen and are narrow
# enough to preserve as direct receptor evidence even when compiler type information is unavailable.
EXTENSION_RECEPTOR_PATTERNS = [
    ("qt_plugin", re.compile(r"\bQPluginLoader\s*::\s*(load|unload|instance|setFileName)\s*\(")),
    ("dynamic_library", re.compile(r"\bQLibrary\s*::\s*(load|unload|resolve)\s*\(")),
    ("lua", re.compile(r"\b(luaL_(?:loadfilex?|loadstring|dofile)|lua_pcallk?|lua_callk?)\s*\(")),
    ("javascript", re.compile(r"\bQJSEngine\s*::\s*(evaluate)\s*\(")),
]

PERSISTENCE_PROVIDER_RE = re.compile(r"\b(QSettings|QSaveFile|QLockFile)\b")


class M3CCppAdapter(Adapter):
    """M3C control-flow / persistence / extension receptor extraction.

    This adapter deliberately does not try to become a compiler. It records mechanically visible guard,
    exception, exit, retry-candidate, persistence-provider and extension-receptor structures that remain
    valuable when compiler context is incomplete. Compiler-proven type effects are synthesized later by
    the cross-file resolution pass.
    """

    name = "m3c_cpp"
    version = "1"

    def accepts(self, record: FileRecord) -> bool:
        return record.language in {"C", "C++", "C++ Header", "C/C++ Header"} and not record.is_binary

    @staticmethod
    def _match_pair(masked: str, open_pos: int, opener: str, closer: str) -> int | None:
        depth = 0
        for i in range(open_pos, len(masked)):
            c = masked[i]
            if c == opener:
                depth += 1
            elif c == closer:
                depth -= 1
                if depth == 0:
                    return i
        return None

    @staticmethod
    def _statement_range(masked: str, start: int, limit: int) -> tuple[int, int] | None:
        i = start
        while i < limit and masked[i].isspace():
            i += 1
        if i >= limit:
            return None
        if masked[i] == "{":
            end = M3CCppAdapter._match_pair(masked, i, "{", "}")
            return (i, (end + 1) if end is not None else limit)
        semi = masked.find(";", i, limit)
        if semi >= 0:
            return (i, semi + 1)
        nl = masked.find("\n", i, limit)
        return (i, nl if nl >= 0 else limit)

    def extract(self, root: Path, record: FileRecord, text: str) -> ExtractionResult:
        out = ExtractionResult()
        masked = mask_cpp(text)
        line_starts = [0]
        for m in re.finditer("\n", text):
            line_starts.append(m.end())

        def line_for(pos: int) -> int:
            return bisect.bisect_right(line_starts, pos)

        def ev(tag: str, start: int, end: int) -> str:
            line = line_for(start)
            excerpt = text[start:end].strip().replace("\n", " ")[:500]
            eid = stable_id("evidence", record.id, self.name, tag, line, excerpt)
            out.evidence.append(Evidence(eid, record.id, record.path, line, line, "DIRECT", self.name, excerpt))
            return eid

        regions = find_function_regions(text)
        file_node = stable_id("node", record.id, "translation_unit")

        for region in regions:
            function_id = stable_id("node", record.id, "function", region.name, region.start_line)
            body_start = region.body_start
            body_end = max(region.body_start, region.end - 1)
            body_mask = masked[body_start:body_end]

            # Generic control-flow heads. Conditions are preserved as evidence; SCAN does not infer that
            # every if-statement is an error guard.
            for m in CONTROL_HEAD_RE.finditer(body_mask):
                kind = m.group(1)
                abs_start = body_start + m.start()
                open_paren = masked.find("(", abs_start, body_end)
                if open_paren < 0:
                    continue
                close_paren = self._match_pair(masked, open_paren, "(", ")")
                if close_paren is None or close_paren >= body_end:
                    continue
                stmt_range = self._statement_range(masked, close_paren + 1, body_end)
                stmt_start, stmt_end = stmt_range if stmt_range else (close_paren + 1, close_paren + 1)
                condition = text[open_paren + 1:close_paren].strip()
                eid = ev(f"control:{region.name}:{kind}:{abs_start}", abs_start, close_paren + 1)

                if kind in {"if", "switch"}:
                    node_kind = "guard"
                    label = f"{kind} guard"
                    coverage = "MAPPED"
                elif kind == "catch":
                    node_kind = "error_path"
                    label = "exception catch"
                    coverage = "MAPPED"
                else:
                    node_kind = "control_loop"
                    label = f"{kind} loop"
                    coverage = "MAPPED"

                attrs = {
                    "control_type": kind,
                    "condition": condition or None,
                    "line": line_for(abs_start),
                    "function": region.name,
                    "body_start": stmt_start,
                    "body_end": stmt_end,
                    "parser": "source_control_flow",
                }
                if PERMISSION_GUARD_RE.search(condition):
                    attrs["guard_domain_candidate"] = "permissions_or_availability"
                if CANCEL_GUARD_RE.search(condition):
                    attrs["guard_domain_candidate"] = "cancel_or_abort"

                nid = stable_id("node", record.id, node_kind, region.name, kind, line_for(abs_start), condition)
                out.nodes.append(Node(nid, node_kind, label, record.id, record.path, coverage, attrs, [eid]))
                edge_kind = "contains_guard" if node_kind == "guard" else "contains_error_path" if node_kind == "error_path" else "contains_loop"
                out.edges.append(Edge(stable_id("edge", function_id, nid, edge_kind), function_id, nid, edge_kind, "MAPPED", {}, [eid]))

                # A loop whose own identifiers explicitly indicate retry/attempt/backoff semantics is a
                # retry candidate, not a proved retry policy. The source loop remains independently mapped.
                if node_kind == "control_loop":
                    loop_excerpt = text[abs_start:min(stmt_end, body_end)]
                    if RETRY_TOKEN_RE.search(condition + " " + loop_excerpt):
                        rid = stable_id("node", record.id, "retry_candidate", region.name, line_for(abs_start))
                        out.nodes.append(Node(
                            rid, "retry_path_candidate", "retry/backoff loop candidate", record.id, record.path, "PARTIAL",
                            {"line": line_for(abs_start), "function": region.name, "mechanism": kind,
                             "basis": "retry/attempt/backoff identifier in loop syntax"}, [eid],
                        ))
                        out.edges.append(Edge(stable_id("edge", nid, rid, "may_retry_via"), nid, rid, "may_retry_via", "PARTIAL", {}, [eid]))

                # Link direct return/throw exits within the guarded/body range. This is structural
                # containment, not a claim that every early return represents an error.
                if stmt_end > stmt_start:
                    segment = masked[stmt_start:stmt_end]
                    for xm in EXIT_RE.finditer(segment):
                        exit_kind = xm.group(1)
                        xs = stmt_start + xm.start()
                        xe = stmt_start + xm.end()
                        xev = ev(f"guarded-exit:{region.name}:{exit_kind}:{xs}", xs, xe)
                        expr = text[xs:xe].strip()
                        xid = stable_id("node", record.id, "control_exit", region.name, exit_kind, line_for(xs), expr)
                        semantics = "exception" if exit_kind == "throw" else "early_return"
                        out.nodes.append(Node(
                            xid, "control_exit", semantics, record.id, record.path, "MAPPED",
                            {"exit_type": exit_kind, "line": line_for(xs), "function": region.name,
                             "expression": expr, "guarded": True}, [xev],
                        ))
                        out.edges.append(Edge(stable_id("edge", nid, xid, "guards_exit"), nid, xid, "guards_exit", "MAPPED", {}, sorted({eid, xev})))
                        out.edges.append(Edge(stable_id("edge", function_id, xid, "contains_exit"), function_id, xid, "contains_exit", "MAPPED", {}, [xev]))
                        if exit_kind == "throw":
                            err = stable_id("node", record.id, "error_throw", region.name, line_for(xs), expr)
                            out.nodes.append(Node(err, "error_path", "exception throw", record.id, record.path, "MAPPED",
                                                  {"error_type": "throw", "line": line_for(xs), "function": region.name}, [xev]))
                            out.edges.append(Edge(stable_id("edge", xid, err, "exits_via_error"), xid, err, "exits_via_error", "MAPPED", {}, [xev]))

            # Throws not already necessarily inside a recognized condition remain explicit exception paths.
            for tm in re.finditer(r"\bthrow\b([^;{}]*);", body_mask):
                ts = body_start + tm.start(); te = body_start + tm.end()
                eid = ev(f"throw:{region.name}:{ts}", ts, te)
                nid = stable_id("node", record.id, "error_throw", region.name, line_for(ts), text[ts:te].strip())
                out.nodes.append(Node(nid, "error_path", "exception throw", record.id, record.path, "MAPPED",
                                      {"error_type": "throw", "line": line_for(ts), "function": region.name}, [eid]))
                out.edges.append(Edge(stable_id("edge", function_id, nid, "contains_error_path"), function_id, nid,
                                      "contains_error_path", "MAPPED", {}, [eid]))

            # Presence of an explicit try block is useful error-path anatomy even before catch semantics
            # are fully resolved.
            for tm in TRY_RE.finditer(body_mask):
                ts = body_start + tm.start()
                eid = ev(f"try:{region.name}:{ts}", ts, min(body_end, ts + 32))
                nid = stable_id("node", record.id, "try_block", region.name, line_for(ts))
                out.nodes.append(Node(nid, "error_path", "try block", record.id, record.path, "MAPPED",
                                      {"error_type": "try", "line": line_for(ts), "function": region.name}, [eid]))
                out.edges.append(Edge(stable_id("edge", function_id, nid, "contains_error_path"), function_id, nid,
                                      "contains_error_path", "MAPPED", {}, [eid]))

            # Narrow source-level extension/script/plugin receptors.
            region_text = text[region.body_start:body_end]
            for receptor_type, rx in EXTENSION_RECEPTOR_PATTERNS:
                for rm in rx.finditer(region_text):
                    rs = region.body_start + rm.start(); re_ = region.body_start + rm.end()
                    action = rm.group(1) if rm.lastindex else rm.group(0)
                    eid = ev(f"extension-receptor:{region.name}:{receptor_type}:{action}:{rs}", rs, re_)
                    rid = stable_id("node", record.id, "extension_receptor", region.name, receptor_type, action, line_for(rs))
                    out.nodes.append(Node(
                        rid, "extension_receptor", f"{receptor_type}:{action}", record.id, record.path, "MAPPED",
                        {"receptor_type": receptor_type, "action": action, "line": line_for(rs),
                         "function": region.name, "classification": "known_extension_api"}, [eid],
                    ))
                    out.edges.append(Edge(stable_id("edge", function_id, rid, "reaches_extension"), function_id, rid,
                                          "reaches_extension", "MAPPED", {}, [eid]))
                    if str(action) in {"instance", "resolve", "evaluate", "loadfile", "loadfilex", "loadstring", "dofile"} or str(action).startswith("luaL_load"):
                        fid = stable_id("node", rid, "capability_factory")
                        out.nodes.append(Node(
                            fid, "capability_factory", f"capability from {receptor_type}", record.id, record.path, "PARTIAL",
                            {"factory_type": receptor_type, "source_receptor_id": rid,
                             "meaning": "loaded/evaluated external material may introduce behavior; exact capabilities depend on runtime payload"}, [eid],
                        ))
                        out.edges.append(Edge(stable_id("edge", rid, fid, "creates_capability"), rid, fid,
                                              "creates_capability", "PARTIAL", {}, [eid]))

            # Persistence provider usage is a provider/receptor fact, not proof that a specific state is
            # durable. Typed write/sync/commit calls are promoted to persistence operations later.
            for pm in PERSISTENCE_PROVIDER_RE.finditer(region_text):
                ps = region.body_start + pm.start(); pe = region.body_start + pm.end()
                provider = pm.group(1)
                eid = ev(f"persistence-provider:{region.name}:{provider}:{ps}", ps, pe)
                pid = stable_id("node", record.id, "persistence_provider", region.name, provider, line_for(ps))
                out.nodes.append(Node(
                    pid, "persistence_provider", provider, record.id, record.path, "PARTIAL",
                    {"provider": provider, "line": line_for(ps), "function": region.name,
                     "meaning": "persistence-capable provider referenced; durable operation requires call/effect evidence"}, [eid],
                ))
                out.edges.append(Edge(stable_id("edge", function_id, pid, "uses_persistence_provider"), function_id, pid,
                                      "uses_persistence_provider", "PARTIAL", {}, [eid]))

        # File-level receptors outside functions are still important (e.g., plugin metadata/static init).
        # Existing cpp_qt/cmake adapters account for many such cases, so M3C does not duplicate them here.
        _ = file_node
        return out
