from __future__ import annotations

import os
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from mantle import spore
from mantle.audits import stage1
from mantle.core.organism import Organism
from mantle.hatchery import hatch, validate_germ
from mantle.lifecycle import LifecycleAction, LifecycleAuthorization


ROOT = Path(__file__).resolve().parents[2]
SPORES = ROOT / "examples" / "spores"
SRC = ROOT / "src"


def _independent_seed_spores() -> list[Path]:
    seeds = []
    for path in sorted(SPORES.glob("*.png")):
        state = spore.read_spore(str(path))["state"]
        germ = state.get("germ")
        if isinstance(germ, dict) and germ.get("schema") == "mantle-germ-v2":
            seeds.append(path)
    return seeds


def test_advertised_seed_spores_decode_verify_and_stage1_hatch():
    seeds = _independent_seed_spores()
    assert seeds, "no independent SEED spores discovered in examples/spores"

    for path in seeds:
        report = spore.verify_spore(str(path))
        assert report["ok"], "%s failed structural verification: %s" % (
            path.name, report["problems"])
        state = spore.read_spore(str(path))["state"]
        germ = validate_germ(dict(state.get("germ") or {}))
        assert germ["identity"]["name"].endswith(".AppAI")

        with tempfile.TemporaryDirectory(prefix="mantle-seed-hatch-") as parent:
            out_dir = str(Path(parent) / "nest")
            auth = LifecycleAuthorization.issue(
                LifecycleAction.HATCH, str(path), out_dir
            )
            result = hatch(str(path), out_dir=out_dir, warmup_beats=0,
                           authorization=auth)
            org = result["organism"]
            passed, evidence = stage1.run(org, include_invariants=False)
            assert result["report"]["certified"] is True
            assert org.stage1_certified is True
            assert passed, "%s failed Stage-1: %s" % (path.name, evidence["fails"])

            out = Path(out_dir)
            report_path = out / "hatch_report.json"
            portrait_path = out / "face.png"
            assert report_path.is_file(), "%s hatch report was not persisted" % path.name
            assert portrait_path.is_file(), "%s self-portrait was not persisted" % path.name
            persisted_report = json.loads(report_path.read_text(encoding="utf-8"))
            assert persisted_report["saved_to"] == out_dir
            assert persisted_report["portrait"] == str(portrait_path)
            assert persisted_report["spore_distillation"]["spore_sealed"] is True

            reloaded = Organism.load(out_dir, verify_seals=True)
            source_facts = [
                entry.get("content") for entry in reloaded.memory.recall("facts")
                if isinstance(entry.get("content"), dict)
                and "sporeagent_source" in entry["content"]
            ]
            assert len(source_facts) == 1, (
                "%s saved before its source lifecycle receipt" % path.name)


def test_doctor_refuses_missing_and_malformed_organisms_without_traceback(tmp_path):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC)

    missing = subprocess.run(
        [sys.executable, "-m", "mantle", "doctor", "path-that-does-not-exist"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert missing.returncode != 0
    assert "DOCTOR REFUSED: no saved Mantle organism found at path-that-does-not-exist" in (
        missing.stdout)
    assert "Traceback" not in missing.stdout + missing.stderr

    malformed = tmp_path / "broken-nest"
    malformed.mkdir()
    (malformed / "organism.json").write_text("{bad json", encoding="utf-8")
    bad = subprocess.run(
        [sys.executable, "-m", "mantle", "doctor", str(malformed)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert bad.returncode != 0
    assert "DOCTOR REFUSED: saved Mantle organism at" in bad.stdout
    assert "could not be loaded" in bad.stdout
    assert "Traceback" not in bad.stdout + bad.stderr
