"""Reviewed local checks used by the notes trial's KPP satisfaction suite."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

from . import heart, heart_trial as trial
from .kpp.core import read_json


class Clock:
    def __init__(self):
        self.tick = 0
        self.wall_base = 1000

    def monotonic(self):
        return self.tick

    def wall(self):
        return self.wall_base + self.tick


def notes(candidate, scratch):
    source = candidate / "notes.py"
    database = scratch / "notes.sqlite"
    trial.behavior(source, database, export=True)
    before = database.read_bytes()
    assert trial.notes(source, database, "export") == "1: " + trial.SEED + " Updated.\n"
    assert database.read_bytes() == before
    missing = subprocess.run(trial.command(source, database, "read", "999"),
                             capture_output=True, timeout=5)
    assert missing.returncode == 2 and b"note not found" in missing.stderr
    assert json.loads(trial.notes(source, database, "read", "1")) == trial.SEED + " Updated."
    if (candidate / "facts.json").exists():
        facts = read_json(candidate / "facts.json")
        assert facts["mind"] == "DISCONNECTED"
        assert heart.sha(source.read_bytes()) == facts["binding"]["notes_sha256"]
        assert heart.sha((candidate / "notes_export.py").read_bytes()) == facts["binding"]["export_sha256"]


def rhythm(candidate, scratch):
    clock = Clock()
    root = scratch / "heart"
    initial = heart.plant(root, trial.PRIMER, {}, wall=clock.wall)["body"]
    live = heart.Rhythm(root, wall=clock.wall, clock=clock.monotonic)
    clock.tick = 599
    assert live.poll() is None
    assert heart.wake(root, "test")["status"] == "QUEUED"
    assert heart.wake(root, "coalesced")["status"] == "COALESCED"
    wake = live.poll()
    assert wake["next_due"] == initial["next_due"] and wake["kind"] == "wake"
    clock.tick = 600
    clock.wall_base -= 120
    natural = live.poll()
    assert natural["kind"] == "natural" and natural["sequence"] == 3
    assert natural["next_due"] == 2200 and natural["mind"] == heart.ABSENT
    assert natural["command_stack"] == ["observe", "resolve"]
    clock.wall_base += 120
    clock.tick = 2401
    resumed = heart.Rhythm(root, wall=clock.wall, clock=clock.monotonic)
    with patch.object(heart, "append", side_effect=OSError("synthetic disk failure")):
        try:
            resumed.poll()
        except OSError:
            assert resumed.degraded
        else:
            raise AssertionError("Expected failed durable append")
    assert heart.beats(heart.records(root))[-1] == natural
    next_beat = resumed.poll()
    assert next_beat["kind"] == "recovery" and next_beat["missed"] == 2
    assert resumed.poll() is None
    assert (root / "PRIMER.md").read_bytes() == trial.PRIMER
    assert heart.beats(heart.records(root))[0] == initial
    facts = read_json(candidate / "facts.json")
    assert facts["cadence"]["elapsed"] >= heart.INTERVAL
    assert facts["cadence"]["natural"]["mind"] == heart.ABSENT


def construction(candidate, scratch):
    facts = read_json(candidate / "facts.json")
    resolution = facts["discovery"]["resolutions"]
    assert resolution == {"notes-storage": "REUSE", "text-export": "ACQUIRE",
                          "other-host-tools": "BLOCKED"}
    effect = facts["construction"]["checked_effect"]
    assert effect["stage"] == "VERIFIED"
    assert effect["observation"]["result"] == facts["binding"]["export_sha256"]
    assert trial.resolve_capability(discovered=True, accessible=True, authorized=False,
                                    verified=True) == "BLOCKED"
    assert trial.resolve_capability(discovered=True, accessible=True, authorized=True,
                                    verified=False, adapter=True) == "ADAPT"
    assert trial.resolve_capability(discovered=False, accessible=False, authorized=False,
                                    verified=False, confirmed_missing=True) == "BUILD"


def assessment(candidate, scratch):
    for name, code, credentials, expected in (
        ("missing", "raise SystemExit(7)", False, "MIND_CREDENTIALS_MISSING"),
        ("failed", "raise SystemExit(7)", True, "ASSESSMENT_ELIGIBLE"),
        ("stalled", "import time; time.sleep(30)", True, "ASSESSMENT_ELIGIBLE"),
    ):
        clock = Clock()
        root = scratch / name
        heart.plant(root, trial.PRIMER, {}, wall=clock.wall)
        heart.wake(root, "assessment test")

        def advance(_):
            time.sleep(0.025)
            clock.tick += 300

        heart.run(root, natural_beats=2, assessment=[sys.executable, "-I", "-c", code],
                  credentials_available=credentials, timeout=60,
                  clock=clock.monotonic, wall=clock.wall, sleep=advance)
        history = heart.records(root)
        pulses = heart.beats(history)
        assert pulses[1]["mind"] == expected
        assert len(pulses) == 4
        workers = [event["body"] for event in history if event["type"] == "heart.worker"]
        if not credentials:
            assert not workers
        elif name == "stalled":
            assert any(worker["outcome"] == "TIMEOUT_RECONCILE" for worker in workers)
        else:
            assert any(worker["outcome"] in {"FAILED", "TIMEOUT_RECONCILE"} for worker in workers)


def admission(candidate, scratch):
    nest = scratch / "early"
    trial.plant(nest)
    for approval, baker in ((None, "synthetic"), ("stale", "synthetic")):
        try:
            trial.birth(nest, approval, baker)
        except ValueError:
            pass
        else:
            raise AssertionError("Birth was allowed without qualification and approval")
    assert not trial.latest(heart.records(nest / ".heart"), "heart.born")


def check(case, candidate):
    checks = {"notes": notes, "rhythm": rhythm, "construction": construction,
              "assessment": assessment, "admission": admission}
    with tempfile.TemporaryDirectory(prefix="heart-check-") as work:
        checks[case](candidate, Path(work))
