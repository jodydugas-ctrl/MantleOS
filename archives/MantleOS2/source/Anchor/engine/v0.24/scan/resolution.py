from __future__ import annotations

from collections import defaultdict
import json
import re

from .model import Edge, ExtractionResult, Finding, Node, stable_id
from .effect_catalog import classify_typed_call


def resolve_cross_file(result: ExtractionResult) -> ExtractionResult:
    """Add conservative cross-file resolution edges after per-file adapters run.

    Resolution is deliberately uniqueness-gated. When a UI object name or qualified handler name maps
    to more than one declaration, SCAN preserves the ambiguity as a finding instead of guessing.
    """
    out = ExtractionResult()
    nodes = {n.id: n for n in result.nodes}
    existing_edge_keys = {(e.src, e.dst, e.kind) for e in result.edges}

    def add_edge(edge: Edge) -> None:
        key = (edge.src, edge.dst, edge.kind)
        if key in existing_edge_keys:
            return
        existing_edge_keys.add(key)
        out.edges.append(edge)

    ui_declarations: dict[str, list] = defaultdict(list)
    ui_references: dict[str, list] = defaultdict(list)
    symbols: dict[str, list] = defaultdict(list)
    symbols_by_signature: dict[tuple[str, str], list] = defaultdict(list)
    bare_symbols: dict[str, list] = defaultdict(list)
    type_definitions: dict[str, list] = defaultdict(list)
    type_references: dict[str, list] = defaultdict(list)
    handlers: dict[str, list] = defaultdict(list)
    member_symbols: dict[tuple[str, str], list] = defaultdict(list)
    call_refs: list = []

    for n in nodes.values():
        attrs = n.attributes or {}
        qname = attrs.get("qt_object_name")
        if qname:
            if n.kind == "human_surface" and attrs.get("surface_type") not in {"ui_object_reference", "keyboard_shortcut", "QShortcut"}:
                ui_declarations[str(qname)].append(n)
            elif n.kind == "surface_reference":
                ui_references[str(qname)].append(n)
        if n.kind == "symbol":
            qualified = attrs.get("qualified_name") or n.name
            symbols[str(qualified)].append(n)
            if attrs.get("signature"):
                symbols_by_signature[(str(qualified), str(attrs["signature"]))].append(n)
            bare_symbols[str(qualified).rsplit("::", 1)[-1]].append(n)
        elif n.kind == "type_symbol":
            qualified = attrs.get("qualified_name") or n.name
            type_definitions[str(qualified)].append(n)
        elif n.kind == "type_reference":
            qualified = attrs.get("qualified_name") or n.name
            type_references[str(qualified)].append(n)
        elif n.kind == "handler_reference":
            qualified = attrs.get("qualified_name") or n.name
            handlers[str(qualified)].append(n)
        elif n.kind == "member_symbol":
            owner = attrs.get("owner_class")
            member = attrs.get("member_name")
            if owner and member:
                member_symbols[(str(owner), str(member))].append(n)
        elif n.kind == "call_reference":
            call_refs.append(n)

    # QAction declarations and references already share an ID. Generic widgets cannot because the same
    # objectName may legally appear in multiple .ui files, so resolve only globally unique names.
    for object_name, refs in sorted(ui_references.items()):
        decls = ui_declarations.get(object_name, [])
        if len(decls) == 1:
            decl = decls[0]
            for ref in refs:
                if decl.id == ref.id:
                    continue
                ev_ids = sorted(set(decl.evidence_ids + ref.evidence_ids))
                add_edge(Edge(
                    stable_id("edge", decl.id, ref.id, "resolves_to"), decl.id, ref.id,
                    "resolves_to", "MAPPED",
                    {"resolution": "unique_qt_object_name", "qt_object_name": object_name}, ev_ids,
                ))
        elif len(decls) > 1:
            out.findings.append(Finding(
                stable_id("finding", "ambiguous-qt-object", object_name, *sorted(d.id for d in decls)),
                "resolution_gap", f"Ambiguous Qt objectName reference: {object_name}", "PARTIAL",
                {"qt_object_name": object_name, "declaration_ids": sorted(d.id for d in decls),
                 "reference_ids": sorted(r.id for r in refs)},
                sorted({eid for n in decls + refs for eid in n.evidence_ids}),
            ))

    def declared_type_owner(value: str | None) -> str | None:
        if not value:
            return None
        t = re.sub(r"\b(const|volatile|class|struct|typename)\b", "", str(value))
        t = re.sub(r"[\*&]+", "", t)
        t = re.sub(r"\s+", " ", t).strip()
        return t.split("<", 1)[0].strip() or None

    # Resolve project-local call references conservatively. Exact/context-qualified names are preferred.
    # Bare calls are linked only when there is exactly one project definition and no receiver whose type
    # would be required to prove dispatch. Ambiguity is preserved as a finding rather than guessed.
    for ref in call_refs:
        attrs = ref.attributes or {}
        receiver = attrs.get("receiver")
        exact_names = []
        if attrs.get("qualified_name"):
            exact_names.append(str(attrs["qualified_name"]))
        if attrs.get("context_qualified_name"):
            exact_names.append(str(attrs["context_qualified_name"]))
        exact_names = list(dict.fromkeys(exact_names))

        resolved = False
        for qualified in exact_names:
            signature = attrs.get("signature")
            defs = symbols_by_signature.get((qualified, str(signature)), []) if signature else symbols.get(qualified, [])
            if signature and not defs:
                defs = symbols.get(qualified, [])
            if len(defs) == 1:
                definition = defs[0]
                add_edge(Edge(
                    stable_id("edge", ref.id, definition.id, "resolves_to"), ref.id, definition.id,
                    "resolves_to", "MAPPED",
                    {"resolution": "exact_or_context_qualified_call", "qualified_name": qualified},
                    sorted(set(ref.evidence_ids + definition.evidence_ids)),
                ))
                resolved = True
                break
            if len(defs) > 1:
                out.findings.append(Finding(
                    stable_id("finding", "ambiguous-call", ref.id, qualified, *sorted(d.id for d in defs)),
                    "resolution_gap", f"Ambiguous call target: {qualified}", "PARTIAL",
                    {"call_reference_id": ref.id, "qualified_name": qualified,
                     "definition_ids": sorted(d.id for d in defs)},
                    sorted({eid for n in defs + [ref] for eid in n.evidence_ids}),
                ))
                resolved = True
                break
        if resolved:
            continue

        bare = str(attrs.get("callee_name") or ref.name).rsplit("::", 1)[-1]

        # Fallback member calls can still be resolved when the receiver is a uniquely declared class
        # data member with an explicit static type, e.g. `GameModel *game; game->startGame(...)`.
        # This is direct source evidence and remains conservative: owner/member and target definition
        # must each be unique. Local-variable type inference is intentionally left to compiler AST work.
        if receiver and not str(receiver).startswith("this"):
            receiver_name = str(receiver).strip()
            receiver_name = re.sub(r"(?:->|\.)\s*$", "", receiver_name).strip()
            caller = str(attrs.get("caller_qualified_name") or "")
            caller_owner = caller.rsplit("::", 1)[0] if "::" in caller else None
            members = member_symbols.get((caller_owner, receiver_name), []) if caller_owner else []
            if len(members) == 1:
                member = members[0]
                target_owner = declared_type_owner((member.attributes or {}).get("declared_type"))
                qualified = f"{target_owner}::{bare}" if target_owner else None
                defs = symbols.get(qualified, []) if qualified else []
                if len(defs) == 1:
                    definition = defs[0]
                    ev_ids = sorted(set(ref.evidence_ids + member.evidence_ids + definition.evidence_ids))
                    add_edge(Edge(
                        stable_id("edge", ref.id, member.id, "receiver_typed_by"), ref.id, member.id,
                        "receiver_typed_by", "MAPPED",
                        {"resolution": "unique_class_member_static_type", "receiver": receiver_name,
                         "receiver_static_type": target_owner, "caller_owner": caller_owner}, ev_ids,
                    ))
                    add_edge(Edge(
                        stable_id("edge", ref.id, definition.id, "resolves_to"), ref.id, definition.id,
                        "resolves_to", "MAPPED",
                        {"resolution": "unique_class_member_static_type", "qualified_name": qualified,
                         "receiver": receiver_name, "receiver_static_type": target_owner}, ev_ids,
                    ))
                    continue
                if len(defs) > 1:
                    out.findings.append(Finding(
                        stable_id("finding", "ambiguous-member-call", ref.id, qualified, *sorted(d.id for d in defs)),
                        "resolution_gap", f"Ambiguous member-call target: {qualified}", "PARTIAL",
                        {"call_reference_id": ref.id, "qualified_name": qualified,
                         "receiver": receiver_name, "receiver_member_id": member.id,
                         "definition_ids": sorted(d.id for d in defs)},
                        sorted({eid for n in defs + [member, ref] for eid in n.evidence_ids}),
                    ))
                    continue
            elif len(members) > 1:
                out.findings.append(Finding(
                    stable_id("finding", "ambiguous-receiver-member", ref.id, caller_owner, receiver_name,
                              *sorted(m.id for m in members)),
                    "resolution_gap", f"Ambiguous receiver member type: {caller_owner}::{receiver_name}", "PARTIAL",
                    {"call_reference_id": ref.id, "caller_owner": caller_owner, "receiver": receiver_name,
                     "member_ids": sorted(m.id for m in members)},
                    sorted({eid for n in members + [ref] for eid in n.evidence_ids}),
                ))
                continue
            continue

        defs = bare_symbols.get(bare, [])
        if len(defs) == 1:
            definition = defs[0]
            add_edge(Edge(
                stable_id("edge", ref.id, definition.id, "resolves_to"), ref.id, definition.id,
                "resolves_to", "PARTIAL",
                {"resolution": "unique_bare_call", "callee_name": bare,
                 "limitation": "fallback parser lacks compiler type resolution"},
                sorted(set(ref.evidence_ids + definition.evidence_ids)),
            ))
        elif len(defs) > 1:
            out.findings.append(Finding(
                stable_id("finding", "ambiguous-call-bare", ref.id, bare, *sorted(d.id for d in defs)),
                "resolution_gap", f"Ambiguous unqualified call target: {bare}", "PARTIAL",
                {"call_reference_id": ref.id, "callee_name": bare,
                 "definition_ids": sorted(d.id for d in defs)},
                sorted({eid for n in defs + [ref] for eid in n.evidence_ids}),
            ))

    # Function-context indexes support M3C persistence/state and capability synthesis.
    caller_by_call: dict[str, list[str]] = defaultdict(list)
    state_changes_by_caller: dict[str, list] = defaultdict(list)
    for edge in result.edges:
        if edge.kind == "calls":
            caller_by_call[edge.dst].append(edge.src)
        elif edge.kind == "changes_state":
            node = nodes.get(edge.dst)
            if node is not None:
                state_changes_by_caller[edge.src].append(node)

    persistence_effect_types = {
        "settings_write", "settings_sync", "filesystem_commit", "persistence_cancel",
        "file_lock_acquire", "file_lock_release",
    }

    # Compiler-typed framework calls and fallback calls with a unique direct source declaration can
    # support high-confidence NEST/effect/feedback semantics. The fallback path does not infer aliases,
    # assignments, casts, or auto types; it requires an explicit local/parameter receiver type.
    for ref in call_refs:
        attrs = ref.attributes or {}
        compiler_typed = attrs.get("parser") == "clang_ast"
        source_typed = (
            attrs.get("parser") == "brace_aware_cpp_fallback"
            and attrs.get("receiver_type_source") == "direct_local_or_parameter_declaration"
            and attrs.get("receiver_static_type")
        )
        if not compiler_typed and not source_typed:
            continue
        classification = "compiler_typed_api" if compiler_typed else "source_declared_receiver_api"
        typed = classify_typed_call(
            qualified_name=attrs.get("qualified_name"),
            receiver_static_type=attrs.get("receiver_static_type"),
            callee_name=attrs.get("callee_name"),
        )
        if not typed:
            continue
        if typed["kind"] == "effect":
            eid_list = list(ref.evidence_ids)
            effect_id = stable_id("node", ref.id, "typed_effect", typed["effect_type"])
            out.nodes.append(Node(
                effect_id, "effect", typed["effect_type"], ref.file_id, ref.path, "MAPPED",
                {**typed, "classification": classification, "call_reference_id": ref.id,
                 "capability_provenance": "COUPLED"}, eid_list,
            ))
            add_edge(Edge(stable_id("edge", ref.id, effect_id, "has_effect"), ref.id, effect_id,
                          "has_effect", "MAPPED", {"resolution": classification}, eid_list))
            boundary_id = stable_id("node", ref.id, "typed_nest_boundary", typed["capability"])
            out.nodes.append(Node(
                boundary_id, "nest_boundary", typed["capability"], ref.file_id, ref.path, "MAPPED",
                {"boundary_type": typed["capability"], "direction": typed["direction"],
                 "provider_type": typed["owner_type"], "classification": classification}, eid_list,
            ))
            add_edge(Edge(stable_id("edge", ref.id, boundary_id, "crosses_boundary"), ref.id, boundary_id,
                          "crosses_boundary", "MAPPED", {"resolution": classification}, eid_list))

            if typed["effect_type"] in persistence_effect_types or typed.get("owner_type") in {"QSettings", "QSaveFile", "QLockFile"}:
                persistence_id = stable_id("node", ref.id, "persistence_operation", typed["effect_type"])
                out.nodes.append(Node(
                    persistence_id, "persistence_operation", typed["effect_type"], ref.file_id, ref.path, "MAPPED",
                    {"operation": typed["effect_type"], "provider_type": typed.get("owner_type"),
                     "capability": typed.get("capability"), "direction": typed.get("direction"),
                     "classification": "compiler_typed_persistence" if compiler_typed else "source_declared_receiver_persistence",
                     "call_reference_id": ref.id}, eid_list,
                ))
                add_edge(Edge(stable_id("edge", ref.id, persistence_id, "persists_via"), ref.id, persistence_id,
                              "persists_via", "MAPPED", {"resolution": classification}, eid_list))
                add_edge(Edge(stable_id("edge", effect_id, persistence_id, "has_persistence_semantics"), effect_id, persistence_id,
                              "has_persistence_semantics", "MAPPED", {}, eid_list))

                # Same-function state mutation followed by a durable provider call is a useful persistence
                # candidate, but it is not variable-level data-flow proof. Keep it explicitly PARTIAL.
                call_line = attrs.get("line")
                for caller in caller_by_call.get(ref.id, []):
                    for state in state_changes_by_caller.get(caller, []):
                        state_line = (state.attributes or {}).get("line")
                        if isinstance(call_line, int) and isinstance(state_line, int) and state_line > call_line:
                            continue
                        add_edge(Edge(
                            stable_id("edge", state.id, persistence_id, "persistence_candidate"), state.id, persistence_id,
                            "persistence_candidate", "PARTIAL",
                            {"basis": "same function; state mutation precedes typed persistence operation",
                             "caller_id": caller, "variable_flow_proven": False},
                            sorted(set(state.evidence_ids + eid_list)),
                        ))
        elif typed["kind"] == "feedback":
            eid_list = list(ref.evidence_ids)
            feedback_id = stable_id("node", ref.id, "typed_feedback", typed["feedback_type"])
            out.nodes.append(Node(
                feedback_id, "feedback", typed["feedback_type"], ref.file_id, ref.path, "MAPPED",
                {**typed, "classification": "compiler_typed_api", "call_reference_id": ref.id}, eid_list,
            ))
            add_edge(Edge(stable_id("edge", ref.id, feedback_id, "has_feedback"), ref.id, feedback_id,
                          "has_feedback", "MAPPED", {"resolution": "compiler_typed_api"}, eid_list))
        elif typed["kind"] == "extension":
            eid_list = list(ref.evidence_ids)
            receptor_id = stable_id("node", ref.id, "typed_extension_receptor", typed["receptor_type"], typed["method"])
            out.nodes.append(Node(
                receptor_id, "extension_receptor", f"{typed['receptor_type']}:{typed['method']}",
                ref.file_id, ref.path, "MAPPED",
                {**typed, "classification": "compiler_typed_extension_api" if compiler_typed else "source_declared_receiver_extension_api",
                 "call_reference_id": ref.id,
                 "capability_provenance": "COUPLED"}, eid_list,
            ))
            add_edge(Edge(stable_id("edge", ref.id, receptor_id, "reaches_extension"), ref.id, receptor_id,
                          "reaches_extension", "MAPPED", {"resolution": classification}, eid_list))
            if typed.get("factory"):
                factory_id = stable_id("node", receptor_id, "capability_factory")
                out.nodes.append(Node(
                    factory_id, "capability_factory", f"capability from {typed['receptor_type']}", ref.file_id, ref.path, "PARTIAL",
                    {"factory_type": typed["receptor_type"], "source_receptor_id": receptor_id,
                     "provider_type": typed.get("owner_type"),
                     "meaning": "runtime-loaded/evaluated payload may introduce capabilities not statically enumerable"}, eid_list,
                ))
                add_edge(Edge(stable_id("edge", receptor_id, factory_id, "creates_capability"), receptor_id, factory_id,
                              "creates_capability", "PARTIAL", {}, eid_list))

    # Resolve compiler-derived type references only when one project definition exists. This lets
    # inheritance/type evidence cross translation-unit boundaries without guessing through duplicate names.
    for qualified, refs in sorted(type_references.items()):
        defs = type_definitions.get(qualified, [])
        if len(defs) == 1:
            definition = defs[0]
            for ref in refs:
                add_edge(Edge(
                    stable_id("edge", ref.id, definition.id, "resolves_to"), ref.id, definition.id,
                    "resolves_to", "MAPPED", {"resolution": "unique_cpp_type_name", "qualified_name": qualified},
                    sorted(set(ref.evidence_ids + definition.evidence_ids)),
                ))
        elif len(defs) > 1:
            out.findings.append(Finding(
                stable_id("finding", "ambiguous-cpp-type", qualified, *sorted(d.id for d in defs)),
                "resolution_gap", f"Ambiguous C++ type definition: {qualified}", "PARTIAL",
                {"qualified_name": qualified, "definition_ids": sorted(d.id for d in defs),
                 "reference_ids": sorted(r.id for r in refs)},
                sorted({eid for n in defs + refs for eid in n.evidence_ids}),
            ))

    # Keyed QAction registries are semantic behavior inventories, not merely object collections.
    # A registry-defined action with no mechanically observed payload-dispatch case is preserved as
    # a PARTIAL anomaly.  It may still be wired through another route, so this is not a bug assertion.
    semantic_registry_defs: dict[str, list] = defaultdict(list)
    for n in result.nodes:
        if n.kind == "semantic_action" and (n.attributes or {}).get("registry"):
            semantic_registry_defs[n.id].append(n)
    payload_dispatch_sources = {
        e.src for e in result.edges
        if e.kind == "dispatches_to" and nodes.get(e.dst) is not None
        and nodes[e.dst].kind == "dispatch_case"
    }
    for action_id, defs in sorted(semantic_registry_defs.items()):
        if action_id in payload_dispatch_sources:
            continue
        exemplar = defs[0]
        ev_ids = sorted({eid for n in defs for eid in n.evidence_ids})
        out.findings.append(Finding(
            stable_id("finding", "semantic-action-dispatch-gap", action_id),
            "semantic_action_dispatch_gap",
            f"No payload dispatch case observed for semantic action: {exemplar.name}",
            "PARTIAL",
            {"semantic_action_id": action_id, "semantic_key": exemplar.name,
             "meaning": "registry action exists but keyed payload dispatch was not mechanically observed; alternate direct wiring may still exist"},
            ev_ids,
        ))

    # Resolve direct method-pointer / designer slot references to an actual definition only when exactly
    # one symbol definition with that qualified name exists in the scanned body.
    for qualified, refs in sorted(handlers.items()):
        defs = symbols.get(qualified, [])
        if len(defs) == 1:
            definition = defs[0]
            for ref in refs:
                if ref.id == definition.id:
                    continue
                add_edge(Edge(
                    stable_id("edge", ref.id, definition.id, "resolves_to"), ref.id, definition.id,
                    "resolves_to", "MAPPED", {"resolution": "unique_qualified_symbol", "qualified_name": qualified},
                    sorted(set(ref.evidence_ids + definition.evidence_ids)),
                ))
        elif len(defs) > 1:
            out.findings.append(Finding(
                stable_id("finding", "ambiguous-handler", qualified, *sorted(d.id for d in defs)),
                "resolution_gap", f"Ambiguous handler definition: {qualified}", "PARTIAL",
                {"qualified_name": qualified, "definition_ids": sorted(d.id for d in defs),
                 "reference_ids": sorted(r.id for r in refs)},
                sorted({eid for n in defs + refs for eid in n.evidence_ids}),
            ))
    return out
