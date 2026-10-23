import json
from pathlib import Path

import pytest

from mantle.research import (
    AppletBodyAdapter,
    CandidateChamber,
    CandidateChamberError,
    GenomeProposalAdapter,
    GraftWorkspaceAdapter,
    SkillTrialAdapter,
    SourceWorktreeAdapter,
)


def test_source_candidate_isolated_and_hash_stable(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "main.py").write_text("print('old')\n", encoding="utf-8")
    chamber = CandidateChamber(SourceWorktreeAdapter(source, allowlist={"main.py"}))
    baseline = chamber.baseline()
    candidate = chamber.materialize({"files": {"main.py": "print('new')\n"}})
    assert baseline.tree_hash != candidate.tree_hash
    assert chamber.verify_original_unchanged()
    assert (source / "main.py").read_text(encoding="utf-8") == "print('old')\n"
    assert candidate.tree_hash == chamber.materialize(
        {"files": {"main.py": "print('new')\n"}},
        workspace=tmp_path / "candidate-two",
    ).tree_hash


def test_surface_escape_and_symlink_are_refused(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "safe.txt").write_text("safe", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    chamber = CandidateChamber(SourceWorktreeAdapter(source, allowlist={"safe.txt"}))
    with pytest.raises(CandidateChamberError):
        chamber.materialize({"files": {"../outside.txt": "nope"}})
    link = source / "link.txt"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable on this host")
    with pytest.raises(CandidateChamberError):
        chamber.baseline()


def test_specialized_adapters_keep_authority_outside_candidate(tmp_path: Path):
    skill = SkillTrialAdapter("def f(x):\n    return x + 1\n", "f", [({"x": 1}, 2)])
    skill_candidate = CandidateChamber(skill).materialize({})
    payload = json.loads((skill_candidate.workspace / "candidate.json").read_text())
    assert payload["calcify"] is False

    genome = GenomeProposalAdapter([])
    genome_candidate = CandidateChamber(genome).materialize({})
    assert json.loads((genome_candidate.workspace / "candidate.json").read_text())["adopt"] is False

    applet_source = tmp_path / "applet"
    applet_source.mkdir()
    (applet_source / "app.py").write_text("print('inert')\n", encoding="utf-8")
    applet_candidate = CandidateChamber(AppletBodyAdapter(applet_source)).materialize({})
    capsule = json.loads((applet_candidate.workspace / "capsule.json").read_text())
    assert capsule["foreign"] is True
    assert capsule["execution_authority"] is False


def test_graft_adapter_requires_explicit_graft_and_preserves_host(tmp_path: Path):
    host = tmp_path / "host"
    host.mkdir()
    (host / "app.py").write_text("def run():\n    return 1\n", encoding="utf-8")
    adapter = GraftWorkspaceAdapter(host)
    with pytest.raises(CandidateChamberError):
        CandidateChamber(adapter).materialize({})
    assert adapter.verify_original_unchanged()
