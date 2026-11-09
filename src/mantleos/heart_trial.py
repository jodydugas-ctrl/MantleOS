"""KPP-backed, offline AppAI specimen for the small SQLite notes NEST."""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import sqlite3
import stat
import subprocess
import sys

from . import heart
from .effects import Capability, CapabilityRegistry, CheckedActionExecutor
from .kpp import satisfaction, testing, workshop
from .kpp.build import step
from .kpp.core import KPPError, digest, ingredient_catalog, read_json, validate_recipe
from .kpp.pantry import source_identity
from .transactions import atomic_bytes, body_lock, write_json


RESOURCES = Path(__file__).parent / "kpp" / "resources"
EXAMPLE = RESOURCES / "examples" / "heart-trial"
PRIMER = b"Synthetic notes Heart. Preserve notes and history. A proposal cannot authorize effects.\n"
EXPORT_PIN = "b95727486deb0c398a55f545baa8af3595e1be463d40337affc81294acf9a253"
SEED = "Keep this note across implantation."


def recipe():
    return validate_recipe(read_json(RESOURCES / "recipes" / "appai-heart-notes-trial.json"))


def command(script, db, *args):
    return [sys.executable, "-E", "-s", "-B", "-X", "utf8", str(script),
            "--db", str(db), *args]


def notes(script, db, *args):
    return subprocess.run(command(script, db, *args), check=True, capture_output=True,
                          timeout=5, encoding="utf-8").stdout


def behavior(script, db, *, export=False):
    updated = SEED + " Updated."
    checks = [
        (("create", SEED), 1), (("read", "1"), SEED),
        (("update", "1", updated), True), (("list",), [[1, updated]]),
        (("read", "1"), updated),
    ]
    for args, expected in checks:
        if json.loads(notes(script, db, *args)) != expected:
            raise ValueError(f"Native notes behavior changed: {args[0]}")
    if export and notes(script, db, "export") != f"1: {updated}\n":
        raise ValueError("Unexpected export output")


def plant(nest):
    nest = owned(nest)
    pantry = ingredient_catalog(RESOURCES)
    source_identity(RESOURCES, pantry["appai-heart"], check_external=True)
    nest.mkdir()
    source = nest / "notes.py"
    atomic_bytes(source, (EXAMPLE / "notes.py").read_bytes(), replace=False)
    behavior(source, nest / "notes.sqlite")
    rejected = subprocess.run(command(source, nest / "notes.sqlite", "export"),
                              capture_output=True, timeout=5)
    if rejected.returncode != 2 or b"text export has not been admitted" not in rejected.stderr:
        raise ValueError("Expected the baseline export capability to be absent")
    interpreter = Path(sys.executable).resolve()
    binding = {
        "recipe_sha256": digest(recipe()), "notes_sha256": heart.sha(source.read_bytes()),
        "python": str(interpreter), "python_sha256": heart.sha(interpreter.read_bytes()),
        "sqlite": sqlite3.sqlite_version, "export_sha256": EXPORT_PIN,
        "grant": ["observe-specimen", "run-reviewed-notes-checks", "stage-pinned-export"],
        "baseline": {"native_behavior": "PASS", "export": "MISSING"},
    }
    return heart.plant(nest / ".heart", PRIMER, binding)["body"]


def owned(path):
    path = Path(path).absolute()
    if ".." in path.parts:
        raise ValueError(f"Traversal in specimen path: {path.name}")
    resolved = path.resolve()
    if resolved != path and (os.name != "nt" or path.anchor != resolved.anchor
                             or len(path.parts) != len(resolved.parts)):
        raise ValueError(f"Linked specimen path: {path.name}")

    # Windows can expand a DOS short name without crossing a filesystem link.
    # Inspect every original component, including ancestors of a missing leaf.
    for part, target in zip((path, *path.parents), (resolved, *resolved.parents), strict=True):
        different_name = part != target and part.name != target.name
        try:
            info = part.lstat()
        except FileNotFoundError:
            if different_name:
                raise ValueError(f"Linked specimen path: {path.name}") from None
            continue
        if (stat.S_ISLNK(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
                or (different_name and not part.samefile(target))):
            raise ValueError(f"Linked specimen path: {path.name}")
    return resolved


def current(nest):
    nest = owned(nest)
    root = owned(nest / ".heart")
    for name in ("PRIMER.md", "ENGRAM.jsonl"):
        owned(root / name)
    history = heart.records(root)
    binding = history[0]["body"]["binding"]
    interpreter = Path(sys.executable).resolve()
    if (binding["recipe_sha256"] != digest(recipe())
            or binding["notes_sha256"] != heart.sha(owned(nest / "notes.py").read_bytes())
            or binding["python"] != str(interpreter)
            or binding["python_sha256"] != heart.sha(interpreter.read_bytes())
            or binding["sqlite"] != sqlite3.sqlite_version):
        raise ValueError("Recipe, native notes source or toolchain drift")
    return nest, root, history, binding


def resolve_capability(*, discovered, accessible, authorized, verified,
                       adapter=False, ingredient=False, confirmed_missing=False):
    """Choose a next action. Unknown or unauthorized existing tools are gaps."""
    if discovered:
        if not accessible or not authorized:
            return "BLOCKED"
        return "REUSE" if verified else "ADAPT" if adapter else "BLOCKED"
    if not confirmed_missing:
        return "BLOCKED"
    return "ACQUIRE" if ingredient else "BUILD"


def run_checks(work, candidate, contract, cases):
    suite = work / "suite"
    suite.mkdir()
    descriptions = []
    for case, obligations in cases.items():
        script = (
            "import sys\nfrom pathlib import Path\n"
            f"sys.path.insert(0, {str(Path(__file__).resolve().parents[1])!r})\n"
            "from mantleos.heart_trial_checks import check\n"
            f"check({case!r}, Path(sys.argv[1]))\n"
        )
        atomic_bytes(suite / f"{case}.py", script.encode(), replace=False)
        descriptions.append({"id": case, "script": f"{case}.py", "obligations": obligations,
                             "relationship": "Local synthetic notes NEST", "requires": ["reviewed-local"]})
    write_json(suite / "suite.json", {"schema": satisfaction.SUITE,
                                     "recipe_sha256": digest(contract), "cases": descriptions})
    context = work / "context.json"
    verifier = adapter_pin()
    write_json(context, {"capabilities": {"reviewed-local": True},
                         "adapter_sha256": verifier, "mind": "DISCONNECTED"})
    workspace = work / "kpp"
    workshop.begin(workspace, contract, RESOURCES)
    satisfaction.start(workspace, candidate, suite, context, reviewed=True)
    for _ in contract["anchors"]:
        packet = step(workspace)
        if packet["decision"] != "CONTINUE":
            raise ValueError(f"KPP stopped verification: {packet['decision']}")
        report = satisfaction.test(workspace, execute=True, reviewed=True, batch_size=32, timeout=30)
        if not report["all_passed"]:
            raise ValueError(f"KPP candidate checks failed. See {report['report_path']}")
        if adapter_pin() != verifier:
            raise ValueError("Trial verifier changed during execution")
        if set(report["verified"]) >= {a["id"] for a in contract["anchors"] if a["required"]}:
            return satisfaction.check(workspace)
    raise ValueError("KPP did not establish all required checks")


def adapter_pin():
    return digest({name: heart.sha(Path(__file__).with_name(name).read_bytes())
                   for name in ("heart_trial.py", "heart_trial_checks.py")})


def stage(nest, *, reviewed=False):
    if reviewed is not True:
        raise ValueError("Stage requires explicit review of the bundled local checks")
    nest, root, _, _ = current(nest)
    with body_lock(root / "stage-worker"):
        return stage_candidate(nest)


def stage_candidate(nest):
    from .scan.scanner import scan, verify_report

    nest, root, _, binding = current(nest)
    work = owned(root / "construction")
    work.mkdir()
    candidate = work / "candidate"
    candidate.mkdir()
    atomic_bytes(candidate / "notes.py", (nest / "notes.py").read_bytes(), replace=False)
    if owned(nest / "notes_export.py").exists():
        raise ValueError("Export is already present")
    observation = verify_report(scan(candidate, work / "scan", max_files=8, max_seconds=5))
    if (not observation["graph"]["scope"]["inventory_exhausted_within_exclusions"]
            or satisfaction.inventory(candidate) != {"notes.py": binding["notes_sha256"]}):
        raise ValueError("Incomplete or changed baseline")
    pantry = ingredient_catalog(RESOURCES)
    label = source_identity(RESOURCES, pantry["heart-notes-export"], check_external=True)
    raw = (EXAMPLE / "notes_export.py").read_bytes()
    if label["integrity"] != "PIN_MATCH" or heart.sha(raw) != binding["export_sha256"]:
        raise ValueError("Pinned Pantry export changed")
    abilities = {
        "notes-storage": {"discovered": True, "accessible": True, "authorized": True,
                          "verified": binding["baseline"]["native_behavior"] == "PASS"},
        "text-export": {"discovered": False, "accessible": False, "authorized": False,
                        "verified": False, "ingredient": True, "confirmed_missing": True},
        "other-host-tools": {"discovered": False, "accessible": None, "authorized": False,
                             "verified": False},
    }
    resolutions = {name: resolve_capability(**ability) for name, ability in abilities.items()}
    discovery = {"abilities": abilities, "resolutions": resolutions,
                 "scan_sha256": observation["graph_digest"], "ingredient": label,
                 "scope": "Pinned notes source and planted Python/SQLite tools"}
    write_json(work / "discovery.json", discovery)
    registry = CapabilityRegistry()

    def stage_export(arguments):
        if arguments:
            raise ValueError("The export staging operation accepts no arguments")
        atomic_bytes(candidate / "notes_export.py", raw, replace=False)
        return heart.sha((candidate / "notes_export.py").read_bytes())

    registry.register(Capability("stage-pinned-export", "local-candidate", "operator-review",
                                 "heart-notes-export", stage_export,
                                 lambda result: result == binding["export_sha256"]))
    checked = CheckedActionExecutor(registry, lambda authority, name: name in binding["grant"])
    result = checked.execute("stage-pinned-export", {}, request_id="notes-export")
    if result["stage"] != "VERIFIED":
        raise ValueError("Checked export staging failed")
    contract = deepcopy(recipe())
    contract["id"] = "appai-heart-export-candidate"
    contract.pop("transformation", None)
    contract.pop("anchor_design", None)
    contract["anchors"] = [{"id": "export-candidate", "statement": "Add export and preserve native notes behavior",
                            "test": "Exercise native notes commands and deterministic export",
                            "required": True, "depth": 1, "depends": []}]
    report = run_checks(work, candidate, contract, {"notes": ["export-candidate"]})
    with body_lock(root):
        _, _, history, _ = current(nest)
        receipt = {"report_sha256": digest(report["report"]), "discovery_sha256": digest(discovery),
                   "adapter_sha256": adapter_pin(), "checked_effect": result}
        event = heart.append(root, "heart.candidate", receipt, history)
    return {"status": "AWAITING_EXPORT_APPROVAL", "review": event["sha256"], **receipt}


def latest(history, *kinds):
    return next((event for event in reversed(history) if event["type"] in kinds), None)


def candidate_review(root, history, binding):
    event = latest(history, "heart.candidate")
    if not event:
        raise ValueError("No reviewed candidate evidence")
    work = owned(root / "construction")
    proof = satisfaction.check(owned(work / "kpp"))
    discovery = read_json(owned(work / "discovery.json"))
    if (event["body"]["adapter_sha256"] != adapter_pin()
            or event["body"]["report_sha256"] != digest(proof["report"])
            or event["body"]["discovery_sha256"] != digest(discovery)
            or proof["report"]["candidate"] != {"notes.py": binding["notes_sha256"],
                                                "notes_export.py": binding["export_sha256"]}):
        raise ValueError("Candidate evidence is stale")
    return event, owned(work / "candidate" / "notes_export.py"), discovery


def active_export(nest, binding):
    path = owned(nest / "notes_export.py")
    if not path.exists():
        return False
    if heart.sha(path.read_bytes()) != binding["export_sha256"]:
        raise ValueError("Unexpected active export source")
    return True


def edit_export(nest, approval, *, remove=False):
    if not approval:
        raise ValueError("Explicit operator review hash required")
    with body_lock(owned(Path(nest) / ".heart")):
        nest, root, history, binding = current(nest)
        event, candidate, _ = candidate_review(root, history, binding)
        prior = latest(history, "heart.export-intent", "heart.export-state")
        if prior and prior["type"] == "heart.export-intent":
            raise ValueError("Interrupted export change. Run recover first")
        expected = prior["sha256"] if remove and prior else event["sha256"]
        if approval != expected:
            raise ValueError("Operator approval does not match current review")
        if active_export(nest, binding) != remove:
            raise ValueError("Export is already in the requested state")
        raw = candidate.read_bytes()
        if heart.sha(raw) != binding["export_sha256"]:
            raise ValueError("Candidate source changed")
        intent = heart.append(root, "heart.export-intent",
                              {"enable": not remove, "review": approval}, history)
        target = owned(nest / "notes_export.py")
        if remove:
            target.unlink()
        else:
            atomic_bytes(target, raw, replace=False)
        outcome = heart.append(root, "heart.export-state",
                               {"enabled": active_export(nest, binding), "intent": intent["sha256"]},
                               [intent])
        return {"enabled": not remove, "change": outcome["sha256"]}


def recover(nest):
    root = owned(Path(nest) / ".heart")
    with body_lock(root / "stage-worker"), body_lock(root):
        nest, root, history, binding = current(nest)
        change = latest(history, "heart.export-intent", "heart.export-state")
        if change and change["type"] == "heart.export-intent":
            enabled = active_export(nest, binding)
            event = heart.append(root, "heart.export-state", {"enabled": enabled,
                                 "intent": change["sha256"], "reconciled": True}, history)
            return {"status": "RECONCILED", "enabled": enabled, "change": event["sha256"]}
        work = owned(root / "construction")
        if work.exists() and not latest(history, "heart.candidate"):
            from uuid import uuid4
            retained = work.with_name(f"interrupted-construction-{uuid4().hex}")
            work.rename(retained)
            heart.append(root, "heart.construction-reconciled",
                         {"retained": retained.name, "admitted": False}, history)
            return {"status": "STAGING_RETAINED", "retained": retained.name}
        return {"status": "NO_PENDING_EXPORT_CHANGE"}


CASES = {
    "notes": ["host-identity", "host-preservation", "body-independence"],
    "rhythm": ["first-heartbeat", "heartbeat-rhythm", "primer-and-continuity",
               "body-cascade", "heartbeat-recovery"],
    "construction": ["nest-discovery", "reuse-before-build", "bounded-construction"],
    "assessment": ["time-sliced-mind"],
    "admission": ["explicit-birth"],
}


def cadence(history):
    first, *rest = heart.beats(history)
    natural = next((beat for beat in rest if beat["kind"] == "natural"), None)
    if (natural is None or first["kind"] != "initial" or first["sequence"] != 1
            or first["next_due"] != first["at"] + heart.INTERVAL
            or natural["at"] < first["next_due"]
            or natural["observed_wall"] < first["next_due"] - 0.25
            or natural["next_due"] != first["next_due"] + heart.INTERVAL
            or first["mind"] != heart.ABSENT or natural["mind"] != heart.ABSENT):
        raise ValueError("The first natural beat with MIND absent has not been evidenced")
    return {"initial": first, "natural": natural, "elapsed": natural["at"] - first["at"]}


def qualify(nest, *, reviewed=False):
    if reviewed is not True:
        raise ValueError("Qualification requires explicit review of the bundled local checks")
    nest, root, history, binding = current(nest)
    change = latest(history, "heart.export-intent", "heart.export-state")
    if not change or change["type"] != "heart.export-state" or not change["body"]["enabled"]:
        raise ValueError("Export integration is awaiting review or recovery")
    event, export, discovery = candidate_review(root, history, binding)
    if not active_export(nest, binding):
        raise ValueError("The approved export is missing")
    timing = cadence(history)
    work = owned(root / "qualification" / change["sha256"])
    work.mkdir(parents=True)
    candidate = work / "candidate"
    candidate.mkdir()
    for source in (nest / "notes.py", export):
        atomic_bytes(candidate / source.name, source.read_bytes(), replace=False)
    write_json(candidate / "facts.json", {"cadence": timing, "discovery": discovery,
                                         "construction": event["body"], "binding": binding,
                                         "mind": "DISCONNECTED"})
    report = run_checks(work, candidate, recipe(), CASES)
    with body_lock(root):
        _, _, history, _ = current(nest)
        if latest(history, "heart.export-intent", "heart.export-state") != change:
            raise ValueError("Export changed during qualification")
        if not active_export(nest, binding):
            raise ValueError("Export is no longer active")
        evidence = heart.append(root, "heart.qualified", {
            "report_sha256": digest(report["report"]), "adapter_sha256": adapter_pin(),
            "change": change["sha256"], "elapsed_seconds": timing["elapsed"],
            "obligations": report["anchors"],
        }, history)
    return {"status": "READY_FOR_BIRTH", "review": evidence["sha256"], **evidence["body"]}


def ready(nest, root, history, binding):
    qualification = latest(history, "heart.qualified")
    change = latest(history, "heart.export-intent", "heart.export-state")
    if (not qualification or not change or change["sha256"] != qualification["body"]["change"]
            or not active_export(nest, binding) or qualification["body"]["adapter_sha256"] != adapter_pin()):
        raise ValueError("No current qualification for the active BODY")
    candidate_review(root, history, binding)
    proof = satisfaction.check(owned(root / "qualification" / change["sha256"] / "kpp"))
    if (qualification["body"]["report_sha256"] != digest(proof["report"])
            or set(proof["anchors"]) != {a["id"] for a in recipe()["anchors"] if a["required"]}):
        raise ValueError("Qualification is stale or incomplete")
    return qualification


def birth(nest, approval, baker):
    if not approval or not baker or not baker.strip() or len(baker) > 120:
        raise ValueError("Explicit Baker name and qualification review hash required")
    with body_lock(owned(Path(nest) / ".heart")):
        nest, root, history, binding = current(nest)
        qualification = ready(nest, root, history, binding)
        if approval != qualification["sha256"]:
            raise ValueError("Baker decision does not match the current qualification")
        if latest(history, "heart.born"):
            raise ValueError("An explicit birth already exists in this Heart's history")
        work = owned(root / "qualification" / qualification["body"]["change"])
        workspace = owned(work / "kpp")
        _, state = workshop.load(workspace)
        if state["phase"] == "BUILDING":
            report = owned(workspace / "artifacts" / "satisfaction" /
                           (qualification["body"]["report_sha256"] + ".json"))
            testing.accept_tested(workspace, report, work / "candidate", work / "suite", baker)
            completion = workshop.finish(workspace)
        else:
            completion = read_json(owned(workspace / "completion-receipt.json"))
            if {entry["baker"] for entry in completion["accepted"].values()} != {baker}:
                raise ValueError("Interrupted birth has a different recorded Baker")
        receipt = heart.append(root, "heart.born", {"review": approval, "baker": baker,
                               "kpp_completion_sha256": digest(completion)}, history)
        return {"status": "BORN", "receipt": receipt["sha256"]}


def status(nest):
    nest, root, history, binding = current(nest)
    initial, *rest = heart.beats(history)
    result = {"status": "DEVELOPING", "identity": initial["identity"],
              "beat": (rest or [initial])[-1], "mind_route": "DISCONNECTED"}
    change = latest(history, "heart.export-intent", "heart.export-state")
    if change and change["type"] == "heart.export-intent":
        return {**result, "status": "BLOCKED", "reason": "Interrupted export change. Run recover"}
    if latest(history, "heart.qualified"):
        try:
            review = ready(nest, root, history, binding)
        except (OSError, ValueError) as error:
            return {**result, "status": "BLOCKED", "reason": str(error)}
        born = latest(history, "heart.born")
        return {**result, "status": "BORN" if born else "READY_FOR_BIRTH", "review": review["sha256"]}
    if latest(history, "heart.candidate"):
        try:
            event, _, discovery = candidate_review(root, history, binding)
        except (OSError, ValueError) as error:
            return {**result, "status": "BLOCKED", "reason": str(error)}
        return {**result, "status": "DEVELOPING" if active_export(nest, binding) else "AWAITING_EXPORT_APPROVAL",
                "candidate_review": event["sha256"], "capabilities": discovery["resolutions"]}
    if (root / "construction").exists():
        return {**result, "status": "BLOCKED", "reason": "Staging has no passing receipt. Inspect retained work"}
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(prog="mantleos heart", description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    for name in ("plant", "run", "wake", "stage", "status", "integrate", "rollback",
                 "qualify", "recover", "birth"):
        command_parser = commands.add_parser(name)
        command_parser.add_argument("nest", type=Path)
        if name in {"stage", "qualify"}:
            command_parser.add_argument("--reviewed", action="store_true")
        if name in {"integrate", "rollback", "birth"}:
            command_parser.add_argument("--approve", required=True)
        if name == "birth":
            command_parser.add_argument("--baker", required=True)
        if name == "wake":
            command_parser.add_argument("reason")
        if name == "run":
            command_parser.add_argument("--natural-beats", type=int)
            command_parser.add_argument("--stage-reviewed", action="store_true")
    args = parser.parse_args(argv)
    try:
        match args.operation:
            case "plant":
                result = plant(args.nest)
            case "run":
                nest, root, _, _ = current(args.nest)
                if args.natural_beats is not None and args.natural_beats < 1:
                    parser.error("--natural-beats must be positive")
                work = ([sys.executable, "-m", "mantleos", "heart", "stage", str(nest), "--reviewed"]
                        if args.stage_reviewed else None)
                heart.run(root, natural_beats=args.natural_beats, work=work)
                return 0
            case "wake":
                result = heart.wake(current(args.nest)[1], args.reason)
            case "stage":
                result = stage(args.nest, reviewed=args.reviewed)
            case "status":
                result = status(args.nest)
            case "integrate" | "rollback":
                result = edit_export(args.nest, args.approve, remove=args.operation == "rollback")
            case "qualify":
                result = qualify(args.nest, reviewed=args.reviewed)
            case "recover":
                result = recover(args.nest)
            case "birth":
                result = birth(args.nest, args.approve, args.baker)
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, KPPError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
