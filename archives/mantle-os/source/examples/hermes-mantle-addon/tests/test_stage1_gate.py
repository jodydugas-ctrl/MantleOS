"""Tests for the addon-specific Stage-1 gate (mantle_addon.stage1_gate)."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mantle_addon.body import ResidentBodyFactory, save_resident
from mantle_addon.config import ResidentConfig
from mantle_addon.runtime import ResidentRuntime
from mantle_addon.stage1_gate import (
    Stage1Receipt,
    format_receipt,
    run_gate,
    PASS,
    FAIL,
    NA,
)


class Stage1GateTests(unittest.TestCase):
    runtime_root = PROJECT_ROOT / ".runtime" / "test-stage1"

    def setUp(self):
        shutil.rmtree(self.runtime_root, ignore_errors=True)
        self.runtime_root.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.runtime_root, ignore_errors=True)

    def _make_resident(self, profile="default"):
        """Create a fresh resident Body + runtime for testing."""
        config = ResidentConfig.from_mapping(
            {"storage_root": str(self.runtime_root)}
        )
        factory = ResidentBodyFactory(config)
        handle = factory.get_or_create(profile)
        runtime = ResidentRuntime(config, profile_id=profile, factory=factory)
        return config, handle, runtime

    def _run_with_framework_evidence(self, organism, config, path, runtime,
                                     passed, evidence):
        from mantle_addon.vendor import vendored_symbol as real_vendored_symbol

        def framework_stub(module_name, symbol_name):
            if module_name == "audits.stage1" and symbol_name == "run":
                return lambda *_args, **_kwargs: (passed, evidence)
            return real_vendored_symbol(module_name, symbol_name)

        with patch("mantle_addon.vendor.vendored_symbol",
                   side_effect=framework_stub):
            return run_gate(organism, config, path, runtime,
                            include_framework=True)

    def test_addon_probes_pass_without_granting_stage1(self):
        """Addon-only probes are diagnostic and cannot grant certification."""
        config, handle, runtime = self._make_resident()
        # Access runtime.organism to trigger _ensure_handle which installs dual-flush
        organism = runtime.organism

        receipt = run_gate(organism, config, handle.path, runtime,
                           include_framework=False)

        self.assertFalse(receipt.passed, msg=format_receipt(receipt))
        self.assertEqual([], receipt.fails)
        self.assertTrue(all(row.result == PASS for row in receipt.rows))
        self.assertFalse(organism.stage1_certified)

    def test_gate_produces_fourteen_addon_rows(self):
        """The gate should produce exactly 14 addon-specific probe rows."""
        config, handle, runtime = self._make_resident()
        organism = runtime.organism  # trigger dual-flush install

        receipt = run_gate(organism, config, handle.path, runtime,
                           include_framework=False)

        self.assertEqual(14, len(receipt.rows))
        codes = {r.code for r in receipt.rows}
        self.assertEqual(
            {"A-01", "A-02", "A-03", "A-04", "A-05", "A-06",
             "A-07", "A-08", "A-09", "A-10", "A-11", "A-12", "A-13", "A-14"},
            codes,
        )

    def test_a01_fails_on_wrong_identity(self):
        """A-01 should fail if the organism identity is not Hermes.Mantle.AppAI."""
        config, handle, runtime = self._make_resident()
        # Tamper with the identity by directly mutating the primer
        handle.organism.body._primer[0]["content"]["identity"]["name"] = "Wrong.AppAI"

        receipt = run_gate(handle.organism, config, handle.path, runtime,
                           include_framework=False)

        a01 = next(r for r in receipt.rows if r.code == "A-01")
        self.assertEqual(FAIL, a01.result)
        self.assertFalse(receipt.passed)

    def test_a02_fails_if_brain_fused(self):
        """A-02 should fail if the brain is fused (Phase-2 in Phase-1)."""
        config, handle, runtime = self._make_resident()
        # Simulate a fused brain by setting the flag
        handle.organism.brain._fused = True
        handle.organism.brain._mind = object()

        receipt = run_gate(handle.organism, config, handle.path, runtime,
                           include_framework=False)

        a02 = next(r for r in receipt.rows if r.code == "A-02")
        self.assertEqual(FAIL, a02.result)
        self.assertFalse(receipt.passed)

    def test_a03_fails_if_already_certified(self):
        """A-03 should fail if stage1_certified is already True."""
        config, handle, runtime = self._make_resident()
        handle.organism.stage1_certified = True

        receipt = run_gate(handle.organism, config, handle.path, runtime,
                           include_framework=False)

        a03 = next(r for r in receipt.rows if r.code == "A-03")
        self.assertEqual(FAIL, a03.result)

    def test_a04_fails_on_missing_self_seal(self):
        """A-04 should fail if self_seal.json is missing."""
        config, handle, runtime = self._make_resident()
        (handle.path / "self_seal.json").unlink()

        receipt = run_gate(handle.organism, config, handle.path, runtime,
                           include_framework=False)

        a04 = next(r for r in receipt.rows if r.code == "A-04")
        self.assertEqual(FAIL, a04.result)
        self.assertIn("missing", a04.note)

    def test_a04_fails_on_tampered_self_seal(self):
        """A-04 should fail if the self seal MAC is corrupted."""
        config, handle, runtime = self._make_resident()
        seal_path = handle.path / "self_seal.json"
        seal = json.loads(seal_path.read_text(encoding="utf-8"))
        seal["mac"] = "0" * 64
        seal_path.write_text(json.dumps(seal), encoding="utf-8")

        receipt = run_gate(handle.organism, config, handle.path, runtime,
                           include_framework=False)

        a04 = next(r for r in receipt.rows if r.code == "A-04")
        self.assertEqual(FAIL, a04.result)

    def test_a06_na_without_runtime(self):
        """A-06 should be NA when no runtime is provided."""
        config, handle, _runtime = self._make_resident()

        receipt = run_gate(handle.organism, config, handle.path, runtime=None,
                           include_framework=False)

        a06 = next(r for r in receipt.rows if r.code == "A-06")
        self.assertEqual(NA, a06.result)
        self.assertFalse(receipt.passed)
        self.assertFalse(handle.organism.stage1_certified)

    def test_a06_hook_exception_fails_instead_of_being_swallowed(self):
        """A hook that raises is not evidence of a fail-open observer boundary."""
        config, handle, runtime = self._make_resident()

        def broken_hook(**_kwargs):
            raise RuntimeError("observer escaped")

        runtime.pre_tool_call = broken_hook
        receipt = run_gate(handle.organism, config, handle.path, runtime,
                           include_framework=False)

        a06 = next(r for r in receipt.rows if r.code == "A-06")
        self.assertEqual(FAIL, a06.result)
        self.assertIn("raised:RuntimeError", a06.note)
        self.assertFalse(receipt.passed)

    def test_a11_passes_vacuously_with_no_proofs(self):
        """A-11 is vacuously true before the first Action Execution Proof exists."""
        config, handle, runtime = self._make_resident()

        receipt = run_gate(handle.organism, config, handle.path, runtime,
                           include_framework=False)

        a11 = next(r for r in receipt.rows if r.code == "A-11")
        self.assertEqual(PASS, a11.result)

    def test_skipping_framework_gate_never_certifies_stage1(self):
        """Fast addon probes are evidence only, never complete Stage-1 certification."""
        config, handle, runtime = self._make_resident()
        organism = runtime.organism

        receipt = run_gate(organism, config, handle.path, runtime,
                           include_framework=False)

        self.assertFalse(receipt.passed)
        self.assertIsNone(receipt.framework_passed)
        self.assertFalse(organism.stage1_certified)

    def test_incomplete_framework_evidence_never_certifies_stage1(self):
        """A framework PASS without substantive evidence must fail closed."""
        config, handle, runtime = self._make_resident()
        organism = runtime.organism
        receipt = self._run_with_framework_evidence(
            organism, config, handle.path, runtime, True,
            {"substrate_rows": [], "mesh_rows": [], "invariants": []},
        )

        self.assertTrue(receipt.framework_passed)
        self.assertEqual(0, receipt.framework_rows)
        self.assertEqual(0, receipt.framework_invariants)
        self.assertFalse(receipt.passed)
        self.assertFalse(organism.stage1_certified)

    def test_framework_failure_detail_overrides_pass_flag(self):
        """Contradictory framework evidence cannot certify a resident."""
        config, handle, runtime = self._make_resident()
        organism = runtime.organism
        receipt = self._run_with_framework_evidence(
            organism, config, handle.path, runtime, True,
            {
                "substrate_rows": [{"result": "PASS"}],
                "mesh_rows": [],
                "invariants": [
                    {"ok": False, "name": "forced-failure", "detail": "test"},
                ],
            },
        )

        self.assertTrue(receipt.framework_passed)
        self.assertEqual(["forced-failure: test"], receipt.framework_failures)
        self.assertFalse(receipt.passed)
        self.assertFalse(organism.stage1_certified)

    def test_a11_passes_after_observed_tool_call(self):
        """A-11 should pass after a post_tool_call produces a BODY-authored proof."""
        config, handle, runtime = self._make_resident()
        runtime.post_tool_call(
            session_id="s1",
            tool_name="terminal",
            args={"command": "echo hi"},
            result="hi",
            tool_call_id="c1",
            status="ok",
            duration_ms=1,
        )
        # Use runtime.organism (the live handle the runtime observes through)
        receipt = run_gate(runtime.organism, config, handle.path, runtime,
                           include_framework=False)

        a11 = next(r for r in receipt.rows if r.code == "A-11")
        self.assertEqual(PASS, a11.result)

    def test_a12_fails_if_mind_enabled(self):
        """A-12 should fail if mind_enabled is True in config."""
        config, handle, runtime = self._make_resident()
        # Production ResidentConfig refuses this state. A plain fixture object
        # proves the gate independently rejects it without bypassing the dataclass.
        invalid_values = config.to_dict()
        invalid_values["mind_enabled"] = True
        config = SimpleNamespace(**invalid_values)

        receipt = run_gate(handle.organism, config, handle.path, runtime,
                           include_framework=False)

        a12 = next(r for r in receipt.rows if r.code == "A-12")
        self.assertEqual(FAIL, a12.result)

    def test_gate_certifies_on_pass(self):
        """On pass, the gate should set organism.stage1_certified = True."""
        config, handle, runtime = self._make_resident()
        organism = runtime.organism  # trigger dual-flush install
        self.assertFalse(organism.stage1_certified)

        receipt = self._run_with_framework_evidence(
            organism, config, handle.path, runtime, True,
            {
                "substrate_rows": [{"result": "PASS"}],
                "mesh_rows": [],
                "invariants": [{"ok": True}],
            },
        )

        self.assertTrue(receipt.passed)
        self.assertTrue(organism.stage1_certified)

    def test_receipt_serializes_to_json(self):
        """The receipt should serialize to valid JSON."""
        config, handle, runtime = self._make_resident()
        organism = runtime.organism  # trigger dual-flush install

        receipt = run_gate(organism, config, handle.path, runtime,
                           include_framework=False)

        data = json.loads(receipt.to_json())
        self.assertFalse(data["passed"])
        self.assertEqual(14, len(data["rows"]))
        self.assertIsNone(data["framework_rows"])
        self.assertIsNone(data["framework_invariants"])
        self.assertEqual([], data["framework_failures"])

    def test_format_receipt_produces_readable_output(self):
        """format_receipt should produce human-readable gate output."""
        config, handle, runtime = self._make_resident()
        organism = runtime.organism  # trigger dual-flush install

        receipt = run_gate(organism, config, handle.path, runtime,
                           include_framework=False)
        text = format_receipt(receipt)

        self.assertIn("STAGE 1 GATE", text)
        self.assertIn("A-01", text)
        self.assertIn("A-14", text)
        self.assertIn("BLOCKED", text)
        self.assertIn("framework-incomplete", text)
        self.assertNotIn("Phase 2 authorized", text)

    def test_framework_stage1_integration(self):
        """The combined gate must fail if either addon or framework evidence fails."""
        config, handle, runtime = self._make_resident()
        resident = runtime.organism

        receipt = run_gate(resident, config, handle.path, runtime,
                           include_framework=True)

        self.assertTrue(receipt.framework_passed, receipt.framework_failures)
        self.assertTrue(receipt.passed, format_receipt(receipt))
        self.assertGreater(receipt.framework_rows or 0, 0)
        self.assertGreater(receipt.framework_invariants or 0, 0)
        self.assertEqual([], receipt.framework_failures)

    def test_a13_passes_when_dual_flush_installed(self):
        """A-13 should pass after the runtime installs dual-flush."""
        config, handle, runtime = self._make_resident()
        # The runtime installs dual-flush in _ensure_handle, which is triggered
        # by accessing .organism
        _ = runtime.organism

        receipt = run_gate(runtime.organism, config, handle.path, runtime,
                           include_framework=False)

        a13 = next(r for r in receipt.rows if r.code == "A-13")
        self.assertEqual(PASS, a13.result)

    def test_a13_fails_when_dual_flush_not_installed(self):
        """A-13 should fail when dual-flush has not been installed."""
        config, handle, runtime = self._make_resident()
        # Don't access runtime.organism (which would trigger _ensure_handle
        # and install dual-flush). Use the handle's organism directly, which
        # has NOT had install_dual_flush called.
        receipt = run_gate(handle.organism, config, handle.path, runtime,
                           include_framework=False)

        a13 = next(r for r in receipt.rows if r.code == "A-13")
        self.assertEqual(FAIL, a13.result)

    def test_a14_passes_on_valid_resident(self):
        """A-14 should pass: save -> reload preserves identity and integrity."""
        config, handle, runtime = self._make_resident()
        organism = runtime.organism  # trigger dual-flush install
        # Add some activity so the organism has state to reconstruct
        runtime.post_tool_call(
            session_id="s1", tool_name="terminal",
            args={"command": "echo hi"}, result="hi",
            tool_call_id="c1", status="ok", duration_ms=1,
        )

        receipt = run_gate(organism, config, handle.path, runtime,
                           include_framework=False)

        a14 = next(r for r in receipt.rows if r.code == "A-14")
        self.assertEqual(PASS, a14.result)

    def test_a14_fails_on_corrupted_identity(self):
        """A-14 should fail when the organism's identity is corrupted on reconstruction."""
        config, handle, runtime = self._make_resident()
        organism = runtime.organism
        # Corrupt the key fingerprint so it doesn't match the genesis key.
        # On save -> load, key_fingerprint_consistent() will return False,
        # triggering an autoimmune_risk PermissionError that the probe catches.
        organism.body._key_fingerprint = "0" * 16

        receipt = run_gate(organism, config, handle.path, runtime,
                           include_framework=False)

        a14 = next(r for r in receipt.rows if r.code == "A-14")
        self.assertEqual(FAIL, a14.result)


if __name__ == "__main__":
    unittest.main()
