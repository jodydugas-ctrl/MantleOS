from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / "examples" / "notepadnext_appai_mantle2_candidate"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_notepadnext_candidate_builds_v2_without_claiming_applied_hooks(tmp_path):
    builder = _load("notepadnext_candidate_builder", CANDIDATE / "build_candidate.py")
    audit = builder.build(tmp_path / "candidate")
    assert audit["result"] == "PASS"
    assert audit["resident_protocol"] == "mantle-resident-v2"
    assert audit["germ_schema"] == "mantle-germ-v2"
    assert audit["genesis_keys_independent"] is True
    assert audit["resident_key_fingerprints"][0] != audit["resident_key_fingerprints"][1]
    assert audit["insertion_state"] == "observed_causal_graph"
    assert audit["runtime_hook_verified"] is False
    assert audit["visible_operation_certified"] is False


def test_notepadnext_terminal_uses_shared_runtime(tmp_path):
    terminal = _load("notepadnext_candidate_terminal", CANDIDATE / "terminal.py")
    assert terminal.ResidentRuntime.PROTOCOL_VERSION == "mantle-resident-v2"
    assert terminal.HOST_COMMIT == "0e9694d98aa8a9962bbe2bfa9dd502931be33670"
