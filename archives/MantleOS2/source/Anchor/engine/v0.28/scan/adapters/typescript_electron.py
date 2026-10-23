from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any

from .base import Adapter
from ..inventory import FileRecord
from ..model import Edge, Evidence, ExtractionResult, Finding, Node, stable_id


_JS_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}
_INTERACTIVE_TAGS = {"button", "input", "textarea", "select", "option", "a", "summary"}
_INTERACTIVE_ROLES = {"button", "tab", "menuitem", "checkbox", "radio", "switch", "textbox", "searchbox", "slider", "combobox"}
_HUMAN_DOM_EVENTS = {
    "keydown", "keyup", "keypress", "click", "dblclick", "mousedown", "mouseup", "pointerdown", "pointerup",
    "contextmenu", "drop", "dragenter", "dragover", "paste", "cut", "copy", "wheel", "touchstart", "touchend",
}

_FS_EFFECTS: dict[str, tuple[str, str]] = {
    "readFile": ("filesystem_read", "read"),
    "readFileSync": ("filesystem_read", "read"),
    "stat": ("filesystem_metadata", "read"),
    "statSync": ("filesystem_metadata", "read"),
    "readdir": ("filesystem_list", "read"),
    "readdirSync": ("filesystem_list", "read"),
    "writeFile": ("filesystem_write", "write"),
    "writeFileSync": ("filesystem_write", "write"),
    "rename": ("filesystem_rename", "write"),
    "renameSync": ("filesystem_rename", "write"),
    "unlink": ("filesystem_delete", "write"),
    "unlinkSync": ("filesystem_delete", "write"),
    "mkdir": ("filesystem_mkdir", "write"),
    "mkdirSync": ("filesystem_mkdir", "write"),
    "open": ("filesystem_open", "read"),
    "openSync": ("filesystem_open", "read"),
}


def _strip_quotes(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    if len(value) >= 2 and value[0] in "'\"`" and value[-1] == value[0]:
        return value[1:-1]
    return value


def _simple_identifier(expr: str | None) -> str | None:
    if not expr:
        return None
    expr = expr.strip()
    if re.fullmatch(r"[A-Za-z_$][\w$]*", expr):
        return expr
    return None


def _callee_tail(callee: str | None) -> str:
    if not callee:
        return ""
    return re.split(r"[.?]", callee)[-1]


def _channel_key(expr: str | None, ipc_values: dict[str, str]) -> tuple[str | None, str | None]:
    if not expr:
        return None, None
    expr = expr.strip()
    m = re.fullmatch(r"IPC\.([A-Za-z_$][\w$]*)", expr)
    if m:
        key = m.group(1)
        return key, ipc_values.get(key)
    literal = _strip_quotes(expr)
    if literal and literal != expr:
        return literal, literal
    return None, None


class TypeScriptElectronAdapter(Adapter):
    """Parse JS/TS/TSX with a scanner-owned TypeScript AST probe and normalize React/Electron anatomy.

    The adapter is intentionally framework-generic. It contains no specimen names, component names,
    IPC channel values, or application-specific paths. The external Node process parses source only;
    it never imports or executes specimen modules.
    """

    name = "typescript-electron"
    version = "1"

    def accepts(self, record: FileRecord) -> bool:
        return Path(record.path).suffix.lower() in _JS_SUFFIXES and not record.is_binary

    def _probe(self, root: Path, record: FileRecord) -> dict[str, Any]:
        node = os.environ.get("SCAN_NODE_BINARY") or shutil.which("node")
        if not node:
            raise RuntimeError("Node.js is unavailable for scanner-owned TypeScript parsing")
        probe = Path(__file__).with_name("ts_probe.cjs")
        if not probe.exists():
            raise RuntimeError(f"scanner TypeScript probe missing: {probe}")
        env = os.environ.copy()
        completed = subprocess.run(
            [node, str(probe), str(root / record.path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=8,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"TypeScript probe failed ({completed.returncode}): {completed.stderr[:1200]}")
        try:
            return json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"TypeScript probe returned invalid JSON: {exc}") from exc

    def extract(self, root: Path, record: FileRecord, text: str) -> ExtractionResult:
        result = ExtractionResult()
        parsed = self._probe(root, record)
        lines = text.splitlines()

        def excerpt(line: int | None) -> str | None:
            if not line or line < 1 or line > len(lines):
                return None
            value = lines[line - 1].strip()
            return value[:500] if value else None

        def evidence(line: int | None, purpose: str, *, end_line: int | None = None) -> str:
            eid = stable_id("evidence", record.id, self.name, self.version, line, end_line, purpose)
            result.evidence.append(Evidence(
                eid, record.id, record.path, line, end_line or line, "MEASURED", f"{self.name}/{self.version}", excerpt(line)
            ))
            return eid

        def node(kind: str, name: str, *, line: int | None = None, coverage: str = "MAPPED",
                 attributes: dict[str, Any] | None = None, ev: list[str] | None = None, global_key: str | None = None) -> str:
            nid = stable_id(kind, global_key if global_key is not None else record.id, name)
            result.nodes.append(Node(
                nid, kind, name, record.id, record.path, coverage, attributes or {},
                ev if ev is not None else ([evidence(line, f"{kind}:{name}")] if line else [])
            ))
            return nid

        def edge(src: str, dst: str, kind: str, *, line: int | None = None, coverage: str = "MAPPED",
                 attributes: dict[str, Any] | None = None, ev: list[str] | None = None) -> str:
            eid = stable_id("edge", src, kind, dst, record.id, line)
            result.edges.append(Edge(
                eid, src, dst, kind, coverage, attributes or {},
                ev if ev is not None else ([evidence(line, f"edge:{kind}:{src}->{dst}")] if line else [])
            ))
            return eid

        diagnostics = (parsed.get("parser") or {}).get("diagnostics") or []
        if diagnostics:
            result.findings.append(Finding(
                stable_id("finding", record.id, self.name, "parse-diagnostics"),
                "parser_gap", f"TypeScript parser reported diagnostics for {record.path}", "PARTIAL",
                {"diagnostic_count": len(diagnostics), "diagnostics": diagnostics[:20],
                 "meaning": "AST recovery succeeded but syntax/parser diagnostics remain visible"}, []
            ))

        import_by_local: dict[str, tuple[str, str]] = {}
        imports_modules: set[str] = set()
        for item in parsed.get("imports", []):
            module = str(item.get("module") or "")
            imports_modules.add(module)
            iev = evidence(item.get("line"), f"import:{module}")
            inode = node("module_reference", module, line=item.get("line"), attributes={"module": module}, ev=[iev])
            for binding in item.get("bindings", []):
                local = str(binding.get("local") or "")
                imported = str(binding.get("imported") or "")
                if local:
                    import_by_local[local] = (module, imported)
                    bnode = node("symbol", local, line=item.get("line"), attributes={
                        "symbol_role": "import_binding", "module": module, "imported": imported,
                    }, ev=[iev])
                    edge(bnode, inode, "resolves_to", line=item.get("line"), ev=[iev])

        local_symbols: dict[str, str] = {}
        function_lines: dict[str, int] = {}
        for fn in parsed.get("functions", []):
            name = str(fn.get("name") or "<function>")
            line = int(fn.get("line") or 0) or None
            ev = evidence(line, f"function:{name}", end_line=fn.get("endLine"))
            sid = node("symbol", name, line=line, attributes={
                "symbol_role": "function", "language": record.language,
                "syntax_kind": fn.get("kind"), "async": bool(fn.get("async")),
                "class_name": fn.get("className"), "parameters": fn.get("parameters") or [],
                "end_line": fn.get("endLine"),
            }, ev=[ev])
            local_symbols[name] = sid
            function_lines[name] = line or 0

        for cls in parsed.get("classes", []):
            name = str(cls.get("name") or "<class>")
            cev = evidence(cls.get("line"), f"class:{name}", end_line=cls.get("endLine"))
            node("symbol", name, line=cls.get("line"), attributes={
                "symbol_role": "class", "extends": cls.get("extends") or [], "end_line": cls.get("endLine")
            }, ev=[cev])

        ipc_values: dict[str, str] = {}
        for obj in parsed.get("objectConstants", []):
            if obj.get("name") == "IPC":
                for prop in obj.get("properties", []):
                    if prop.get("name") and prop.get("literal") is not None:
                        ipc_values[str(prop["name"])] = str(prop["literal"])

        def ipc_node(channel_expr: str | None, line: int | None) -> str | None:
            key, value = _channel_key(channel_expr, ipc_values)
            if not key:
                return None
            label = value or key
            ev = evidence(line, f"ipc-channel:{key}:{label}")
            return node("ipc_channel", label, line=line, coverage="MAPPED" if value else "PARTIAL", attributes={
                "channel_key": key, "channel_value": value, "framework": "electron_ipc"
            }, ev=[ev], global_key=f"electron-ipc:{key}:{value}")

        def handler_ref(expr: str, line: int | None, *, role: str = "handler_reference") -> str:
            expr = expr.strip()
            ev = evidence(line, f"handler:{expr}")
            hid = node("handler_reference", expr, line=line, coverage="PARTIAL", attributes={
                "expression": expr, "framework": "javascript"
            }, ev=[ev])
            simple = _simple_identifier(expr)
            if simple and simple in local_symbols:
                edge(hid, local_symbols[simple], "resolves_to", line=line, ev=[ev])
            return hid

        # A global identity for React prop endpoints lets a surface in Child.tsx route through
        # <Child onFoo={handler}> in Parent.tsx without guessing based on filenames.
        def prop_endpoint(component: str, prop: str, line: int | None) -> str:
            ev = evidence(line, f"react-prop:{component}.{prop}")
            return node("handler_reference", f"{component}.{prop}", line=line, coverage="PARTIAL", attributes={
                "framework": "react", "component": component, "prop": prop, "role": "prop_endpoint"
            }, ev=[ev], global_key=f"react-prop:{component}:{prop}")

        # Exposed preload object method symbols are normalized to a global endpoint so calls such
        # as window.api.save() can meet api.save = () => ipcRenderer.invoke(...) across files.
        preload_methods: dict[str, str] = {}
        for fn_name, sid in list(local_symbols.items()):
            m = re.fullmatch(r"([A-Za-z_$][\w$]*)\.([A-Za-z_$][\w$]*)", fn_name)
            if not m:
                continue
            owner, method = m.groups()
            endpoint = node("handler_reference", f"preload:{owner}.{method}", line=function_lines.get(fn_name), coverage="PARTIAL",
                            attributes={"framework": "electron", "role": "preload_api", "object": owner, "method": method},
                            global_key=f"preload-api:{owner}:{method}")
            preload_methods[f"{owner}.{method}"] = endpoint
            edge(endpoint, sid, "resolves_to", line=function_lines.get(fn_name))

        # Component prop bindings are structural routing evidence, not separate human surfaces.
        for jsx in parsed.get("jsx", []):
            if not jsx.get("customComponent"):
                continue
            component = str(jsx.get("tag") or "")
            attrs = jsx.get("attributes") or {}
            for prop, expr in attrs.items():
                if not re.match(r"^on[A-Z]", str(prop)) or not expr:
                    continue
                endpoint = prop_endpoint(component, str(prop), jsx.get("line"))
                target = handler_ref(str(expr), jsx.get("line"))
                edge(endpoint, target, "routes_to", line=jsx.get("line"), coverage="PARTIAL")

        # Intrinsic JSX controls are the physical surface denominator. Custom component instances
        # only provide prop-routing evidence above, preventing double-counting of one physical button.
        for jsx in parsed.get("jsx", []):
            if jsx.get("customComponent"):
                continue
            tag = str(jsx.get("tag") or "").lower()
            attrs = jsx.get("attributes") or {}
            events = jsx.get("eventAttributes") or {}
            role = _strip_quotes(str(attrs.get("role") or "")) or str(attrs.get("role") or "")
            if tag not in _INTERACTIVE_TAGS and role not in _INTERACTIVE_ROLES and not events:
                continue
            label = jsx.get("text") or attrs.get("aria-label") or attrs.get("title") or attrs.get("placeholder") or f"<{tag}>@{jsx.get('line')}"
            label = str(label)
            sev = evidence(jsx.get("line"), f"jsx-surface:{tag}:{label}")
            surface = node("human_surface", label, line=jsx.get("line"), coverage="MAPPED", attributes={
                "surface_type": f"react_jsx:{tag}", "surface_role": "input", "tag": tag,
                "role": role or None, "disabled_condition": attrs.get("disabled"), "hidden_condition": attrs.get("hidden"),
                "event_props": sorted(events), "component_function": jsx.get("function"),
            }, ev=[sev])
            component_fn = str(jsx.get("function") or "")
            component_name = component_fn.split(".")[-1] if component_fn else ""
            for event_name, expr in events.items():
                expr = str(expr or "").strip()
                if not expr:
                    continue
                pm = re.fullmatch(r"props\.([A-Za-z_$][\w$]*)", expr)
                if pm and component_name:
                    target = prop_endpoint(component_name, pm.group(1), jsx.get("line"))
                else:
                    target = handler_ref(expr, jsx.get("line"))
                edge(surface, target, "dispatches_to", line=jsx.get("line"), coverage="MAPPED")

        # Generic call graph and framework/effect classification.
        calls = parsed.get("calls", [])
        callback_symbols: list[tuple[str, int, str]] = [
            (name, function_lines.get(name, 0), sid) for name, sid in local_symbols.items() if name.startswith("callback:")
        ]
        user_data_seen = False
        fs_write_effects: list[str] = []

        def owning_symbol(fn_name: str | None) -> str | None:
            if not fn_name:
                return None
            return local_symbols.get(str(fn_name))

        def effect_from_call(callee: str, line: int | None, call_id: str, import_binding: tuple[str, str] | None) -> str | None:
            nonlocal user_data_seen
            tail = _callee_tail(callee)
            module = import_binding[0] if import_binding else None
            imported = import_binding[1] if import_binding else None
            classification = "typescript_import_resolved_api" if module else "typescript_ast_api"

            if module in {"node:fs", "node:fs/promises", "fs", "fs/promises"} and imported in _FS_EFFECTS:
                effect_type, direction = _FS_EFFECTS[imported]
                ee = evidence(line, f"effect:{effect_type}:{callee}")
                en = node("effect", f"{effect_type}:{callee}", line=line, attributes={
                    "effect_type": effect_type, "capability": "filesystem", "direction": direction,
                    "classification": classification, "capability_provenance": "COUPLED",
                    "module": module, "api": imported,
                }, ev=[ee])
                edge(call_id, en, "produces_effect", line=line, ev=[ee])
                if direction == "write":
                    fs_write_effects.append(en)
                return en

            if callee.endswith("dialog.showOpenDialog") or callee.endswith("dialog.showSaveDialog"):
                ee = evidence(line, f"effect:native_dialog:{callee}")
                en = node("effect", f"native_dialog:{tail}", line=line, attributes={
                    "effect_type": "native_dialog", "capability": "native_dialog", "direction": "human_io",
                    "classification": "typescript_import_resolved_api", "capability_provenance": "BORROWED",
                }, ev=[ee])
                edge(call_id, en, "produces_effect", line=line, ev=[ee])
                return en

            if callee.endswith("shell.openExternal") or callee.endswith("shell.openPath"):
                ee = evidence(line, f"effect:os_shell:{callee}")
                en = node("effect", f"os_shell:{tail}", line=line, attributes={
                    "effect_type": "os_shell_open", "capability": "os_shell", "direction": "outbound",
                    "classification": "typescript_import_resolved_api", "capability_provenance": "BORROWED",
                }, ev=[ee])
                edge(call_id, en, "produces_effect", line=line, ev=[ee])
                return en

            if callee.endswith("app.getPath"):
                ee = evidence(line, f"effect:app_path_read:{callee}")
                en = node("effect", "electron_app_path_read", line=line, attributes={
                    "effect_type": "environment_read", "capability": "application_paths", "direction": "read",
                    "classification": "typescript_import_resolved_api", "capability_provenance": "BORROWED",
                }, ev=[ee])
                edge(call_id, en, "produces_effect", line=line, ev=[ee])
                return en

            if tail == "checkForUpdates" and "electron-updater" in imports_modules:
                ee = evidence(line, f"effect:update_check:{callee}")
                en = node("effect", "application_update_check", line=line, coverage="PARTIAL", attributes={
                    "effect_type": "network_request", "capability": "application_updates", "direction": "outbound",
                    "classification": "typescript_ast_framework_api", "capability_provenance": "COUPLED",
                }, ev=[ee])
                edge(call_id, en, "produces_effect", line=line, coverage="PARTIAL", ev=[ee])
                return en

            if callee.endswith("dialog.showMessageBox") or callee.endswith("dialog.showErrorBox"):
                fe = evidence(line, f"feedback:dialog:{callee}")
                fn = node("feedback", f"modal_feedback:{tail}", line=line, attributes={"feedback_type": "modal_message"}, ev=[fe])
                edge(call_id, fn, "produces_feedback", line=line, ev=[fe])
                return fn
            return None

        for call in calls:
            callee = str(call.get("callee") or "")
            line = int(call.get("line") or 0) or None
            cev = evidence(line, f"call:{callee}")
            cid = node("call_reference", callee or f"call@{line}", line=line, coverage="PARTIAL", attributes={
                "callee": callee, "arguments": call.get("args") or [], "containing_function": call.get("function")
            }, ev=[cev])
            owner = owning_symbol(call.get("function"))
            if owner:
                edge(owner, cid, "calls", line=line, coverage="MAPPED", ev=[cev])

            simple = _simple_identifier(callee)
            if simple and simple in local_symbols:
                edge(cid, local_symbols[simple], "resolves_to", line=line, coverage="MAPPED", ev=[cev])

            root_name = callee.split(".", 1)[0].replace("?", "") if callee else ""
            import_binding = import_by_local.get(root_name)
            effect_from_call(callee, line, cid, import_binding)

            args = call.get("args") or []
            if callee.endswith("app.getPath") and args and _strip_quotes(str(args[0])) == "userData":
                user_data_seen = True

            if callee.endswith("window.addEventListener") or callee.endswith("document.addEventListener"):
                event_name = _strip_quotes(str(args[0])) if args else None
                if event_name in _HUMAN_DOM_EVENTS:
                    hev = evidence(line, f"dom-human-event:{event_name}")
                    surf = node("human_surface", f"DOM {event_name}", line=line, attributes={
                        "surface_type": f"dom_event:{event_name}", "surface_role": "input"
                    }, ev=[hev])
                    if len(args) > 1:
                        hid = handler_ref(str(args[1]), line)
                        edge(surf, hid, "dispatches_to", line=line, ev=[hev])

            # Renderer -> preload endpoint routing.
            m_api = re.fullmatch(r"window\.([A-Za-z_$][\w$]*)\.([A-Za-z_$][\w$]*)", callee)
            if m_api:
                owner_name, method = m_api.groups()
                endpoint = node("handler_reference", f"preload:{owner_name}.{method}", line=line, coverage="PARTIAL",
                                attributes={"framework": "electron", "role": "preload_api", "object": owner_name, "method": method},
                                global_key=f"preload-api:{owner_name}:{method}")
                edge(cid, endpoint, "routes_to", line=line, coverage="PARTIAL", ev=[cev])

            # Electron renderer IPC send/invoke/listen edges.
            if re.search(r"(?:^|\.)ipcRenderer\.(invoke|send|on|postMessage)$", callee):
                ch = ipc_node(str(args[0]) if args else None, line)
                if ch:
                    edge(cid, ch, "crosses_boundary", line=line, coverage="MAPPED", ev=[cev])

            # Electron main-side IPC registration, including generic trusted-wrapper functions.
            if callee in {"ipcMain.handle", "ipcMain.on", "handleFromRenderer", "onFromRenderer"}:
                ch = ipc_node(str(args[0]) if args else None, line)
                if ch:
                    handler = node("handler_reference", f"IPC handler {args[0] if args else ch}", line=line, coverage="PARTIAL",
                                   attributes={"framework": "electron_ipc", "registration": callee}, ev=[cev])
                    edge(ch, handler, "dispatches_to", line=line, coverage="MAPPED", ev=[cev])
                    # Associate the scanner-observed callback function when it begins near this registration.
                    for cb_name, cb_line, cb_sid in callback_symbols:
                        if cb_name.startswith(f"callback:{callee}@") and abs(cb_line - (line or 0)) <= 4:
                            edge(handler, cb_sid, "resolves_to", line=cb_line, coverage="PARTIAL")
                            break

            if callee.endswith("contextBridge.exposeInMainWorld") and len(args) >= 2:
                world = _strip_quotes(str(args[0])) or str(args[0])
                obj = str(args[1])
                bev = evidence(line, f"context-bridge:{world}:{obj}")
                boundary = node("nest_boundary", f"Electron contextBridge:{world}", line=line, attributes={
                    "boundary_type": "electron_context_bridge", "direction": "bidirectional-mediated",
                    "world_name": world, "exposed_object": obj, "classification": "typescript_import_resolved_api"
                }, ev=[bev])
                edge(cid, boundary, "crosses_boundary", line=line, ev=[bev])

            if callee.endswith("protocol.handle") or callee.endswith("protocol.registerSchemesAsPrivileged"):
                bev = evidence(line, f"electron-protocol:{callee}")
                boundary = node("nest_boundary", "Electron custom protocol", line=line, attributes={
                    "boundary_type": "custom_protocol", "direction": "inbound", "classification": "typescript_import_resolved_api"
                }, ev=[bev])
                edge(cid, boundary, "crosses_boundary", line=line, ev=[bev])

        # New BrowserWindow(...) is strong evidence of a desktop window/NEST seam. We preserve the
        # raw options expression rather than pretending to evaluate arbitrary JavaScript.
        for new_expr in parsed.get("news", []):
            callee = str(new_expr.get("callee") or "")
            if callee != "BrowserWindow":
                continue
            line = int(new_expr.get("line") or 0) or None
            nev = evidence(line, "electron-browser-window")
            boundary = node("nest_boundary", "Electron BrowserWindow", line=line, attributes={
                "boundary_type": "desktop_window", "direction": "human_io", "classification": "typescript_import_resolved_api",
                "options_expression": (new_expr.get("args") or [None])[0],
            }, ev=[nev])
            owner = owning_symbol(new_expr.get("function"))
            if owner:
                edge(owner, boundary, "crosses_boundary", line=line, ev=[nev])

        if user_data_seen:
            pev = evidence(1 if lines else None, "electron-userdata-persistence-provider")
            provider = node("persistence_provider", "Electron userData", line=1 if lines else None, coverage="MAPPED", attributes={
                "provider_type": "filesystem_directory", "nest_provider": "electron_app_path", "path_key": "userData"
            }, ev=[pev])
            for eff in fs_write_effects:
                op = node("persistence_operation", f"persist via {eff}", coverage="PARTIAL", attributes={
                    "operation": "write", "provider": "Electron userData", "classification": "same_module_candidate"
                }, ev=[pev])
                edge(eff, op, "has_effect", coverage="PARTIAL", ev=[pev])
                edge(op, provider, "crosses_boundary", coverage="PARTIAL", ev=[pev])

        # Preserve one explicit adapter finding so transferability and parser provenance are visible.
        result.findings.append(Finding(
            stable_id("finding", record.id, self.name, self.version, "parser"),
            "adapter_provenance", f"Parsed {record.path} with TypeScript compiler API", "MAPPED" if not diagnostics else "PARTIAL",
            {"typescript_version": (parsed.get("parser") or {}).get("version"),
             "function_count": len(parsed.get("functions", [])), "call_count": len(calls),
             "jsx_count": len(parsed.get("jsx", [])), "diagnostic_count": len(diagnostics)}, []
        ))
        return result


class ElectronMetadataAdapter(Adapter):
    """Extract Electron application/NEST declarations from package.json and electron-builder YAML.

    Build metadata is treated as direct configuration evidence, not proof that a packaged runtime
    successfully exercises the declared capability.
    """

    name = "electron-metadata"
    version = "1"

    def accepts(self, record: FileRecord) -> bool:
        name = Path(record.path).name.lower()
        return name == "package.json" or name in {"electron-builder.yml", "electron-builder.yaml"}

    def extract(self, root: Path, record: FileRecord, text: str) -> ExtractionResult:
        result = ExtractionResult()
        lines = text.splitlines()

        def ev(line: int | None, purpose: str) -> str:
            eid = stable_id("evidence", record.id, self.name, self.version, line, purpose)
            excerpt = lines[line - 1].strip()[:500] if line and 0 < line <= len(lines) else None
            result.evidence.append(Evidence(eid, record.id, record.path, line, line, "DIRECT", f"{self.name}/{self.version}", excerpt))
            return eid

        def add_node(kind: str, name: str, line: int | None, coverage: str, attrs: dict[str, Any], key: str | None = None) -> str:
            evid = ev(line, f"{kind}:{name}")
            nid = stable_id(kind, key or record.id, name)
            result.nodes.append(Node(nid, kind, name, record.id, record.path, coverage, attrs, [evid]))
            return nid

        name = Path(record.path).name.lower()
        if name == "package.json":
            try:
                data = json.loads(text)
            except json.JSONDecodeError as exc:
                result.findings.append(Finding(stable_id("finding", record.id, self.name, "json"), "parser_gap",
                                               "Malformed package.json", "BLOCKED", {"error": str(exc)}, []))
                return result
            deps = {**(data.get("dependencies") or {}), **(data.get("devDependencies") or {})}
            if "electron" in deps:
                add_node("nest_boundary", "Electron runtime", 1, "PARTIAL", {
                    "boundary_type": "desktop_runtime", "provider": "electron", "declared_version": deps.get("electron"),
                    "classification": "build_metadata"
                }, key="electron-runtime")
            if "electron-updater" in deps:
                add_node("nest_boundary", "Electron updater service", 1, "PARTIAL", {
                    "boundary_type": "application_updates", "provider": "electron-updater", "declared_version": deps.get("electron-updater"),
                    "classification": "build_metadata"
                }, key="electron-updater")
            main = data.get("main")
            if isinstance(main, str):
                add_node("entry_point", main, 1, "MAPPED", {"entry_type": "electron_main", "declared_by": "package.json"})
        else:
            # Conservative line-oriented YAML extraction: preserve declarations without evaluating
            # templates or platform conditions.
            publish_provider = None
            in_file_assoc = False
            for idx, raw in enumerate(lines, 1):
                stripped = raw.strip()
                if stripped.startswith("fileAssociations:"):
                    in_file_assoc = True
                    continue
                if in_file_assoc and re.match(r"^[A-Za-z][A-Za-z0-9_-]*:", stripped) and not stripped.startswith(("ext:", "name:", "description:", "role:", "mimeType:")):
                    in_file_assoc = False
                m_ext = re.match(r"-?\s*ext:\s*['\"]?([^'\"#\s]+)", stripped)
                if in_file_assoc and m_ext:
                    ext = m_ext.group(1)
                    add_node("human_surface", f"OS file association .{ext}", idx, "PARTIAL", {
                        "surface_type": "os_file_association", "surface_role": "input", "extension": ext,
                        "declaration_only": True
                    }, key=f"file-association:{ext}")
                if stripped.startswith("provider:"):
                    publish_provider = stripped.split(":", 1)[1].strip().strip("'\"")
                    if publish_provider:
                        add_node("nest_boundary", f"Release provider: {publish_provider}", idx, "PARTIAL", {
                            "boundary_type": "release_provider", "provider": publish_provider,
                            "classification": "build_metadata"
                        }, key=f"release-provider:{publish_provider}")
            if publish_provider:
                result.findings.append(Finding(
                    stable_id("finding", record.id, self.name, "publish-provider", publish_provider),
                    "nest_candidate", f"Electron build declares release provider {publish_provider}", "PARTIAL",
                    {"provider": publish_provider, "meaning": "declaration does not prove runtime update coupling"}, []
                ))
        return result
