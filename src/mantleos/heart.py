"""Local Heart rhythm and continuity. Host work is supplied by the trial adapter."""
import hashlib
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

from . import engram
from .transactions import atomic_bytes, body_lock


INTERVAL = 600
SOURCE = "appai-heart"
ABSENT = "MIND_ABSENT"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def engine_pin():
    return sha(Path(__file__).read_bytes())


def records(root):
    root = Path(root)
    history = engram.read(root / "ENGRAM.jsonl")
    if not history or history[0]["type"] != "heart.planted":
        raise ValueError("No planted Heart")
    founding = history[0]["body"]
    if sha((root / "PRIMER.md").read_bytes()) != founding["primer_sha256"]:
        raise ValueError("Founding PRIMER changed")
    if engine_pin() != founding["engine_sha256"]:
        raise ValueError("Planted Heart source changed")
    return history


def append(root, kind, body, history):
    return engram.append(Path(root) / "ENGRAM.jsonl", kind, SOURCE, body,
                         expected_head=history[-1]["sha256"] if history else engram.ZERO)


def plant(root, primer, binding, *, wall=time.time):
    root = Path(root)
    root.mkdir()
    atomic_bytes(root / "PRIMER.md", primer, replace=False)
    now = wall()
    return append(root, "heart.planted", {
        "identity": uuid.uuid4().hex, "primer_sha256": sha(primer),
        "engine_sha256": engine_pin(), "binding": binding,
        "sequence": 1, "kind": "initial", "at": now, "next_due": now + INTERVAL,
        "missed": 0, "mind": ABSENT, "command_stack": ["observe", "resolve"],
    }, [])


def beats(history):
    return [event["body"] for event in history
            if event["type"] in {"heart.planted", "heart.beat"}]


def pending_wake(history):
    for event in reversed(history):
        if event["type"] == "heart.wake":
            return event["sha256"]
        if event["type"] in {"heart.beat", "heart.planted"}:
            return None
    return None


def wake(root, reason):
    if not reason.strip() or len(reason) > 120:
        raise ValueError("Wake reason needs 1–120 characters")
    with body_lock(root):
        history = records(root)
        if pending_wake(history):
            return {"status": "COALESCED"}
        append(root, "heart.wake", {"reason": reason}, history)
        return {"status": "QUEUED"}


class Rhythm:
    def __init__(self, root, *, wall=time.time, clock=time.monotonic):
        self.root = Path(root)
        self.wall = wall
        self.clock = clock
        last = beats(records(root))[-1]
        self.origin = max(wall(), last["at"])
        self.started = clock()
        self.deadline = self.started + last["next_due"] - self.origin
        self.restart_due = self.deadline <= self.started
        self.next_wake = self.started
        self.degraded = False

    def poll(self, mind=ABSENT):
        tick = self.clock()
        try:
            with body_lock(self.root):
                history = records(self.root)
                if self.degraded:
                    append(self.root, "heart.durability-restored", {"at": self.wall()}, history)
                    self.degraded = False
                    history = records(self.root)
                last = beats(history)[-1]
                wake_id = pending_wake(history)
                due = tick >= self.deadline
                if not due and (not wake_id or tick < self.next_wake):
                    return None
                missed = max(0, math.floor((tick - self.deadline) / INTERVAL)) if due else 0
                advance = (missed + 1) * INTERVAL if due else 0
                beat = {
                    "sequence": last["sequence"] + 1,
                    "kind": ("recovery" if self.restart_due or missed else "natural") if due else "wake",
                    "at": self.origin + (tick - self.started), "observed_wall": self.wall(),
                    "next_due": last["next_due"] + advance, "missed": missed,
                    "wake": wake_id, "mind": mind, "command_stack": ["observe", "resolve"],
                }
                append(self.root, "heart.beat", beat, history)
                self.deadline += advance
                self.next_wake = tick + 1
                if due:
                    self.restart_due = False
                return beat
        except OSError:
            self.degraded = True
            raise


def run(root, *, natural_beats=None, work=None, timeout=60, assessment=None,
        credentials_available=False, clock=time.monotonic, wall=time.time, sleep=time.sleep):
    """Supervise explicitly supplied local commands. Assessment output cannot dispatch effects."""
    if not 0 < timeout <= 60:
        raise ValueError("Worker timeout must be within 60 seconds")
    completed = 0
    children = {}

    def report(kind, outcome, sequence=None):
        try:
            with body_lock(root):
                append(root, "heart.worker", {"worker": kind, "outcome": outcome,
                                              "beat": sequence}, records(root))
        except OSError as error:
            rhythm.degraded = True
            print(f"Worker receipt could not be written: {error}", file=sys.stderr, flush=True)

    def launch(kind, command, sequence=None):
        try:
            options = {}
            if kind == "assessment":
                options = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL,
                           "env": {key: os.environ[key] for key in ("SYSTEMROOT", "TEMP", "TMP")
                                   if key in os.environ}}
            child = subprocess.Popen(command, stdin=subprocess.DEVNULL, **options)
        except OSError:
            report(kind, "START_FAILED", sequence)
            return
        children[kind] = child, clock() + timeout, sequence

    with body_lock(Path(root) / "runner"):
        rhythm = Rhythm(root, clock=clock, wall=wall)
        try:
            while True:
                for kind, (child, deadline, sequence) in list(children.items()):
                    code = child.poll()
                    if code is not None:
                        report(kind, "EXITED" if code == 0 else "FAILED", sequence)
                        del children[kind]
                    elif clock() >= deadline:
                        child.kill()
                        report(kind, "TIMEOUT_RECONCILE", sequence)
                        children[kind] = child, math.inf, sequence
                if natural_beats is not None and completed >= natural_beats:
                    if not children:
                        return
                    sleep(0.25)
                    continue
                try:
                    mind = ABSENT if assessment is None else (
                        "MIND_CREDENTIALS_MISSING" if not credentials_available else
                        "MIND_BUSY" if "assessment" in children else "ASSESSMENT_ELIGIBLE")
                    beat = rhythm.poll(mind)
                except OSError as error:
                    print(f"Heart durability degraded: {error}", file=sys.stderr, flush=True)
                    beat = None
                if beat:
                    print(engram.canonical(beat), flush=True)
                    completed += beat["kind"] != "wake"
                    if mind == "ASSESSMENT_ELIGIBLE":
                        launch("assessment", [*assessment, engram.canonical(beat)], beat["sequence"])
                if work is not None:
                    launch("construction", work)
                    work = None
                sleep(0.25)
        finally:
            for kind, (child, _, sequence) in children.items():
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=5)
                report(kind, "INTERRUPTED_RECONCILE", sequence)


