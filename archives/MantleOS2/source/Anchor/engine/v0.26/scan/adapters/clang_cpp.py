from __future__ import annotations

import json
import re
import shlex
import shutil
import subprocess
import threading
from contextlib import suppress
from hashlib import sha256
from pathlib import Path
from typing import Any

from ..cpp_structure import find_class_regions, find_function_regions, mask_cpp
from ..inventory import FileRecord
from ..model import Edge, Evidence, ExtractionResult, Finding, Node, stable_id
from .base import Adapter


SOURCE_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".c++", ".m", ".mm"}
DECL_KINDS = {"FunctionDecl", "CXXMethodDecl", "CXXConstructorDecl", "CXXDestructorDecl", "CXXConversionDecl"}
CALL_KINDS = {"CallExpr", "CXXMemberCallExpr", "CXXOperatorCallExpr"}
RECORD_KINDS = {"CXXRecordDecl", "RecordDecl"}


class ClangCppAdapter(Adapter):
    """Compiler-assisted C/C++ structural adapter.

    SCAN invokes a fixed local clang binary directly. `compile_commands.json` is treated only as data:
    scanner code extracts a narrow, non-executing parse-context whitelist and never replays specimen
    compiler commands, response files, plugins, generated commands, or linker steps.

    v0.8+ adds context-sensitive cache keys, bounded compile-database discovery, type/inheritance evidence,
    overload-safe declaration identity, template-specialization provenance, and explicit virtual-dispatch
    candidates. A failed compiler parse remains a visible parser gap and conservative fallback extraction
    is expected to continue.
    """

    name = "clang_cpp"

    def __init__(self, clang: str | None = None, *, timeout_seconds: float = 5.0,
                 max_source_bytes: int = 2_000_000, max_ast_json_bytes: int = 64_000_000,
                 compile_db_search_depth: int = 4):
        self.clang = clang or shutil.which("clang++") or shutil.which("clang")
        self.timeout_seconds = timeout_seconds
        self.filtered_timeout_seconds = timeout_seconds * 4
        self.max_source_bytes = max_source_bytes
        self.max_ast_json_bytes = max_ast_json_bytes
        self.compile_db_search_depth = compile_db_search_depth
        self.tool_version = self._tool_version()
        self.version = f"8-{self.tool_version}"
        self._db_cache: dict[str, list[tuple[Path, Any]]] = {}

    def _tool_version(self) -> str:
        if not self.clang:
            return "unavailable"
        try:
            p = subprocess.run([self.clang, "--version"], capture_output=True, text=True, timeout=3, check=False)
            first = (p.stdout or p.stderr or "unknown").splitlines()[0].strip()
            token = "-".join(first.split()[:3]).replace("/", "_")
            return token[:64] or "unknown"
        except Exception:
            return "unknown"

    def _run_clang_bounded(self, cmd: list[str]) -> dict[str, Any]:
        """Run Clang without allowing compiler output to grow process memory without bound.

        Both pipes are drained concurrently.  The process is stopped as soon as stdout crosses
        the configured JSON parse ceiling; callers may then attempt a narrower declaration dump.
        Stderr is retained only up to a fixed diagnostic ceiling while still being fully drained.
        """
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert proc.stdout is not None
        assert proc.stderr is not None
        stdout_parts: list[bytes] = []
        stderr_parts: list[bytes] = []
        state = {"stdout_bytes": 0, "stderr_bytes": 0, "stdout_truncated": False,
                 "stderr_truncated": False}
        stderr_limit = 1_000_000

        def drain(stream, parts: list[bytes], *, key: str, limit: int, kill_on_limit: bool) -> None:
            while True:
                chunk = stream.read(65_536)
                if not chunk:
                    break
                state[key] += len(chunk)
                stored = sum(len(part) for part in parts)
                if stored < limit:
                    parts.append(chunk[:limit - stored])
                if state[key] > limit:
                    state[key.replace("_bytes", "_truncated")] = True
                    if kill_on_limit and proc.poll() is None:
                        with suppress(OSError):
                            proc.kill()
            stream.close()

        stdout_thread = threading.Thread(
            target=drain,
            args=(proc.stdout, stdout_parts),
            kwargs={"key": "stdout_bytes", "limit": self.max_ast_json_bytes,
                    "kill_on_limit": True},
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=drain,
            args=(proc.stderr, stderr_parts),
            kwargs={"key": "stderr_bytes", "limit": stderr_limit, "kill_on_limit": False},
            daemon=True,
        )
        stdout_thread.start()
        stderr_thread.start()
        timed_out = False
        command_timeout = (
            self.filtered_timeout_seconds
            if any(str(argument).startswith("-ast-dump-filter=") for argument in cmd)
            else self.timeout_seconds
        )
        try:
            proc.wait(timeout=command_timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            proc.kill()
            proc.wait()
        stdout_thread.join()
        stderr_thread.join()
        return {
            "returncode": proc.returncode,
            "stdout": b"".join(stdout_parts).decode("utf-8", errors="replace"),
            "stderr": b"".join(stderr_parts).decode("utf-8", errors="replace"),
            "stdout_bytes": state["stdout_bytes"],
            "stderr_bytes": state["stderr_bytes"],
            "stdout_truncated": state["stdout_truncated"],
            "stderr_truncated": state["stderr_truncated"],
            "timed_out": timed_out,
        }

    @staticmethod
    def _filtered_dump_term(source: Path, text: str) -> str | None:
        """Choose one deterministic source-derived declaration substring for AST recovery."""
        masked = mask_cpp(text)
        stem = source.stem
        if re.search(rf"\b{re.escape(stem)}\b", masked):
            return stem

        candidates: list[str] = []
        candidates.extend(region.name for region in find_class_regions(text, masked_text=masked))
        for region in find_function_regions(text, masked_text=masked):
            candidates.append(region.class_scope or region.name.rsplit("::", 1)[-1])
        valid = sorted({candidate.rsplit("::", 1)[-1] for candidate in candidates
                        if re.fullmatch(r"[A-Za-z_]\w*", candidate.rsplit("::", 1)[-1])})
        if not valid:
            return None
        return min(valid, key=lambda candidate: (-len(re.findall(rf"\b{re.escape(candidate)}\b", masked)),
                                                  -len(candidate), candidate))

    @staticmethod
    def _parse_ast_documents(payload: str) -> dict[str, Any]:
        """Parse either one normal Clang JSON AST or filtered concatenated JSON declarations."""
        decoder = json.JSONDecoder()
        documents: list[dict[str, Any]] = []
        index = 0
        while True:
            while index < len(payload) and payload[index].isspace():
                index += 1
            if index >= len(payload):
                break
            document, index = decoder.raw_decode(payload, index)
            if not isinstance(document, dict):
                raise json.JSONDecodeError("Clang AST document is not an object", payload, index)
            documents.append(document)
        if not documents:
            raise json.JSONDecodeError("Clang AST output contains no JSON documents", payload, 0)
        if len(documents) == 1:
            return documents[0]
        return {"kind": "TranslationUnitDecl", "inner": documents}

    def accepts(self, record: FileRecord) -> bool:
        return record.language in {"C", "C++"} and Path(record.path).suffix.lower() in SOURCE_SUFFIXES and not record.is_binary

    def _compile_db_documents(self, root: Path) -> list[tuple[Path, Any]]:
        key = str(root.resolve())
        cached = self._db_cache.get(key)
        if cached is not None:
            return cached

        candidates: list[Path] = []
        direct = root / "compile_commands.json"
        if direct.exists():
            candidates.append(direct)

        # Bounded breadth-first discovery catches common build/, cmake-build-*/, out/build/* layouts
        # without making repository size an unbounded recursive filesystem problem.
        queue: list[tuple[Path, int]] = [(root, 0)]
        seen = {root.resolve()}
        skip = {".git", ".scan", "node_modules", "__pycache__", ".pytest_cache"}
        while queue and len(candidates) < 32:
            directory, depth = queue.pop(0)
            if depth >= self.compile_db_search_depth:
                continue
            try:
                children = sorted((p for p in directory.iterdir() if p.is_dir() and p.name not in skip), key=lambda p: p.name)
            except OSError:
                continue
            for child in children[:128]:
                try:
                    resolved = child.resolve()
                except OSError:
                    continue
                if resolved in seen:
                    continue
                seen.add(resolved)
                db = child / "compile_commands.json"
                if db.exists() and db not in candidates:
                    candidates.append(db)
                queue.append((child, depth + 1))

        docs: list[tuple[Path, Any]] = []
        for db in candidates:
            try:
                payload = json.loads(db.read_text(encoding="utf-8", errors="replace"))
                docs.append((db, payload))
            except Exception:
                # Invalid compile DB is handled as absent context rather than executable input.
                continue
        self._db_cache[key] = docs
        return docs

    def _compile_db_context(self, root: Path, record: FileRecord) -> dict[str, Any]:
        target = (root / record.path).resolve()
        for db, payload in self._compile_db_documents(root):
            for entry in payload if isinstance(payload, list) else []:
                file_value = entry.get("file")
                if not isinstance(file_value, str):
                    continue
                directory = Path(entry.get("directory") or db.parent)
                candidate = Path(file_value)
                if not candidate.is_absolute():
                    candidate = directory / candidate
                try:
                    if candidate.resolve() != target:
                        continue
                except OSError:
                    continue
                args = entry.get("arguments")
                if not isinstance(args, list):
                    command = entry.get("command")
                    if not isinstance(command, str):
                        args = []
                    else:
                        try:
                            args = shlex.split(command)
                        except ValueError:
                            args = []
                flags = self._safe_flags([str(a) for a in args], directory)
                digest = sha256(json.dumps({
                    "db": str(db.resolve()), "directory": str(directory.resolve()), "flags": flags
                }, sort_keys=True).encode()).hexdigest()[:20]
                return {
                    "flags": flags,
                    "compile_db": db.relative_to(root).as_posix() if db.is_relative_to(root) else str(db),
                    "directory": str(directory),
                    "context_digest": digest,
                }
        return {"flags": [], "compile_db": None, "directory": None, "context_digest": "no-compile-db-context"}

    def cache_version(self, root: Path, record: FileRecord) -> str:
        context = self._compile_db_context(root, record)
        return f"{self.version}-ctx-{context['context_digest']}"

    @staticmethod
    def _safe_flags(args: list[str], directory: Path) -> list[str]:
        """Extract read-only parser context from compile-database data.

        The scanner never trusts the command executable or output/plugin/dependency flags. Include paths,
        preprocessor defines, language standard/mode and sysroot/framework search paths may affect parsing,
        so those are copied as data and relative paths are anchored to the recorded compile directory.
        """
        out: list[str] = []
        i = 0
        two_part_paths = {"-I", "-isystem", "-iquote", "-idirafter", "-isysroot", "-F", "-iframework"}
        two_part_value = {"-D", "-U", "-x", "-target"}
        forbidden_exact = {"-o", "-MF", "-MT", "-MQ", "-include", "-imacros", "-Xclang", "-load", "-c"}
        forbidden_prefixes = ("-fplugin", "@", "-Wl,", "-Wa,", "-Wp,")

        while i < len(args):
            arg = args[i]
            if arg in forbidden_exact:
                # Flags in this set consume one value except -c; skip both conservatively.
                i += 1 if arg == "-c" else 2
                continue
            if any(arg.startswith(x) for x in forbidden_prefixes):
                i += 1
                continue
            if arg in two_part_paths and i + 1 < len(args):
                val = args[i + 1]
                p = Path(val)
                if not p.is_absolute():
                    val = str((directory / p).resolve())
                out.extend([arg, val])
                i += 2
                continue
            if arg in two_part_value and i + 1 < len(args):
                out.extend([arg, args[i + 1]])
                i += 2
                continue
            if arg.startswith("-I") and len(arg) > 2:
                p = Path(arg[2:])
                out.append("-I" + str((directory / p).resolve() if not p.is_absolute() else p))
            elif arg.startswith(("-D", "-U", "-std=", "--sysroot=")):
                out.append(arg)
            # Everything else, including compiler executable/source/output/linker args, is ignored.
            i += 1
        return out

    @staticmethod
    def _walk(node: dict[str, Any]):
        yield node
        for child in node.get("inner") or []:
            if isinstance(child, dict):
                yield from ClangCppAdapter._walk(child)

    @staticmethod
    def _has_body(node: dict[str, Any]) -> bool:
        return any(isinstance(c, dict) and c.get("kind") == "CompoundStmt" for c in node.get("inner") or [])

    @staticmethod
    def _line(node: dict[str, Any]) -> int | None:
        loc = node.get("loc") or {}
        if isinstance(loc.get("line"), int):
            return loc["line"]
        begin = (node.get("range") or {}).get("begin") or {}
        return begin.get("line") if isinstance(begin.get("line"), int) else None

    @staticmethod
    def _offset(node: dict[str, Any]) -> int | None:
        loc = node.get("loc") or {}
        if isinstance(loc.get("offset"), int):
            return loc["offset"]
        begin = (node.get("range") or {}).get("begin") or {}
        return begin.get("offset") if isinstance(begin.get("offset"), int) else None

    @staticmethod
    def _referenced_decl_id(node: dict[str, Any]) -> str | None:
        for x in ClangCppAdapter._walk(node):
            rid = x.get("referencedMemberDecl")
            if isinstance(rid, str):
                return rid
            ref = x.get("referencedDecl")
            if isinstance(ref, dict) and isinstance(ref.get("id"), str):
                return ref["id"]
        return None

    @staticmethod
    def _found_template_decl_id(node: dict[str, Any]) -> str | None:
        for x in ClangCppAdapter._walk(node):
            ref = x.get("foundReferencedDecl")
            if isinstance(ref, dict) and ref.get("kind") == "FunctionTemplateDecl" and isinstance(ref.get("id"), str):
                return ref["id"]
        return None

    @staticmethod
    def _receiver_static_type(node: dict[str, Any]) -> str | None:
        member = next((x for x in ClangCppAdapter._walk(node) if x.get("kind") == "MemberExpr"), None)
        if not member:
            return None
        for child in member.get("inner") or []:
            typ = (child.get("type") or {}).get("qualType") if isinstance(child, dict) else None
            if isinstance(typ, str):
                return typ
        return None

    def extract(self, root: Path, record: FileRecord, text: str) -> ExtractionResult:
        out = ExtractionResult()
        if not self.clang:
            out.findings.append(Finding(
                stable_id("finding", record.id, self.name, "clang-unavailable"), "parser_gap",
                f"Compiler AST unavailable for {record.path}", "PARTIAL",
                {"parser": "clang", "reason": "clang executable not found", "fallback_expected": "cpp_qt"}, [],
            ))
            return out
        if record.size > self.max_source_bytes:
            out.findings.append(Finding(
                stable_id("finding", record.id, self.name, "source-too-large", record.size), "parser_gap",
                f"Compiler AST skipped for large source {record.path}", "PARTIAL",
                {"parser": "clang", "size": record.size, "limit": self.max_source_bytes, "fallback_expected": "cpp_qt"}, [],
            ))
            return out

        source = (root / record.path).resolve()

        def is_main_source_node(node: dict[str, Any]) -> bool:
            """Return True only for AST nodes whose expansion/location belongs to this translation unit.

            Clang's JSON AST contains declarations and instantiated templates from system/project headers.
            Those objects remain available internally for referenced-declaration/type lookup, but emitting them
            as if they lived in `record.path` creates false source provenance and enormous stdlib noise.
            Main-file macro expansions are accepted via expansionLoc; header-origin nodes are not emitted.
            """
            loc = node.get("loc") or (node.get("range") or {}).get("begin") or {}
            if isinstance(loc, dict) and isinstance(loc.get("expansionLoc"), dict):
                loc = loc["expansionLoc"]
            if not isinstance(loc, dict):
                return False
            if isinstance(loc.get("includedFrom"), dict):
                return False
            file_value = loc.get("file")
            if isinstance(file_value, str) and file_value:
                try:
                    candidate = Path(file_value)
                    if not candidate.is_absolute():
                        candidate = source.parent / candidate
                    return candidate.resolve() == source
                except OSError:
                    return False
            offset = loc.get("offset")
            return isinstance(offset, int) and 0 <= offset <= len(text)

        context = self._compile_db_context(root, record)
        flags = list(context["flags"])
        if not any(a.startswith("-std=") for a in flags) and record.language == "C++":
            flags.append("-std=c++17")
        cmd = [self.clang, *flags, "-fsyntax-only", "-fno-color-diagnostics", "-Wno-everything",
               "-Xclang", "-ast-dump=json", str(source)]
        try:
            compiler_run = self._run_clang_bounded(cmd)
        except OSError as exc:
            out.findings.append(Finding(
                stable_id("finding", record.id, self.name, "os-error", str(exc)), "parser_gap",
                f"Compiler AST failed to start for {record.path}", "BLOCKED",
                {"parser": "clang", "error": str(exc), "compile_context": context}, [],
            ))
            return out
        filtered_recovery = False
        ast_dump_filter: str | None = None
        bounded_recovery_needed = compiler_run["timed_out"] or compiler_run["stdout_truncated"]
        if bounded_recovery_needed:
            # Whether the full-output attempt reaches the time ceiling or the byte ceiling first is
            # scheduler-dependent. Canonical evidence records the configured bounds and the filtered
            # recovery outcome, not that race or the variable amount drained after process termination.
            ast_dump_filter = self._filtered_dump_term(source, text)
            if ast_dump_filter:
                filtered_cmd = [*cmd[:-1], "-Xclang", f"-ast-dump-filter={ast_dump_filter}", cmd[-1]]
                try:
                    compiler_run = self._run_clang_bounded(filtered_cmd)
                except OSError as exc:
                    compiler_run = {"timed_out": False, "stdout_truncated": False, "stdout_bytes": 0,
                                    "stdout": "", "stderr": str(exc), "returncode": None,
                                    "stderr_truncated": False}
                filtered_recovery = not compiler_run["timed_out"] and not compiler_run["stdout_truncated"]

            if not filtered_recovery:
                reason = "no source-derived declaration filter was available"
                if ast_dump_filter and compiler_run["timed_out"]:
                    reason = "the filtered recovery timed out"
                elif ast_dump_filter and compiler_run["stdout_truncated"]:
                    reason = "the filtered recovery also exceeded the safe parse limit"
                out.findings.append(Finding(
                    stable_id("finding", record.id, self.name, "bounded-recovery-failed",
                              self.max_ast_json_bytes, context["context_digest"], ast_dump_filter),
                    "parser_gap",
                    f"Compiler AST exceeded its bounded full-output envelope for {record.path}; {reason}",
                    "PARTIAL",
                    {"parser": "clang", "max_ast_json_bytes": self.max_ast_json_bytes,
                     "timeout_seconds": self.timeout_seconds, "ast_dump_filter": ast_dump_filter,
                     "filtered_timeout_seconds": self.filtered_timeout_seconds if ast_dump_filter else None,
                     "bounded_recovery_attempted": bool(ast_dump_filter),
                     "safe_compile_db_flags": flags,
                     "compile_context": context, "fallback_expected": "cpp_qt"}, [],
                ))
                return out

        diagnostics = (compiler_run["stderr"] or "").strip().splitlines()
        ast_json_bytes = compiler_run["stdout_bytes"]
        try:
            ast = self._parse_ast_documents(compiler_run["stdout"])
        except json.JSONDecodeError as exc:
            # Clang commonly returns nonzero for an unavailable dependency while still emitting a
            # structurally valid JSON AST for the source-local declarations it could recover.  Only
            # discard the compiler result when there is no valid AST to authenticate; otherwise the
            # recoverable branch below retains it with an explicit PARTIAL parser result and gap.
            state = "PARTIAL" if compiler_run["returncode"] != 0 or filtered_recovery else "BLOCKED"
            out.findings.append(Finding(
                stable_id("finding", record.id, self.name, "invalid-json"), "parser_gap",
                f"Compiler AST emitted invalid JSON for {record.path}", state,
                {"parser": "clang", "returncode": compiler_run["returncode"], "error": str(exc),
                 "diagnostics": diagnostics[:8], "safe_compile_db_flags": flags,
                 "compile_context": context,
                 "filtered_after_bounded_attempt": filtered_recovery,
                 "ast_dump_filter": ast_dump_filter, "fallback_expected": "cpp_qt"}, [],
            ))
            return out

        parse_coverage = "PARTIAL" if compiler_run["returncode"] != 0 or filtered_recovery else "MAPPED"
        if compiler_run["returncode"] != 0 or filtered_recovery:
            finding_kind = "filtered-recovery" if filtered_recovery else "parse-failed"
            out.findings.append(Finding(
                stable_id("finding", record.id, self.name, finding_kind, compiler_run["returncode"],
                          context["context_digest"], ast_dump_filter), "parser_gap",
                (f"Compiler AST recovered through bounded declaration filtering for {record.path}"
                 if filtered_recovery else f"Compiler AST parse incomplete for {record.path}"), "PARTIAL",
                {"parser": "clang", "returncode": compiler_run["returncode"],
                 "diagnostics": diagnostics[:8],
                 "safe_compile_db_flags": flags, "compile_context": context,
                 "recovered_valid_ast": True,
                 "filtered_after_bounded_attempt": filtered_recovery,
                 "ast_dump_filter": ast_dump_filter,
                 "filtered_timeout_seconds": self.filtered_timeout_seconds if filtered_recovery else None,
                 "unfiltered_ast_json_limit": self.max_ast_json_bytes,
                 "fallback_expected": "cpp_qt"}, [],
            ))

        parse_node = stable_id("node", record.id, "compiler_parse", self.tool_version, context["context_digest"])
        out.nodes.append(Node(
            parse_node, "parser_result", "clang_ast", record.id, record.path, parse_coverage,
            {"parser": "clang_ast", "tool_version": self.tool_version, "safe_compile_db_flags": flags,
             "compile_context": context, "returncode": compiler_run["returncode"],
             "recovered_after_diagnostics": compiler_run["returncode"] != 0,
             "filtered_after_bounded_attempt": filtered_recovery,
             "ast_dump_filter": ast_dump_filter,
             "filtered_timeout_seconds": self.filtered_timeout_seconds if filtered_recovery else None,
             "unfiltered_ast_json_limit": self.max_ast_json_bytes if filtered_recovery else None,
             "ast_json_bytes": ast_json_bytes,
             "max_ast_json_bytes": self.max_ast_json_bytes}, [],
        ))

        nodes_by_ast_id = {n.get("id"): n for n in self._walk(ast) if isinstance(n.get("id"), str)}
        context_name: dict[str, str] = {}
        lexical_decl_name: dict[str, str] = {}
        template_name_by_id: dict[str, str] = {}
        template_parent_by_decl: dict[str, str] = {}

        def index_context(n: dict[str, Any], current: str | None = None, current_template: str | None = None):
            kind = n.get("kind")
            name = n.get("name")
            next_context = current
            next_template = current_template
            if kind in {"NamespaceDecl", "CXXRecordDecl", "RecordDecl", "ClassTemplateDecl"} and n.get("id") and name:
                candidate = str(name) if not current else f"{current}::{name}"
                if current and current.rsplit("::", 1)[-1] == str(name) and kind in {"CXXRecordDecl", "RecordDecl"}:
                    candidate = current
                context_name[n["id"]] = candidate
                next_context = candidate
            if kind == "FunctionTemplateDecl" and n.get("id") and name:
                q = str(name) if not current else f"{current}::{name}"
                template_name_by_id[n["id"]] = q
                next_template = n["id"]
            if kind in DECL_KINDS and n.get("id") and name:
                lexical_decl_name[n["id"]] = str(name) if not current else f"{current}::{name}"
                if current_template:
                    template_parent_by_decl[n["id"]] = current_template
            for child in n.get("inner") or []:
                if isinstance(child, dict):
                    index_context(child, next_context, next_template)

        index_context(ast)

        def qname(n: dict[str, Any]) -> str:
            name = str(n.get("name") or "<anonymous>")
            parent = n.get("parentDeclContextId")
            if isinstance(parent, str) and parent in context_name:
                return f"{context_name[parent]}::{name}"
            aid = n.get("id")
            if isinstance(aid, str) and aid in lexical_decl_name:
                return lexical_decl_name[aid]
            return name

        def node_line(n: dict[str, Any]) -> int | None:
            line = self._line(n)
            if line is not None:
                return line
            off = self._offset(n)
            if off is not None and 0 <= off <= len(text):
                return text.count("\n", 0, off) + 1
            return None

        def excerpt_for(node: dict[str, Any]) -> str | None:
            begin = (node.get("range") or {}).get("begin") or {}
            end = (node.get("range") or {}).get("end") or {}
            a = begin.get("offset")
            b = end.get("offset")
            tok = end.get("tokLen", 1)
            if isinstance(a, int) and isinstance(b, int) and 0 <= a <= b < len(text):
                return text[a:min(len(text), b + (tok if isinstance(tok, int) else 1))].strip().replace("\n", " ")[:500]
            return None

        def canonical_decl_id(aid: str | None) -> str | None:
            if not aid:
                return None
            seen: set[str] = set()
            current = aid
            while current in nodes_by_ast_id and current not in seen:
                seen.add(current)
                prev = nodes_by_ast_id[current].get("previousDecl")
                if not isinstance(prev, str):
                    break
                current = prev
            return current

        decl_qname: dict[str, str] = {}
        decl_signature: dict[str, str | None] = {}
        for aid, n in nodes_by_ast_id.items():
            if n.get("kind") in DECL_KINDS and n.get("name"):
                decl_qname[aid] = qname(n)
                decl_signature[aid] = (n.get("type") or {}).get("qualType")

        # Type definitions and inheritance are compiler-derived anatomical objects.
        type_def_by_name: dict[str, str] = {}
        for n in self._walk(ast):
            if n.get("kind") not in RECORD_KINDS or not n.get("completeDefinition") or not n.get("id") or not n.get("name"):
                continue
            if not is_main_source_node(n):
                continue
            line = node_line(n)
            if line is None:
                continue
            qn = context_name.get(n["id"], qname(n))
            eid = stable_id("evidence", record.id, self.name, "type", qn, line, self.tool_version)
            out.evidence.append(Evidence(eid, record.id, record.path, line, line, "DIRECT", self.name, excerpt_for(n)))
            tid = stable_id("node", record.id, "cpp_type", qn, line)
            type_def_by_name[qn] = tid
            bases = [((b.get("type") or {}).get("qualType")) for b in (n.get("bases") or []) if isinstance(b, dict)]
            polymorphic = bool((n.get("definitionData") or {}).get("isPolymorphic"))
            out.nodes.append(Node(
                tid, "type_symbol", qn, record.id, record.path, "MAPPED",
                {"qualified_name": qn, "line": line, "parser": "clang_ast",
                 "bases": [b for b in bases if b], "is_polymorphic": polymorphic}, [eid],
            ))
            for base in [b for b in bases if b]:
                ref = stable_id("node", "cpp_type_ref", base)
                out.nodes.append(Node(ref, "type_reference", base, record.id, record.path, "PARTIAL",
                                      {"qualified_name": base, "parser": "clang_ast"}, [eid]))
                out.edges.append(Edge(stable_id("edge", tid, ref, "inherits"), tid, ref, "inherits", "MAPPED",
                                      {"access": next((x.get("access") for x in (n.get("bases") or []) if ((x.get("type") or {}).get("qualType")) == base), None)}, [eid]))

        # Template declarations are explicit so specialized calls can retain their generic origin.
        for tid_ast, tname in template_name_by_id.items():
            tnode = nodes_by_ast_id.get(tid_ast, {})
            if not is_main_source_node(tnode):
                continue
            line = node_line(tnode)
            if line is None:
                continue
            eid = stable_id("evidence", record.id, self.name, "template", tname, line, self.tool_version)
            out.evidence.append(Evidence(eid, record.id, record.path, line, line, "DIRECT", self.name, excerpt_for(tnode)))
            nid = stable_id("node", record.id, "function_template", tname, line)
            out.nodes.append(Node(nid, "template_symbol", tname, record.id, record.path, "MAPPED",
                                  {"qualified_name": tname, "line": line, "parser": "clang_ast"}, [eid]))

        definition_by_decl_root: dict[str, str] = {}
        function_ast_to_scan: dict[str, str] = {}
        function_meta: dict[str, dict[str, Any]] = {}
        qname_to_definitions: dict[str, list[str]] = {}
        for n in self._walk(ast):
            if n.get("kind") not in DECL_KINDS or not n.get("id") or not n.get("name") or not self._has_body(n):
                continue
            if not is_main_source_node(n):
                continue
            qn = qname(n)
            line = node_line(n)
            if line is None:
                continue
            signature = (n.get("type") or {}).get("qualType")
            root_decl = canonical_decl_id(n["id"]) or n["id"]
            root_node = nodes_by_ast_id.get(root_decl, n)
            virtual = bool(root_node.get("virtual") or n.get("virtual"))
            is_override = any(isinstance(c, dict) and c.get("kind") == "OverrideAttr" for c in n.get("inner") or [])
            template_ast = template_parent_by_decl.get(n["id"]) or template_parent_by_decl.get(root_decl)
            template_origin = template_name_by_id.get(template_ast) if template_ast else None
            eid = stable_id("evidence", record.id, self.name, "function", qn, signature, line, self.tool_version)
            out.evidence.append(Evidence(eid, record.id, record.path, line, line, "DIRECT", self.name, excerpt_for(n)))
            sid = stable_id("node", record.id, "function", qn, line)
            function_ast_to_scan[n["id"]] = sid
            definition_by_decl_root[root_decl] = sid
            qname_to_definitions.setdefault(qn, []).append(sid)
            function_meta[sid] = {"qualified_name": qn, "signature": signature, "virtual": virtual,
                                  "override": is_override, "root_decl": root_decl}
            out.nodes.append(Node(
                sid, "symbol", qn, record.id, record.path, "MAPPED",
                {"symbol_type": "function", "qualified_name": qn, "signature": signature, "line": line,
                 "parser": "clang_ast", "clang_tool_version": self.tool_version,
                 "mangled_name": n.get("mangledName"), "virtual": virtual, "override": is_override,
                 "template_origin": template_origin, "compile_context_digest": context["context_digest"]}, [eid],
            ))
            if template_origin:
                template_nodes = [x for x in out.nodes if x.kind == "template_symbol" and x.name == template_origin]
                if template_nodes:
                    out.edges.append(Edge(stable_id("edge", sid, template_nodes[0].id, "specializes"), sid, template_nodes[0].id,
                                          "specializes", "MAPPED", {"parser": "clang_ast"}, [eid]))

        # Connect override definitions to matching base methods when the AST provides enough type evidence.
        type_bases: dict[str, list[str]] = {}
        for n in self._walk(ast):
            if (n.get("kind") in RECORD_KINDS and n.get("completeDefinition") and n.get("id") in context_name
                    and is_main_source_node(n)):
                type_bases[context_name[n["id"]]] = [((b.get("type") or {}).get("qualType")) for b in (n.get("bases") or []) if isinstance(b, dict) and (b.get("type") or {}).get("qualType")]
        for sid, meta in list(function_meta.items()):
            if not meta["override"] or "::" not in meta["qualified_name"]:
                continue
            owner, bare = meta["qualified_name"].rsplit("::", 1)
            for base in type_bases.get(owner, []):
                candidate = f"{base}::{bare}"
                for base_sid in qname_to_definitions.get(candidate, []):
                    bmeta = function_meta.get(base_sid, {})
                    if meta.get("signature") == bmeta.get("signature"):
                        out.edges.append(Edge(stable_id("edge", sid, base_sid, "overrides"), sid, base_sid, "overrides", "MAPPED",
                                              {"resolution": "clang_override_type_signature"}, []))

        def walk_function(node: dict[str, Any], current_scan_id: str | None = None, current_qn: str | None = None,
                          control_stack: tuple[str, ...] = ()):
            if node.get("kind") in DECL_KINDS and node.get("id") in function_ast_to_scan:
                current_scan_id = function_ast_to_scan[node["id"]]
                current_qn = decl_qname.get(node["id"]) or qname(node)
                control_stack = ()

            next_control_stack = control_stack
            if current_scan_id and node.get("kind") in {"IfStmt", "SwitchStmt", "ForStmt", "WhileStmt", "DoStmt", "CXXCatchStmt"}:
                line = node_line(node)
                if line is not None:
                    kind_map = {
                        "IfStmt": ("guard", "if guard", "if"),
                        "SwitchStmt": ("guard", "switch guard", "switch"),
                        "ForStmt": ("control_loop", "for loop", "for"),
                        "WhileStmt": ("control_loop", "while loop", "while"),
                        "DoStmt": ("control_loop", "do loop", "do"),
                        "CXXCatchStmt": ("error_path", "exception catch", "catch"),
                    }
                    nkind, label, ctype = kind_map[node.get("kind")]
                    excerpt = excerpt_for(node)
                    eid = stable_id("evidence", record.id, self.name, "control", current_qn, ctype, line, self.tool_version)
                    out.evidence.append(Evidence(eid, record.id, record.path, line, line, "DIRECT", self.name, excerpt))
                    cid = stable_id("node", record.id, "clang_control", current_qn, ctype, line)
                    attrs = {"control_type": ctype, "line": line, "function": current_qn, "parser": "clang_ast",
                             "compile_context_digest": context["context_digest"]}
                    if nkind == "error_path":
                        attrs["error_type"] = "catch"
                    out.nodes.append(Node(cid, nkind, label, record.id, record.path, "MAPPED", attrs, [eid]))
                    edge_kind = "contains_guard" if nkind == "guard" else "contains_error_path" if nkind == "error_path" else "contains_loop"
                    out.edges.append(Edge(stable_id("edge", current_scan_id, cid, edge_kind), current_scan_id, cid, edge_kind, "MAPPED", {"parser": "clang_ast"}, [eid]))
                    next_control_stack = control_stack + (cid,)

            if current_scan_id and node.get("kind") in {"ReturnStmt", "CXXThrowExpr"}:
                line = node_line(node)
                if line is not None:
                    is_throw = node.get("kind") == "CXXThrowExpr"
                    exit_type = "throw" if is_throw else "return"
                    excerpt = excerpt_for(node)
                    eid = stable_id("evidence", record.id, self.name, "control-exit", current_qn, exit_type, line, self.tool_version)
                    out.evidence.append(Evidence(eid, record.id, record.path, line, line, "DIRECT", self.name, excerpt))
                    xid = stable_id("node", record.id, "clang_control_exit", current_qn, exit_type, line)
                    out.nodes.append(Node(
                        xid, "control_exit", "exception" if is_throw else "early_return", record.id, record.path, "MAPPED",
                        {"exit_type": exit_type, "line": line, "function": current_qn, "parser": "clang_ast",
                         "guarded": bool(control_stack)}, [eid],
                    ))
                    out.edges.append(Edge(stable_id("edge", current_scan_id, xid, "contains_exit"), current_scan_id, xid,
                                          "contains_exit", "MAPPED", {"parser": "clang_ast"}, [eid]))
                    if control_stack:
                        out.edges.append(Edge(stable_id("edge", control_stack[-1], xid, "guards_exit"), control_stack[-1], xid,
                                              "guards_exit", "MAPPED", {"parser": "clang_ast"}, [eid]))
                    if is_throw:
                        err = stable_id("node", record.id, "clang_error_throw", current_qn, line)
                        out.nodes.append(Node(err, "error_path", "exception throw", record.id, record.path, "MAPPED",
                                              {"error_type": "throw", "line": line, "function": current_qn, "parser": "clang_ast"}, [eid]))
                        out.edges.append(Edge(stable_id("edge", xid, err, "exits_via_error"), xid, err,
                                              "exits_via_error", "MAPPED", {"parser": "clang_ast"}, [eid]))

            if current_scan_id and node.get("kind") in CALL_KINDS:
                line = node_line(node)
                source_offset = self._offset(node)
                call_excerpt = excerpt_for(node)
                ref_id = self._referenced_decl_id(node)
                root_ref = canonical_decl_id(ref_id)
                callee_qn = decl_qname.get(ref_id or "") or decl_qname.get(root_ref or "")
                signature = decl_signature.get(ref_id or "") or decl_signature.get(root_ref or "")
                receiver_type = self._receiver_static_type(node)
                template_decl = self._found_template_decl_id(node)
                template_origin = template_name_by_id.get(template_decl) if template_decl else None
                ref_node = nodes_by_ast_id.get(root_ref or ref_id or "", {})
                virtual = bool(ref_node.get("virtual"))
                dispatch_kind = "virtual_possible" if virtual else ("template_specialization" if template_origin else "direct")
                if line is not None:
                    # Clang declaration IDs are process-local pointer representations. They are
                    # valid only while resolving this AST and must not enter stable IDs or output.
                    eid = stable_id("evidence", record.id, self.name, "call", current_qn,
                                    callee_qn or "unresolved", signature, line, source_offset,
                                    call_excerpt, self.tool_version)
                    out.evidence.append(Evidence(eid, record.id, record.path, line, line,
                                                 "DIRECT", self.name, call_excerpt))
                    call_id = stable_id("node", record.id, "clang_call", current_qn, line,
                                        source_offset, callee_qn or "unresolved", signature,
                                        call_excerpt)
                    out.nodes.append(Node(
                        call_id, "call_reference", callee_qn or "compiler-resolved call", record.id, record.path,
                        "MAPPED" if callee_qn else "PARTIAL",
                        {"callee_name": (callee_qn or "").rsplit("::", 1)[-1] or None,
                         "qualified_name": callee_qn, "signature": signature,
                         "caller_qualified_name": current_qn, "line": line, "parser": "clang_ast",
                         "source_offset": source_offset,
                         "receiver_static_type": receiver_type, "dispatch_kind": dispatch_kind,
                         "template_origin": template_origin, "clang_tool_version": self.tool_version}, [eid],
                    ))
                    out.edges.append(Edge(stable_id("edge", current_scan_id, call_id, "calls"), current_scan_id, call_id, "calls", "MAPPED", {"parser": "clang_ast"}, [eid]))
                    target = definition_by_decl_root.get(root_ref or "")
                    if target:
                        out.edges.append(Edge(stable_id("edge", call_id, target, "resolves_to"), call_id, target, "resolves_to", "MAPPED", {"resolution": "clang_decl_identity", "dispatch_kind": dispatch_kind}, [eid]))
                        if virtual:
                            # Runtime dispatch may choose an overriding method. Expose those possibilities explicitly.
                            for edge in list(out.edges):
                                if edge.kind == "overrides" and edge.dst == target:
                                    out.edges.append(Edge(stable_id("edge", call_id, edge.src, "virtual_dispatch_candidate"), call_id, edge.src,
                                                          "virtual_dispatch_candidate", "PARTIAL",
                                                          {"resolution": "clang_override_candidate", "receiver_static_type": receiver_type}, [eid]))

            if current_scan_id and node.get("kind") in {"BinaryOperator", "CompoundAssignOperator"} and node.get("opcode") in {"=", "+=", "-=", "*=", "/=", "%="}:
                # Only the assignment target can be a state mutation. Earlier versions walked the
                # whole assignment and could mistake RHS reads such as `clickRow = pointPair.first`
                # for writes to `first`. Require the target member chain to be rooted in `this`, so
                # local/external object member writes are not silently promoted to specimen state.
                lhs = (node.get("inner") or [None])[0]
                member = None
                if isinstance(lhs, dict):
                    member = next((
                        x for x in self._walk(lhs)
                        if x.get("kind") == "MemberExpr" and x.get("name")
                        and any(y.get("kind") == "CXXThisExpr" for y in self._walk(x))
                    ), None)
                line = node_line(node)
                if member and line is not None:
                    member_name = str(member["name"])
                    eid = stable_id("evidence", record.id, self.name, "state-change", current_qn, member_name, line, self.tool_version)
                    out.evidence.append(Evidence(eid, record.id, record.path, line, line, "DIRECT", self.name, excerpt_for(node)))
                    state_id = stable_id("node", record.id, "clang_state_change", current_qn, member_name, line)
                    out.nodes.append(Node(
                        state_id, "state_change", member_name, record.id, record.path, "MAPPED",
                        {"member": member_name, "operator": node.get("opcode"), "line": line,
                         "mechanism": "clang_member_assignment", "parser": "clang_ast"}, [eid],
                    ))
                    out.edges.append(Edge(stable_id("edge", current_scan_id, state_id, "changes_state"), current_scan_id, state_id, "changes_state", "MAPPED", {"parser": "clang_ast"}, [eid]))

            for child in node.get("inner") or []:
                if isinstance(child, dict):
                    walk_function(child, current_scan_id, current_qn, next_control_stack)

        walk_function(ast)
        return out
