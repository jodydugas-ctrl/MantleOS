"""Addon-specific Stage-1 gate for the Hermes Mantle resident.

The framework's Stage-1 gate (mantle.audits.stage1) proves the Zombie Body is
sound in isolation. This gate proves the resident Body is sound *within the
Hermes host context* — addon-specific probes that the framework gate does not
cover. Together, the framework gate + this gate establish Stage-1 evidence for
Phase-2 readiness review; they do not themselves authorize MIND fusion.

Probes (all deterministic, LLM-free, network-free):

  A-01  Resident identity is "Hermes.Mantle.AppAI"
  A-02  Brain is dormant (not fused) — Phase-1 requirement
  A-03  stage1_certified is False (no prior self-certification)
  A-04  SELF seal exists and verifies under the body's genesis key
  A-05  All nine organs present with contracts (fail-open)
  A-06  Observer hooks are fail-open (callbacks return None)
  A-07  No raw payloads in senses band (redaction boundary)
  A-08  Heartbeat runs without network/model/subprocess
  A-09  Vendored runtime is isolated from preloaded global mantle
  A-10  Storage boundary: owner-only permissions, no symlinks
  A-11  Action Execution Proofs are BODY-authored
  A-12  Config mind_enabled is False (Phase-1 only)
  A-13  Dual-flush installed (checkpoint + atexit)
  A-14  Reconstruction: save -> reload -> identity + seal + organs intact

Usage:

    from mantle_addon.stage1_gate import run_gate
    receipt = run_gate(organism, config, path, runtime)
    if receipt.passed:
        # organism.stage1_certified is now True
        # receipt is the evidence artifact

License: MIT (same as Mantle OS)
"""

from __future__ import annotations

import json
import os
import socket
import stat
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, NamedTuple
from unittest.mock import patch

from .config import ResidentConfig


PASS = "PASS"
FAIL = "FAIL"
NA = "NA"

_NINE_ORGANS = (
    "heart", "genome", "nervous", "senses", "immune",
    "limbs", "memory", "brain", "reproduction",
)


class GateRow(NamedTuple):
    code: str
    requirement: str
    result: str
    note: str


class Stage1Receipt(NamedTuple):
    """Evidence artifact produced by the addon-specific Stage-1 gate."""
    passed: bool
    rows: list[GateRow]
    fails: list[str]
    framework_passed: bool | None
    framework_rows: int | None
    framework_invariants: int | None
    framework_failures: list[str]
    summary: str
    issued_at: str
    resident_identity: str
    body_fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "rows": [r._asdict() for r in self.rows],
            "fails": self.fails,
            "framework_passed": self.framework_passed,
            "framework_rows": self.framework_rows,
            "framework_invariants": self.framework_invariants,
            "framework_failures": self.framework_failures,
            "summary": self.summary,
            "issued_at": self.issued_at,
            "resident_identity": self.resident_identity,
            "body_fingerprint": self.body_fingerprint,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


def _row(code: str, requirement: str, result: str, note: str = "") -> GateRow:
    return GateRow(code=code, requirement=requirement, result=result, note=note)


def _framework_evidence_complete(passed: bool | None, rows: int | None,
                                 invariants: int | None,
                                 failures: list[str]) -> bool:
    return (
        passed is True
        and rows is not None and rows > 0
        and invariants is not None and invariants > 0
        and not failures
    )


def _probe_a01_identity(organism: Any) -> GateRow:
    """A-01: Resident identity is Hermes.Mantle.AppAI."""
    name = organism.body.identity_name()
    ok = name == "Hermes.Mantle.AppAI"
    return _row("A-01", "Resident identity is Hermes.Mantle.AppAI",
                PASS if ok else FAIL,
                "name=%s" % name)


def _probe_a02_brain_dormant(organism: Any) -> GateRow:
    """A-02: Brain is dormant (not fused) — Phase-1 requirement."""
    fused = organism.brain.fused
    return _row("A-02", "Brain is dormant (not fused)",
                PASS if not fused else FAIL,
                "fused=%s" % fused)


def _probe_a03_not_pre_certified(organism: Any) -> GateRow:
    """A-03: stage1_certified is False (no prior self-certification)."""
    cert = organism.stage1_certified
    return _row("A-03", "No prior self-certification (stage1_certified is False)",
                PASS if not cert else FAIL,
                "stage1_certified=%s" % cert)


def _probe_a04_self_seal_verifies(organism: Any, path: Path) -> GateRow:
    """A-04: SELF seal exists and verifies under the body's genesis key."""
    seal_path = path / "self_seal.json"
    if not seal_path.is_file():
        return _row("A-04", "SELF seal exists and verifies", FAIL,
                    "self_seal.json missing")
    try:
        seal = json.loads(seal_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return _row("A-04", "SELF seal exists and verifies", FAIL,
                    "malformed: %s" % type(exc).__name__)
    if not organism.body.has_key:
        return _row("A-04", "SELF seal exists and verifies", FAIL,
                    "body has no genesis key")
    # Re-derive the payload the same way Organism._self_seal_payload does
    payload = organism._self_seal_payload()
    verifies = organism.body.verify(payload, seal.get("mac", ""))
    fp_match = seal.get("fingerprint") == organism.body.key_fingerprint
    ok = verifies and fp_match
    return _row("A-04", "SELF seal exists and verifies",
                PASS if ok else FAIL,
                "mac_verifies=%s, fingerprint_match=%s" % (verifies, fp_match))


def _probe_a05_organs_contracted(organism: Any) -> GateRow:
    """A-05: All nine organs present with contracts (fail-open)."""
    organs = organism.organs()
    missing = set(_NINE_ORGANS) - set(organs)
    if missing:
        return _row("A-05", "All nine organs present with contracts", FAIL,
                    "missing: %s" % sorted(missing))
    uncontracted = []
    not_fail_open = []
    for name, organ in organs.items():
        contract = getattr(organ, "contract", None)
        if contract is None:
            uncontracted.append(name)
        elif getattr(contract, "fail_mode", None) != "fail-open":
            not_fail_open.append(name)
    ok = not uncontracted and not not_fail_open
    note = "9/9 organs" if ok else (
        "uncontracted=%s, not_fail_open=%s" % (uncontracted, not_fail_open))
    return _row("A-05", "All nine organs present with contracts (fail-open)",
                PASS if ok else FAIL, note)


def _probe_a06_hooks_fail_open(runtime: Any) -> GateRow:
    """A-06: Observer hooks are fail-open (callbacks return None)."""
    from .runtime import OBSERVER_HOOKS
    results = []
    all_none = True
    for hook_name in OBSERVER_HOOKS:
        hook = getattr(runtime, hook_name, None)
        if hook is None:
            all_none = False
            results.append("%s=missing" % hook_name)
            continue
        try:
            result = hook()
        except Exception as exc:
            all_none = False
            results.append("%s=raised:%s" % (hook_name, type(exc).__name__))
            continue
        if result is not None:
            all_none = False
            results.append("%s!=None" % hook_name)
    return _row("A-06", "Observer hooks are fail-open (return None)",
                PASS if all_none else FAIL,
                "all return None" if all_none else "; ".join(results))


def _probe_a07_no_raw_payloads(organism: Any) -> GateRow:
    """A-07: No raw payloads in senses band (redaction boundary).

    The senses band should contain only derived/redacted metadata, never raw
    prompts, tool arguments, or results. We check that no entry in the senses
    band contains keys that would indicate raw payload storage.
    """
    senses = organism.prime.read("senses", reveal_private=True)
    raw_indicators = []
    for entry in senses:
        content = entry.get("content") if isinstance(entry, dict) else None
        if not isinstance(content, dict):
            continue
        signal = content.get("signal", {})
        metadata = signal.get("metadata", {})
        # The runtime redacts into content summaries; raw strings would indicate
        # a bypass of the _content_summary / _metadata pipeline.
        for field in ("user_message", "assistant_response", "args", "result"):
            val = metadata.get(field)
            if isinstance(val, str) and not val.startswith("sha256:"):
                # A raw string (not a content summary dict) indicates raw storage
                raw_indicators.append(field)
    ok = not raw_indicators
    return _row("A-07", "No raw payloads in senses band (redaction boundary)",
                PASS if ok else FAIL,
                "clean" if ok else "raw fields: %s" % sorted(set(raw_indicators)))


def _probe_a08_heartbeat_offline(organism: Any) -> GateRow:
    """A-08: Heartbeat runs without network/model/subprocess."""
    blocked = AssertionError("external capability used during heartbeat")
    try:
        with (
            patch("socket.create_connection", side_effect=blocked),
            patch("urllib.request.urlopen", side_effect=blocked),
            patch("subprocess.run", side_effect=blocked),
            patch("subprocess.Popen", side_effect=blocked),
        ):
            before = organism.heart.beats
            organism.heart.beat(assemble=False)
            advanced = organism.heart.beats == before + 1
        ok = advanced
        note = "1 beat with no network/subprocess"
    except AssertionError as exc:
        ok = False
        note = "blocked: %s" % str(exc)[:80]
    return _row("A-08", "Heartbeat runs without network/model/subprocess",
                PASS if ok else FAIL, note)


def _probe_a09_vendor_isolated() -> GateRow:
    """A-09: Vendored runtime is isolated from preloaded global mantle module."""
    from .vendor import vendored_symbol
    original = sys.modules.get("mantle")
    fake = ModuleType("mantle")
    setattr(fake, "__version__", "999.0-fake")
    sys.modules["mantle"] = fake
    try:
        Organism = vendored_symbol("core.organism", "Organism")
        version = vendored_symbol("__init__", "__version__")
        isolated = version != "999.0-fake"
    finally:
        if original is None:
            sys.modules.pop("mantle", None)
        else:
            sys.modules["mantle"] = original
    return _row("A-09", "Vendored runtime isolated from global mantle",
                PASS if isolated else FAIL,
                "vendored version=%s" % version if not isolated else "isolated")


def _probe_a10_storage_boundary(path: Path) -> GateRow:
    """A-10: Storage boundary: owner-only permissions, no symlinks."""
    violations = []
    if not path.is_dir():
        return _row("A-10", "Storage boundary (owner-only, no symlinks)", FAIL,
                    "path is not a directory")
    # Check the root
    root_info = path.lstat()
    if stat.S_ISLNK(root_info.st_mode):
        violations.append("root is symlink")
    if root_info.st_mode & 0o077:
        violations.append("root perms not owner-only")
    # Check all children
    for node in path.rglob("*"):
        info = node.lstat()
        if stat.S_ISLNK(info.st_mode):
            violations.append("%s is symlink" % node.name)
        if info.st_mode & 0o077:
            violations.append("%s perms not owner-only" % node.name)
        if not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
            violations.append("%s unsupported type" % node.name)
    ok = not violations
    return _row("A-10", "Storage boundary (owner-only, no symlinks)",
                PASS if ok else FAIL,
                "clean" if ok else "; ".join(violations[:3]))


def _probe_a11_proofs_body_authored(organism: Any) -> GateRow:
    """A-11: Action Execution Proofs are BODY-authored."""
    brain = organism.prime.read("brain", reveal_private=True)
    proofs = [
        e for e in brain
        if isinstance(e.get("content"), dict) and "action_proof" in e["content"]
    ]
    if not proofs:
        return _row("A-11", "Action Execution Proofs are BODY-authored", PASS,
                    "no proofs yet; no contradictory authorship")
    non_body = [
        e for e in proofs
        if e.get("authorship") != "BODY" or e.get("author") != "BODY"
    ]
    ok = not non_body
    return _row("A-11", "Action Execution Proofs are BODY-authored",
                PASS if ok else FAIL,
                "%d proof(s), all BODY" % len(proofs) if ok
                else "%d/%d non-BODY" % (len(non_body), len(proofs)))


def _probe_a12_mind_disabled(config: ResidentConfig) -> GateRow:
    """A-12: Config mind_enabled is False (Phase-1 only)."""
    ok = not config.mind_enabled
    return _row("A-12", "Config mind_enabled is False (Phase-1 only)",
                PASS if ok else FAIL,
                "mind_enabled=%s" % config.mind_enabled)


def _probe_a13_dual_flush(organism: Any) -> GateRow:
    """A-13: Dual-flush installed (checkpoint + atexit).

    The Heart's install_dual_flush() registers an atexit handler that calls
    circulate() on shutdown. This probe verifies the handler is installed by
    checking the Heart's _atexit_installed flag.
    """
    installed = getattr(organism.heart, "_atexit_installed", False)
    return _row("A-13", "Dual-flush installed (checkpoint + atexit)",
                PASS if installed else FAIL,
                "atexit_installed=%s" % installed)


def _probe_a14_reconstruction(organism: Any, path: Path) -> GateRow:
    """A-14: Reconstruction — save -> reload -> identity + seal + organs intact.

    The doctrine requires that a certified Body can be rebuilt from its sealed
    state. This probe saves the organism to a temp directory, reloads it via
    the vendored Organism.load() (with verify_seals=True), and verifies:
      1. The genesis key fingerprint is preserved (SELF continuity)
      2. The self-seal verifies under the reloaded key (anti-clone)
      3. All nine organs are present in the reloaded organism
      4. The Primer is sealed (identity immutability)
      5. No autoimmune or ancestor_tamper events were raised on load
    """
    import tempfile, shutil
    from .vendor import vendored_symbol

    Organism = vendored_symbol("core.organism", "Organism")
    tmp = Path(tempfile.mkdtemp(prefix="hermes-recon-"))
    try:
        # Save the organism to the temp directory
        organism.save(str(tmp))

        # Reload from the temp directory with seal verification
        org2 = Organism.load(str(tmp), verify_seals=True)

        # 1. Fingerprint preserved
        fp_match = organism.body.key_fingerprint == org2.body.key_fingerprint
        # 2. Self-seal verifies (no autoimmune_risk events on load)
        autoimm = any(
            e.get("kind") == "autoimmune_risk"
            for e in org2.immune.log
        )
        # 3. All nine organs present
        organs_ok = set(_NINE_ORGANS) == set(org2.organs())
        # 4. Primer sealed
        primer_ok = org2.body.primer_sealed
        # 5. No ancestor tamper events
        tamper = any(
            e.get("kind") == "ancestor_tamper"
            for e in org2.immune.log
        )

        ok = fp_match and not autoimm and organs_ok and primer_ok and not tamper
        note = "fp=%s, organs=%s, primer=%s, autoimmune=%s, tamper=%s" % (
            fp_match, organs_ok, primer_ok, autoimm, tamper)
        return _row("A-14", "Reconstruction: save -> reload -> identity + seal + organs intact",
                    PASS if ok else FAIL, note)
    except Exception as exc:
        return _row("A-14", "Reconstruction: save -> reload -> identity + seal + organs intact",
                    FAIL, "exception: %s: %s" % (type(exc).__name__, str(exc)[:80]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run_gate(
    organism: Any,
    config: ResidentConfig,
    path: Path,
    runtime: Any | None = None,
    *,
    include_framework: bool = True,
) -> Stage1Receipt:
    """Run the addon-specific Stage-1 gate.

    Args:
        organism: The resident Organism to audit.
        config: The resident configuration.
        path: The on-disk path to the organism's state directory.
        runtime: The ResidentRuntime (needed for A-06 hook probe).
                 If None, A-06 is marked NA.
        include_framework: If True, also run the vendored framework's
                           Stage-1 gate and include its result.

    Returns:
        A Stage1Receipt. If passed, sets organism.stage1_certified = True.
    """
    rows: list[GateRow] = []

    # Addon-specific probes
    rows.append(_probe_a01_identity(organism))
    rows.append(_probe_a02_brain_dormant(organism))
    rows.append(_probe_a03_not_pre_certified(organism))
    rows.append(_probe_a04_self_seal_verifies(organism, path))
    rows.append(_probe_a05_organs_contracted(organism))

    if runtime is not None:
        rows.append(_probe_a06_hooks_fail_open(runtime))
    else:
        rows.append(_row("A-06", "Observer hooks are fail-open (return None)", NA,
                         "no runtime provided"))

    rows.append(_probe_a07_no_raw_payloads(organism))
    rows.append(_probe_a08_heartbeat_offline(organism))
    rows.append(_probe_a09_vendor_isolated())
    rows.append(_probe_a10_storage_boundary(path))
    rows.append(_probe_a11_proofs_body_authored(organism))
    rows.append(_probe_a12_mind_disabled(config))
    rows.append(_probe_a13_dual_flush(organism))
    rows.append(_probe_a14_reconstruction(organism, path))

    # Framework gate
    framework_passed = None
    framework_rows = None
    framework_invariants = None
    framework_failures: list[str] = []
    if include_framework:
        try:
            from .vendor import vendored_symbol
            stage1_run = vendored_symbol("audits.stage1", "run")
            fw_passed, fw_evidence = stage1_run(
                organism, include_invariants=True
            )
            framework_passed = fw_passed
            framework_rows = len(fw_evidence.get("substrate_rows", [])) + len(
                fw_evidence.get("mesh_rows", [])
            )
            invariants = fw_evidence.get("invariants", [])
            framework_invariants = len(invariants)
            framework_failures = list(fw_evidence.get("fails", [])) + [
                "%s: %s" % (
                    row.get("name", "unnamed-invariant"),
                    row.get("detail", "no detail"),
                )
                for row in invariants
                if not row.get("ok")
            ]
        except Exception as exc:
            framework_passed = False
            framework_failures = ["exception:%s" % type(exc).__name__]

    fails = [r.code for r in rows if r.result != PASS]
    addon_passed = not fails
    framework_complete = _framework_evidence_complete(
        framework_passed, framework_rows, framework_invariants,
        framework_failures,
    )
    passed = addon_passed and framework_complete

    organism.stage1_certified = passed

    summary = (
        "addon probes: %d/%d passed, %d non-passing; framework: %s"
        % (
            sum(1 for r in rows if r.result == PASS),
            len(rows),
            len(fails),
            "PASS" if framework_passed else (
                "FAIL" if framework_passed is False else "skipped"
            ),
        )
    )

    return Stage1Receipt(
        passed=passed,
        rows=rows,
        fails=fails,
        framework_passed=framework_passed,
        framework_rows=framework_rows,
        framework_invariants=framework_invariants,
        framework_failures=framework_failures,
        summary=summary,
        issued_at=datetime.now(timezone.utc).isoformat(),
        resident_identity=organism.body.identity_name(),
        body_fingerprint=organism.body.key_fingerprint,
    )


def format_receipt(receipt: Stage1Receipt) -> str:
    """Human-readable gate output."""
    blocked_by = list(receipt.fails)
    framework_complete = _framework_evidence_complete(
        receipt.framework_passed, receipt.framework_rows,
        receipt.framework_invariants, receipt.framework_failures,
    )
    if not framework_complete:
        blocked_by.append("framework-incomplete")
    lines = ["=" * 74,
             "HERMES MANTLE ADDON — STAGE 1 GATE (addon-specific)",
             "=" * 74]
    width = max(len(r.requirement) for r in receipt.rows)
    for r in receipt.rows:
        tag = {"PASS": "[PASS]", "FAIL": "[FAIL]", "NA": "[ NA ]"}[r.result]
        lines.append("  %s %-5s %-*s  %s" % (tag, r.code, width, r.requirement, r.note))
    lines.append("-" * 74)
    lines.append("  Framework Stage-1: %s" % (
        "PASS" if receipt.framework_passed else (
            "FAIL" if receipt.framework_passed is False else "skipped")))
    lines.append("  Framework rows/invariants: %s / %s" % (
        receipt.framework_rows if receipt.framework_rows is not None else "skipped",
        receipt.framework_invariants
        if receipt.framework_invariants is not None else "skipped"))
    lines.append("  Framework failures: %s" % (
        receipt.framework_failures or "none"))
    lines.append("  Addon fails: %s" % (receipt.fails or "none"))
    lines.append("  RESULT: %s" % (
        "STAGE-1 PASSED — eligible for separate Phase-2 readiness and authorization"
        if receipt.passed
        else "STAGE-1 BLOCKED — %s" % ", ".join(blocked_by)))
    return "\n".join(lines)
