"""Contract-first conformance for existing pinned profiles; never auto-promote."""
import copy
from functools import wraps
from datetime import datetime, timezone
from pathlib import Path
import platform
import re
import sys
import time
import uuid
from . import anchor_language as ac
from .anchor_blueprint import draft_from_scan, validate_blueprint
from .native_anchor import qualify_program, MAX_SOURCE_BYTES
from .scan.common import ScanError, canonical, digest, sha
from .scan.evidence import context, timestamp, verify_evidence
from .scan.providers import HEX, fields

CATEGORIES = {"positive", "negative", "malformed", "limit", "regression"}
AUTHORITY = "NONE_FROM_CONTRACT_SOURCE_OR_CONFORMANCE"
PROFILES = {
    "EMIT_TEXT/0.2": {"native_admission": True, "inputs": "NONE", "state": "NONE"},
    "NOTEPAD_LLM/1.3": {"native_admission": False, "inputs": "COMMAND_SEQUENCE", "state": "DISPOSABLE_IN_MEMORY"}
}


def contract_errors(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        try: return function(*args, **kwargs)
        except ScanError: raise
        except (KeyError, TypeError, AttributeError, ValueError, IndexError, RecursionError, OSError) as error:
            raise ScanError("Malformed or unavailable Anchor qualification contract: " + str(error)[:300]) from error
    return wrapped


def now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalized_source(source):
    return source.replace("\r\n", "\n").replace("\r", "\n")


def profile_catalog():
    ac.verify_source_pins()
    return {"schema": "anchor.profile-contracts/1", "profiles": copy.deepcopy(PROFILES),
            "source_pins_sha256": sha((ac.source_directory() / "SOURCE-PINS.json").read_bytes()),
            "harness_sha256": digest([sha(Path(__file__).read_bytes()), sha(Path(ac.__file__).read_bytes()),
                                      sha((Path(__file__).parent / "native_anchor.py").read_bytes())]),
            "limitations": ["No new profiles/opcodes are admitted by this harness.",
                            "NOTEPAD_LLM/1.3 conformance remains experimental and does not widen native program admission."]}


@contract_errors
def freeze_contract(document):
    fields(document, ("schema", "id", "profile", "purpose", "oracle", "cases", "created_at"), ("sha256",))
    if document["schema"] != "anchor.behavior-contract/1" or document["profile"] not in PROFILES:
        raise ScanError("Unsupported behavior contract/profile")
    if not isinstance(document["id"], str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", document["id"]):
        raise ScanError("Invalid behavior contract identity")
    if not isinstance(document["purpose"], str) or not 1 <= len(document["purpose"]) <= 2000:
        raise ScanError("Behavior contract purpose missing")
    timestamp(document["created_at"])
    fields(document["oracle"], ("kind", "owner", "reference"))
    if document["oracle"]["kind"] != "FIXED_LITERAL_FIXTURES" or any(not isinstance(document["oracle"][key], str) or not 1 <= len(document["oracle"][key]) <= 1000 for key in ("owner", "reference")):
        raise ScanError("Only independently preselected literal fixtures are admitted as an oracle")
    cases = document["cases"]
    if not isinstance(cases, list) or not 5 <= len(cases) <= 64:
        raise ScanError("Use 5-64 conformance fixtures covering every required category")
    ids, categories, fixture_bytes = set(), set(), 0
    candidate_positive = False
    for case in cases:
        fields(case, ("id", "category", "program", "fixture_source", "input", "expect"))
        if not isinstance(case["id"], str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", case["id"]) or case["id"] in ids:
            raise ScanError("Invalid or duplicate conformance case identity")
        ids.add(case["id"])
        if case["category"] not in CATEGORIES or case["program"] not in ("CANDIDATE", "FIXTURE"):
            raise ScanError("Unknown fixture category or program role")
        categories.add(case["category"])
        fixture = case["fixture_source"]
        if case["program"] == "CANDIDATE":
            if fixture is not None: raise ScanError("Candidate fixtures must not substitute another program")
        else:
            if not isinstance(fixture, str) or not 1 <= len(fixture.encode()) <= 131072:
                raise ScanError("Fixture source byte budget exceeded")
            fixture_bytes += len(fixture.encode())
        inputs = case["input"]
        if document["profile"].startswith("EMIT_TEXT/"):
            if inputs is not None and not isinstance(inputs, dict): raise ScanError("EMIT_TEXT command rejection fixtures must use a JSON object")
        elif not isinstance(inputs, list) or not 1 <= len(inputs) <= 32:
            raise ScanError("Notepad fixtures need 1-32 explicit commands")
        expected = case["expect"]
        fields(expected, ("outcome", "observations", "error_code"))
        if expected["outcome"] not in ("RETURN", "REJECT") or not isinstance(expected["observations"], dict) or len(expected["observations"]) > 100:
            raise ScanError("Invalid expected conformance outcome")
        if expected["outcome"] == "REJECT":
            if expected["observations"] or expected["error_code"] not in ("SOURCE_LIMIT", "INVALID_PROGRAM", "INVALID_COMMAND", "PROFILE_MISMATCH"):
                raise ScanError("Rejected fixture must specify a stable harness boundary error")
        else:
            if expected["error_code"] is not None or not expected["observations"]:
                raise ScanError("Returned fixture must specify independent expected observations")
            if document["profile"].startswith("EMIT_TEXT/"):
                if set(expected["observations"]) != {"/stdout", "/effect_claim"} or not isinstance(expected["observations"]["/stdout"], str) or expected["observations"]["/effect_claim"] != "NONE":
                    raise ScanError("EMIT_TEXT oracle must fix exact stdout and no-effect result")
            else:
                if not all(isinstance(path, str) and re.fullmatch(r"/(state/[A-Za-z0-9_~/]+|steps/[0-9]+/(result|effect_claim|state/[A-Za-z0-9_~/]+))", path) for path in expected["observations"]):
                    raise ScanError("Notepad observations must be explicit state/result/effect paths")
                if any(f"/steps/{index}/result" not in expected["observations"] or f"/steps/{index}/effect_claim" not in expected["observations"] for index in range(len(inputs))):
                    raise ScanError("Every state transition needs a fixed result and effect expectation")
                if not any(path.startswith("/state/") for path in expected["observations"]):
                    raise ScanError("Stateful fixture must fix a final state observation")
            if case["program"] == "CANDIDATE" and case["category"] == "positive": candidate_positive = True
    if categories != CATEGORIES or not candidate_positive:
        raise ScanError("Conformance suite needs positive candidate plus negative, malformed, limit and regression categories")
    if fixture_bytes > 2_000_000 or len(canonical(document).encode()) > 4_000_000:
        raise ScanError("Conformance contract byte budget exceeded")
    body = copy.deepcopy({key: value for key, value in document.items() if key != "sha256"})
    fingerprint = digest(body)
    if "sha256" in document and document["sha256"] != fingerprint:
        raise ScanError("Behavior contract identity mismatch")
    return dict(body, sha256=fingerprint)


@contract_errors
def specification(report, source_root, receipts, contract, *, blueprint_id, name, purpose, expected_contract_sha256,
                  runtime_receipts=None, authorized_runs=None):
    frozen = freeze_contract(contract)
    if frozen["sha256"] != expected_contract_sha256:
        raise ScanError("Behavior oracle is not independently pinned")
    if not isinstance(receipts, list) or not 1 <= len(receipts) <= 64 or len({item["id"] for item in receipts}) != len(receipts):
        raise ScanError("Specification requires 1-64 distinct verified evidence envelopes")
    verdicts = [verify_evidence(item, report, source_root, runtime_receipts=runtime_receipts, authorized_runs=authorized_runs) for item in receipts]
    draft = draft_from_scan(report, blueprint_id=blueprint_id, name=name, purpose=purpose)
    citations = []
    for receipt in receipts:
        for span in receipt["source_spans"]:
            citation = {"path": span["path"], "sha256": span["source_sha256"], "line_start": span["line_start"],
                        "line_end": span["line_end"], "node_id": span["node_id"], "receipt_id": receipt["id"],
                        "scope": "SOURCE_REFERENCE_ONLY; oracle expectation is operator-selected"}
            if citation not in citations: citations.append(citation)
    draft["acceptance_contracts"] = [{"id": "fixture." + case["id"],
        "statement": "Operator-selected " + case["category"] + " fixture " + case["id"] + "; actual behavior remains unverified pending conformance.",
        "anchors": [], "evidence": copy.deepcopy(citations[:100]),
        "test_hint": "anchor.behavior-contract/1 " + frozen["sha256"] + " case " + case["id"]} for case in frozen["cases"]]
    validate_blueprint(draft)
    body = {"schema": "anchor.specification/1", "status": "CANDIDATE_ONLY", "blueprint": draft,
            "context": context(report), "evidence": [{"id": value["evidence_id"], "class": value["evidence_class"]} for value in verdicts],
            "contract_sha256": frozen["sha256"], "behavior_contract": frozen, "profile": frozen["profile"],
            "unknowns": ["Static source references do not prove behavioral semantics.",
                         "Expected fixtures cover only the independently declared contract.",
                         "Independent semantic critique and human program review remain required."],
            "authority": AUTHORITY, "requires_human_review": True}
    if len(canonical(body).encode()) > 8_000_000: raise ScanError("Specification byte budget exceeded")
    return dict(body, sha256=digest(body))


@contract_errors
def verify_specification(value, report, source_root, receipts, contract, *, expected_contract_sha256,
                         runtime_receipts=None, authorized_runs=None):
    if not isinstance(value, dict) or not isinstance(value.get("blueprint"), dict):
        raise ScanError("Specification Blueprint missing")
    draft = value["blueprint"]
    expected = specification(report, source_root, receipts, contract, blueprint_id=draft["id"], name=draft["name"], purpose=draft["purpose"],
                             expected_contract_sha256=expected_contract_sha256, runtime_receipts=runtime_receipts, authorized_runs=authorized_runs)
    if value != expected: raise ScanError("Specification evidence/source/oracle binding mismatch")
    return {"schema": "anchor.specification-verification/1", "result": "PASS", "status": "CANDIDATE_ONLY", "promotion_authority": False}


def pointer(value, path):
    try:
        for part in path[1:].split("/"):
            key = part.replace("~1", "/").replace("~0", "~")
            value = value[int(key)] if isinstance(value, list) else value[key]
        return value
    except (KeyError, ValueError, IndexError, TypeError) as error:
        raise ScanError("Expected observation path is absent: " + path) from error


def run_fixture(source, profile, inputs, deadline):
    if time.monotonic() >= deadline: raise ScanError("Conformance total time budget exceeded")
    ac.verify_source_pins()
    if len(source.encode()) > MAX_SOURCE_BYTES:
        return {"outcome": "REJECT", "error_code": "SOURCE_LIMIT", "value": None}
    # Preserve the original UTF-8 digest while matching existing text-mode
    # Windows readers. Profile primers are compared after universal newlines.
    source = normalized_source(source)
    lines = source.splitlines()
    if len(lines) >= 2 and lines[1].split() and lines[1].split()[-1] != profile:
        return {"outcome": "REJECT", "error_code": "PROFILE_MISMATCH", "value": None}
    if profile.startswith("EMIT_TEXT/"):
        try:
            qualify_program(source, profile=profile)
        except ValueError:
            return {"outcome": "REJECT", "error_code": "INVALID_PROGRAM", "value": None}
        if inputs is not None:
            return {"outcome": "REJECT", "error_code": "INVALID_COMMAND", "value": None}
        value = ac.execute_blueprint(source)
        return {"outcome": "RETURN", "error_code": None, "value": {"stdout": value["stdout"], "effect_claim": value["effect_claim"]}}
    from .anchor_engine.tools.anchor_notepad import load_blueprint, Session
    try:
        ac.inspect_blueprint(source)
        _, seed = load_blueprint(source)
    except ValueError:
        return {"outcome": "REJECT", "error_code": "INVALID_PROGRAM", "value": None}
    session = Session(seed)  # NoExportHost; no host callback or clock is supplied.
    results = []
    for command in inputs:
        if time.monotonic() >= deadline: raise ScanError("Conformance total time budget exceeded")
        results.append(session.step(command))
        if len(canonical(results).encode()) > 8_000_000:
            raise ScanError("State transition capture budget exceeded")
    return {"outcome": "RETURN", "error_code": None, "value": {"steps": results, "state": session.state}}


@contract_errors
def qualify(candidate, contract, *, expected_contract_sha256, permit_execution=False, specification_sha256=None, max_seconds=30):
    if permit_execution is not True:
        raise ScanError("Anchor conformance needs explicit bounded-profile execution permission")
    if not isinstance(candidate, str) or not 1 <= len(candidate.encode()) <= MAX_SOURCE_BYTES:
        raise ScanError("Candidate source byte budget exceeded")
    if type(max_seconds) is not int or not 1 <= max_seconds <= 30:
        raise ScanError("Conformance time budget must be 1-30 seconds")
    frozen = freeze_contract(contract)
    if frozen["sha256"] != expected_contract_sha256:
        raise ScanError("Preselected oracle contract digest mismatch")
    if specification_sha256 is not None and (not isinstance(specification_sha256, str) or not HEX.fullmatch(specification_sha256)):
        raise ScanError("Invalid specification binding")
    catalog = profile_catalog()  # Pin failures are infrastructure failures, never expected program errors.
    started, records, deadline = now(), [], time.monotonic() + max_seconds
    for case in frozen["cases"]:
        source = candidate if case["program"] == "CANDIDATE" else case["fixture_source"]
        actual = run_fixture(source, frozen["profile"], case["input"], deadline)
        expected = case["expect"]
        mismatches = []
        if actual["outcome"] != expected["outcome"] or actual["error_code"] != expected["error_code"]:
            mismatches.append("OUTCOME_OR_ERROR")
        if actual["outcome"] == "RETURN" and expected["outcome"] == "RETURN":
            for path, value in expected["observations"].items():
                try: observed = pointer(actual["value"], path)
                except ScanError:
                    mismatches.append(path + ":MISSING"); continue
                if canonical(observed) != canonical(value): mismatches.append(path + ":DIFFERS")
        records.append({"id": case["id"], "category": case["category"], "program": case["program"], "source_sha256": sha(source.encode()),
                        "input_sha256": digest(case["input"]), "actual": actual, "expected_sha256": digest(expected),
                        "result": "FAIL" if mismatches else "PASS", "mismatches": mismatches})
        if len(canonical(records).encode()) > 8_000_000:
            raise ScanError("Conformance result byte budget exceeded")
    if time.monotonic() >= deadline: raise ScanError("Conformance total time budget exceeded")
    ac.verify_source_pins()
    body = {"schema": "anchor.conformance/1", "status": "CONFORMANCE_PASS_REVIEW_PENDING" if all(record["result"] == "PASS" for record in records) else "CONFORMANCE_FAIL",
            "candidate_sha256": sha(candidate.encode()), "contract_sha256": frozen["sha256"], "specification_sha256": specification_sha256,
            "candidate_interpreted_sha256": sha(normalized_source(candidate).encode()), "source_normalization": "UTF8_TEXT_UNIVERSAL_NEWLINES",
            "profile": frozen["profile"], "profile_contracts_sha256": digest(catalog), "cases": records,
            "run": {"id": "qualification:" + str(uuid.uuid4()), "started_at": started, "finished_at": now(),
                    "host": platform.system(), "python": sys.version.split()[0], "permission": "EXPLICIT_BOUNDED_PROFILE_EXECUTION",
                    "host_tools": False, "engram_writes": False},
            "authority": AUTHORITY, "promotion": "NOT_PERFORMED", "requires_human_review": True,
            "scope": "Exact preselected fixtures only; no whole-project equivalence or profile widening",
            "native_profile_previously_admitted": PROFILES[frozen["profile"]]["native_admission"]}
    return dict(body, sha256=digest(body))


@contract_errors
def verify_conformance(receipt, candidate, contract, *, expected_contract_sha256):
    fields(receipt, ("schema", "status", "candidate_sha256", "contract_sha256", "specification_sha256", "profile", "profile_contracts_sha256",
                     "candidate_interpreted_sha256", "source_normalization",
                     "cases", "run", "authority", "promotion", "requires_human_review", "scope", "native_profile_previously_admitted", "sha256"))
    body = {key: value for key, value in receipt.items() if key != "sha256"}
    frozen = freeze_contract(contract)
    if receipt["schema"] != "anchor.conformance/1" or receipt["sha256"] != digest(body) or frozen["sha256"] != expected_contract_sha256 or receipt["contract_sha256"] != frozen["sha256"] or receipt["candidate_sha256"] != sha(candidate.encode()):
        raise ScanError("Conformance source/oracle/receipt identity mismatch")
    if receipt["authority"] != AUTHORITY or receipt["promotion"] != "NOT_PERFORMED" or receipt["requires_human_review"] is not True:
        raise ScanError("Conformance cannot manufacture promotion authority")
    if receipt["candidate_interpreted_sha256"] != sha(normalized_source(candidate).encode()) or receipt["source_normalization"] != "UTF8_TEXT_UNIVERSAL_NEWLINES":
        raise ScanError("Conformance text interpretation binding mismatch")
    if receipt["profile"] != frozen["profile"] or receipt["profile_contracts_sha256"] != digest(profile_catalog()):
        raise ScanError("Conformance profile contract changed")
    if receipt["specification_sha256"] is not None and (not isinstance(receipt["specification_sha256"], str) or not HEX.fullmatch(receipt["specification_sha256"])):
        raise ScanError("Conformance specification reference mismatch")
    if receipt["native_profile_previously_admitted"] is not PROFILES[frozen["profile"]]["native_admission"] or receipt["scope"] != "Exact preselected fixtures only; no whole-project equivalence or profile widening":
        raise ScanError("Conformance admission/scope claim mismatch")
    fields(receipt["run"], ("id", "started_at", "finished_at", "host", "python", "permission", "host_tools", "engram_writes"))
    run = receipt["run"]
    if not isinstance(run["id"], str) or not run["id"].startswith("qualification:"):
        raise ScanError("Qualification run identity missing")
    try: uuid.UUID(run["id"][14:])
    except ValueError as error: raise ScanError("Invalid qualification run identity") from error
    if timestamp(run["started_at"]) > timestamp(run["finished_at"]) or run["permission"] != "EXPLICIT_BOUNDED_PROFILE_EXECUTION" or run["host_tools"] is not False or run["engram_writes"] is not False:
        raise ScanError("Qualification permission/scope/time mismatch")
    if any(not isinstance(run[key], str) or not 1 <= len(run[key]) <= 200 for key in ("host", "python")):
        raise ScanError("Qualification host provenance missing")
    if not isinstance(receipt["cases"], list) or len(receipt["cases"]) != len(frozen["cases"]):
        raise ScanError("Conformance fixture coverage mismatch")
    for row, case in zip(receipt["cases"], frozen["cases"]):
        source = candidate if case["program"] == "CANDIDATE" else case["fixture_source"]
        if any(row.get(key) != value for key, value in {"id": case["id"], "category": case["category"], "program": case["program"],
                "source_sha256": sha(source.encode()), "input_sha256": digest(case["input"]), "expected_sha256": digest(case["expect"])}.items()):
            raise ScanError("Conformance fixture references changed")
        actual, expected = row.get("actual"), case["expect"]
        fields(actual, ("outcome", "error_code", "value"))
        if actual["outcome"] not in ("RETURN", "REJECT") or actual["outcome"] == "REJECT" and actual["value"] is not None:
            raise ScanError("Invalid conformance observation class")
        matches = actual["outcome"] == expected["outcome"] and actual["error_code"] == expected["error_code"]
        if matches and actual["outcome"] == "RETURN":
            try: matches = all(canonical(pointer(actual["value"], path)) == canonical(value) for path, value in expected["observations"].items())
            except ScanError: matches = False
        if row.get("result") != ("PASS" if matches else "FAIL"):
            raise ScanError("Conformance verdict contradicts its observations")
    passed = all(row["result"] == "PASS" for row in receipt["cases"])
    if receipt["status"] != ("CONFORMANCE_PASS_REVIEW_PENDING" if passed else "CONFORMANCE_FAIL"):
        raise ScanError("Conformance aggregate verdict mismatch")
    return {"schema": "anchor.conformance-verification/1", "result": "PASS", "conformance_passed": passed,
            "scope": "Receipt/reference/verdict consistency; execution authenticity requires an independent trusted run digest",
            "promotion_authority": False}


@contract_errors
def review_program(receipt, candidate, contract, review, *, expected_contract_sha256, trusted_run_sha256, trusted_review_sha256):
    verify_conformance(receipt, candidate, contract, expected_contract_sha256=expected_contract_sha256)
    fields(review, ("schema", "reviewer", "independent", "approved", "candidate_sha256", "contract_sha256", "conformance_sha256", "scope", "created_at"))
    if len(canonical(review).encode()) > 64_000: raise ScanError("Human review record byte budget exceeded")
    if digest(receipt) != trusted_run_sha256 or digest(review) != trusted_review_sha256:
        raise ScanError("Conformance run and human review need separately trusted digests")
    fields(review["reviewer"], ("id", "role"))
    if review["schema"] != "anchor.program-review/1" or review["reviewer"]["role"] != "HUMAN" or not isinstance(review["reviewer"]["id"], str) or not review["reviewer"]["id"].strip() or review["independent"] is not True or review["approved"] is not True:
        raise ScanError("Independent human review is required")
    if receipt["status"] != "CONFORMANCE_PASS_REVIEW_PENDING": raise ScanError("Failed conformance cannot be promoted")
    for key in ("candidate_sha256", "contract_sha256"):
        if review[key] != receipt[key]: raise ScanError("Human review refers to another candidate/contract")
    if review["conformance_sha256"] != receipt["sha256"] or review["scope"] != "DECLARED_CONTRACT_ONLY" or timestamp(review["created_at"]) < timestamp(receipt["run"]["finished_at"]):
        raise ScanError("Human review scope/run/time mismatch")
    if not PROFILES[receipt["profile"]]["native_admission"]:
        raise ScanError("Experimental reference profile remains outside native program admission")
    body = {"schema": "anchor.program-admission/1", "status": "REVIEWED_WITHIN_DECLARED_CONTRACT",
            "candidate_sha256": receipt["candidate_sha256"], "profile": receipt["profile"],
            "contract_sha256": receipt["contract_sha256"], "conformance_sha256": receipt["sha256"],
            "review_sha256": digest(review), "authority": "NO_HOST_EFFECT_OR_IDENTITY_AUTHORITY",
            "body_mutated": False, "whole_project_equivalence": "UNKNOWN"}
    return dict(body, sha256=digest(body))
