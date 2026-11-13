"""Fidelity 9 — WH-BLUEPRINT-GATE (WhiteHole).

A *build-time*, fail-closed conformance gate for the cumulative Anchor blueprint.
This is NOT a security sandbox, formal AnchorForge review, or KPP satisfaction.
It detects defined kinds of architectural drift before a coding agent presents
its work for review. It has no authority to dispatch editor commands and holds
no runtime document state.
"""
from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
import json
import re
from pathlib import Path
import shutil
import subprocess
import sys


@dataclass(frozen=True)
class BlueprintReport:
    valid: bool
    anchor_count: int
    obligation_count: int
    preserved_test_count: int
    violations: tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "gate": "WH-BLUEPRINT-GATE",
            "valid": self.valid,
            "anchor_count": self.anchor_count,
            "obligation_count": self.obligation_count,
            "preserved_test_count": self.preserved_test_count,
            "violations": list(self.violations),
            "scope": "static architecture and declared evidence only; not formal proof",
        }


class WhiteHoleBlueprintGate:
    """WhiteHole gate for *candidate build* contracts, not user intents.

    The blueprint draft is the single source for responsibilities, flows,
    state owners, effects and obligations. `blueprint-manifest.json` maps these
    roles to source/tests and declares additional source-boundary invariants.
    A coding agent must keep both consistent; it cannot claim Baker acceptance.
    """

    anchor_id = "WH-BLUEPRINT-GATE"
    canonical_type = "WhiteHole"

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    @staticmethod
    def _parse_json(path: Path, errors: list[str]) -> dict:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if type(value) is not dict:
                raise ValueError("top level must be an object")
            return value
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(f"cannot read {path.name}: {exc}")
            return {}

    @staticmethod
    def _test_ids(tree: ast.AST, filename: str) -> set[str]:
        result: set[str] = set()
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                for method in node.body:
                    if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)) and method.name.startswith("test_"):
                        result.add(f"{filename}::{node.name}.{method.name}")
        return result

    @staticmethod
    def _declared_role(tree: ast.Module, class_name: str) -> tuple[object, object] | None:
        for node in tree.body:
            if not isinstance(node, ast.ClassDef) or node.name != class_name:
                continue
            values = {}
            for member in node.body:
                if isinstance(member, ast.Assign) and isinstance(member.value, ast.Constant):
                    for target in member.targets:
                        if isinstance(target, ast.Name) and target.id in {"anchor_id", "canonical_type"}:
                            values[target.id] = member.value.value
            return values.get("anchor_id"), values.get("canonical_type")
        return None

    @staticmethod
    def _stored_attributes(tree: ast.Module) -> set[str]:
        result: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.ctx, (ast.Store, ast.Del)):
                if isinstance(node.value, ast.Name) and node.value.id == "self":
                    result.add(node.attr)
        return result

    @staticmethod
    def _action_set(tree: ast.Module) -> set[str] | None:
        for klass in tree.body:
            if not isinstance(klass, ast.ClassDef) or klass.name != "WhiteHoleCommandGuard":
                continue
            for statement in klass.body:
                if not isinstance(statement, ast.Assign):
                    continue
                if not any(isinstance(t, ast.Name) and t.id == "supported_actions" for t in statement.targets):
                    continue
                value = statement.value
                if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "frozenset" and len(value.args) == 1:
                    value = value.args[0]
                if isinstance(value, (ast.Set, ast.List, ast.Tuple)) and all(isinstance(x, ast.Constant) and type(x.value) is str for x in value.elts):
                    return {x.value for x in value.elts}
        return None

    @staticmethod
    def _source_calls(tree: ast.Module) -> set[str]:
        result: set[str] = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Name):
                result.add(func.id)
            elif isinstance(func, ast.Attribute):
                result.add(func.attr)
                if isinstance(func.value, ast.Name):
                    result.add(f"{func.value.id}.{func.attr}")
                elif (isinstance(func.value, ast.Attribute)
                      and isinstance(func.value.value, ast.Name)
                      and func.value.value.id == "self"):
                    result.add(f"{func.value.attr}.{func.attr}")
        return result

    def evaluate(self) -> BlueprintReport:
        errors: list[str] = []
        blueprint = self._parse_json(self.root / "anchorforge-spec.json", errors)
        manifest = self._parse_json(self.root / "blueprint-manifest.json", errors)
        roles = blueprint.get("responsibilities", [])
        sources = manifest.get("sources", {})
        obligations = blueprint.get("obligations", [])
        states = blueprint.get("state", [])
        effects = blueprint.get("effects", [])
        flows = blueprint.get("flows", [])
        anchor_count = len(roles) if isinstance(roles, list) else 0
        obligation_count = len(obligations) if isinstance(obligations, list) else 0
        if not blueprint or not manifest:
            return BlueprintReport(False, anchor_count, obligation_count, 0, tuple(errors))

        if blueprint.get("schema") != "anchorforge.organ-spec/1":
            errors.append("blueprint schema must be anchorforge.organ-spec/1 (draft)")
        if manifest.get("schema") != "notepad.blueprint-manifest/1":
            errors.append("unknown blueprint-manifest schema")
        depth = blueprint.get("fidelity")
        if type(depth) is not int or depth != manifest.get("fidelity") or depth != anchor_count:
            errors.append("fidelity, manifest fidelity and Anchor count must agree")
        if anchor_count != manifest.get("minimum_anchor_count") or anchor_count < 9:
            errors.append("Anchor count must not fall below preserved Fidelity 9 count")
        if not isinstance(roles, list) or not isinstance(sources, dict):
            errors.append("responsibilities must be list and source map object")
            return BlueprintReport(False, anchor_count, obligation_count, 0, tuple(errors))

        identities = [r.get("id") for r in roles if isinstance(r, dict)]
        known = set(identities)
        if len(identities) != len(roles) or len(known) != len(identities):
            errors.append("every Anchor must have one distinct ID")
        if known != set(sources):
            errors.append("every declared Anchor must map to exactly one implementation (and vice versa)")
        allowed_types = {"BlackHole", "Neutral", "WhiteHole"}
        kinds = {}
        for role in roles:
            if not isinstance(role, dict):
                errors.append("Anchor responsibilities must be objects")
                continue
            id_, kind = role.get("id"), role.get("definition")
            kinds[id_] = kind
            if kind not in allowed_types or not isinstance(role.get("responsibility"), str) or not role["responsibility"].strip():
                errors.append(f"{id_}: missing role type or responsibility truth")
        if kinds.get(self.anchor_id) != "WhiteHole":
            errors.append("Fidelity 9 gate must exist as a WhiteHole Anchor")
        if kinds.get("WH-COMMAND-GUARD") != "WhiteHole":
            errors.append("runtime command guard role has changed")

        trees = {}
        files_used = set()
        for id_, info in sources.items():
            if not isinstance(info, dict):
                errors.append(f"{id_}: source-map item must be an object")
                continue
            module, cls = info.get("file"), info.get("class")
            if not isinstance(module, str) or Path(module).name != module or not module.endswith(".py"):
                errors.append(f"{id_}: invalid source filename")
                continue
            if module in files_used:
                errors.append(f"{id_}: multiple Anchors share a mapped source module")
            files_used.add(module)
            try:
                tree = ast.parse((self.root / module).read_text(encoding="utf-8"), filename=module)
            except (OSError, UnicodeError, SyntaxError) as exc:
                errors.append(f"{id_}: unable to parse {module}: {exc}")
                continue
            trees[id_] = tree
            actual = self._declared_role(tree, cls)
            if actual != (id_, kinds.get(id_)):
                errors.append(f"{id_}: source class {cls} does not declare matching anchor_id/canonical_type")

        owner_by_state = {}
        for state in states if isinstance(states, list) else []:
            if not isinstance(state, dict) or not isinstance(state.get("id"), str):
                errors.append("invalid declared state entry")
                continue
            s, owner = state.get("id"), state.get("owner")
            if s in owner_by_state:
                errors.append(f"duplicate state identity: {s}")
            owner_by_state[s] = owner
            if owner not in known or kinds.get(owner) != "Neutral":
                errors.append(f"state {s} must have exactly one Neutral owner")
        required_state = manifest.get("preserved_state_owners", {})
        for s, owner in required_state.items():
            if owner_by_state.get(s) != owner:
                errors.append(f"state owner drift for {s}: expected {owner}")

        for variable, expected in manifest.get("exclusive_state_attributes", {}).items():
            for id_, tree in trees.items():
                writes = variable in self._stored_attributes(tree)
                if writes and id_ != expected:
                    errors.append(f"{id_}: forbidden writer of {variable}; owner is {expected}")
            if expected in trees and variable not in self._stored_attributes(trees[expected]):
                errors.append(f"{expected}: missing declared owned state attribute {variable}")

        for i, effect in enumerate(effects if isinstance(effects, list) else []):
            if not isinstance(effect, dict):
                errors.append(f"effect {i}: not an object")
                continue
            name = effect.get("id", i)
            for key in ("requester", "guard", "executor"):
                if effect.get(key) not in known:
                    errors.append(f"effect {name}: unknown {key} Anchor")
            if effect.get("guard") != "WH-COMMAND-GUARD":
                errors.append(f"effect {name}: host effect must pass runtime command guard")
            if not str(effect.get("confirmation", "")).strip():
                errors.append(f"effect {name}: no confirmed success condition")
        preserved_effects = manifest.get("preserved_effects", {})
        seen_effects = {e.get("id"): e for e in effects if isinstance(e, dict)}
        for name, owner in preserved_effects.items():
            if seen_effects.get(name, {}).get("executor") != owner:
                errors.append(f"host effect {name} lost original executor {owner}")
        for flow in flows if isinstance(flows, list) else []:
            if not isinstance(flow, dict) or flow.get("from") not in known or flow.get("to") not in known or not str(flow.get("relationship", "")).strip():
                errors.append("flow has unknown endpoint or empty relationship")
        required_flows = manifest.get("required_flows", [])
        flow_pairs = {(f.get("from"), f.get("to")) for f in flows if isinstance(f, dict)}
        for a, b in required_flows:
            if (a, b) not in flow_pairs:
                errors.append(f"required flow missing: {a} -> {b}")

        by_id = {}
        for item in obligations if isinstance(obligations, list) else []:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                errors.append("obligations require stable string IDs")
                continue
            oid = item["id"]
            if oid in by_id:
                errors.append(f"duplicate obligation: {oid}")
            by_id[oid] = item
            if item.get("required") is not True or not str(item.get("statement", "")).strip() or not str(item.get("test", "")).strip():
                errors.append(f"obligation {oid} must be mandatory, testable and stated")
            if type(item.get("depth")) is not int or type(depth) is not int or not 1 <= item["depth"] <= depth:
                errors.append(f"obligation {oid} has invalid fidelity depth")
            anchors = item.get("design_anchors", [])
            if not anchors or any(a not in known for a in anchors):
                errors.append(f"obligation {oid} has missing/unknown Anchor coverage")
        for oid in manifest.get("preserved_obligation_ids", []):
            if oid not in by_id:
                errors.append(f"preserved obligation removed: {oid}")
        for id_ in known:
            if id_ not in {a for o in by_id.values() for a in o.get("design_anchors", [])}:
                errors.append(f"Anchor {id_} is not covered by any mandatory obligation")
        for oid, item in by_id.items():
            for prerequisite in item.get("depends", []):
                if prerequisite not in by_id or prerequisite == oid:
                    errors.append(f"obligation {oid}: invalid dependency {prerequisite}")
        pending, resolved = set(by_id), set()
        while pending:
            ready = {o for o in pending if all(dep in resolved for dep in by_id[o].get("depends", []))}
            if not ready:
                errors.append("obligation dependency cycle or missing dependency")
                break
            resolved.update(ready)
            pending -= ready

        # Concrete source-to-boundary checks. This is drift detection, not a
        # proof that a hostile coder cannot hide a forbidden operation.
        sensitive_calls = {
            "open": {"N-FILE-SESSION"},
            "os.replace": {"N-FILE-SESSION"},
            "NamedTemporaryFile": {"N-FILE-SESSION"},
            "clipboard_get": {"N-EDITOR-SURFACE"},
            "clipboard_clear": {"N-EDITOR-SURFACE"},
            "clipboard_append": {"N-EDITOR-SURFACE"},
        }
        for id_, tree in trees.items():
            calls = self._source_calls(tree)
            for name, permitted in sensitive_calls.items():
                if name in calls and id_ not in permitted:
                    errors.append(f"{id_}: forbidden host call {name}")
            for item in ast.walk(tree):
                if isinstance(item, ast.Import):
                    names = [n.name.split(".")[0] for n in item.names]
                elif isinstance(item, ast.ImportFrom):
                    names = [str(item.module).split(".")[0]]
                else:
                    continue
                for name in names:
                    if name in {"socket", "requests", "urllib", "http", "ftplib"}:
                        errors.append(f"{id_}: undeclared network module imported: {name}")
                    if name == "subprocess" and id_ != self.anchor_id:
                        errors.append(f"{id_}: subprocess use outside offline gate")
        if "WH-COMMAND-GUARD" in trees:
            actions = self._action_set(trees["WH-COMMAND-GUARD"])
            if actions != set(manifest.get("runtime_actions", [])):
                errors.append("runtime command allowlist drift: review all authorized actions")
        if "N-EDITOR-SURFACE" in trees:
            surface = trees["N-EDITOR-SURFACE"]
            calls = self._source_calls(surface)
            if "BlackHoleEditorInput.receive" not in calls or "guard.execute" not in calls:
                errors.append("surface no longer sends captured intent through WH guard")

        found_tests: set[str] = set()
        for filename in sorted(self.root.glob("test_*.py")):
            try:
                tree = ast.parse(filename.read_text(encoding="utf-8"), filename=filename.name)
            except (OSError, UnicodeError, SyntaxError) as exc:
                errors.append(f"cannot parse test {filename.name}: {exc}")
                continue
            found_tests |= self._test_ids(tree, filename.name)
        preserved_tests = set(manifest.get("preserved_test_ids", []))
        if len(preserved_tests) != len(manifest.get("preserved_test_ids", [])):
            errors.append("preservation test registry contains duplicates")
        missing = preserved_tests - found_tests
        if missing:
            errors.append(f"{len(missing)} inherited test method(s) removed or renamed: " + ", ".join(sorted(missing)[:5]))
        if not any(s.startswith("test_notepad_blueprint_gate.py::") for s in found_tests):
            errors.append("new blueprint gate has no discoverable tests")
        return BlueprintReport(not errors, anchor_count, obligation_count, len(preserved_tests), tuple(errors))


def _suite_is_complete(output: str, minimum_tests: int) -> bool:
    """Fail closed on no tests or skips: unittest exits 0 with skipped GUI tests."""
    match = re.search(r"Ran (\d+) tests? in ", output)
    if match is None or int(match.group(1)) < minimum_tests:
        return False
    skipped = re.search(r"skipped=(\d+)", output)
    return skipped is None or int(skipped.group(1)) == 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate candidate Notepad against the cumulative Anchor blueprint")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="Project root with Anchor spec and code")
    parser.add_argument("--verify", action="store_true", help="Also execute full discovered Python regression suite")
    args = parser.parse_args(argv)
    root = Path(args.root)
    report = WhiteHoleBlueprintGate(root).evaluate()
    print(json.dumps(report.as_dict(), indent=2))
    if not report.valid:
        return 1
    if args.verify:
        cmd = [sys.executable, "-m", "unittest", "discover", "-v", "-p", "test_*.py"]
        # Prefer a fresh virtual display on Linux even when DISPLAY is set:
        # DISPLAY may be stale or unreachable, causing all Tk tests to skip.
        if sys.platform.startswith("linux") and shutil.which("xvfb-run"):
            cmd = ["xvfb-run", "-a", *cmd]
        print("Running cumulative Python test suite:", " ".join(cmd), flush=True)
        result = subprocess.run(cmd, cwd=root, check=False, capture_output=True, text=True)
        print(result.stdout, end="", flush=True)
        print(result.stderr, end="", file=sys.stderr, flush=True)
        if result.returncode != 0:
            return result.returncode
        output = result.stdout + "\n" + result.stderr
        if not _suite_is_complete(output, report.preserved_test_count + 1):
            print("REJECTED: test discovery incomplete or one or more tests skipped; full cumulative verification not established.", file=sys.stderr)
            return 1
        print("VERIFIED: Python suite executed in full with zero skipped tests.")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
