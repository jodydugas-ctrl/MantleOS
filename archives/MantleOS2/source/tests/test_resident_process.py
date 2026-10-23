"""Actual process evidence; this does not certify OS service registration."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time

import pytest
from test_runtime import prepare_unborn_nest

from mantleos.assimilate import _runtime_payloads
from mantleos.resident import _runner_text
from mantleos.runtime import MantleBody


def _wait_for(process, condition):
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            raise AssertionError(f"Resident exited: {process.returncode}: {stdout} {stderr}")
        try:
            if condition():
                return
        except json.JSONDecodeError:
            # Observation may coincide with the writer appending one record.
            pass
        time.sleep(0.1)
    raise AssertionError("Resident did not produce the expected committed evidence")


def _stop(process):
    if process.poll() is None:
        process.kill()
    process.communicate(timeout=10)


def _prepare_resident(tmp_path, *, create_runner=True):
    nest = (tmp_path / "disposable Body").resolve()
    nest.mkdir()
    prepare_unborn_nest(nest)
    for relative, text in _runtime_payloads().items():
        target = nest / "mantle" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    manifest_path = nest / "mantle" / "ASSIMILATION.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = sorted(p for p in (nest / "mantle").rglob("*") if p.is_file())
    manifest["delta"] = {
        "paths": [p.relative_to(nest).as_posix() for p in files],
        "sha256": {
            p.relative_to(nest).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in files if p != manifest_path
        },
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    prebirth_path = nest / ".mantle" / "prebirth.json"
    prebirth = json.loads(prebirth_path.read_text(encoding="utf-8"))
    prebirth["public_manifest_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    prebirth_path.write_text(json.dumps(prebirth), encoding="utf-8")
    native = nest / "body.py"
    native.write_text("print(6 * 7)\n", encoding="utf-8")
    body = MantleBody(nest)
    body.birth("Disposable resident process test", approved=True)
    runner = nest / ".mantle" / "resident" / "run-heart.py"
    if create_runner:
        runner.parent.mkdir(parents=True)
        runner.write_text(_runner_text(nest), encoding="utf-8")
    return body, runner, native


def test_real_resident_start_communication_and_restart_with_local_organs(tmp_path):
    body, runner, native = _prepare_resident(tmp_path)
    native_before = native.read_bytes()
    primer_before = body.paths.primer.read_bytes()

    def starts():
        events, _ = body._vcw().events_after(limit=1000)
        return sum(
            e["kind"] == "heartbeat.completed" and e["data"]["reason"] == "resident-startup"
            for e in events
        )

    def start():
        return subprocess.Popen(
            [sys.executable, "-I", str(runner)], cwd=tmp_path,
            env={**os.environ, "PYTHONPATH": str(tmp_path / "nonexistent")},
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    process = start()
    try:
        _wait_for(process, lambda: starts() == 1)
        with body.paths.communication.open("a", encoding="utf-8") as stream:
            stream.write("USER> committed process test message\n")
        _wait_for(process, lambda: "APPAI> Received and recorded." in
                  body.paths.communication.read_text(encoding="utf-8"))
        _wait_for(process, lambda: any(
            e["kind"] == "heartbeat.completed" and e["data"]["reason"] == "communication-file-save"
            for e in body._vcw().events_after(limit=1000)[0]
        ))
    finally:
        _stop(process)

    # A pending host receipt models a host lost between before/after-MIND seams.
    body.begin_host_heartbeat("disposable-session", "interrupted-turn")
    process = start()
    try:
        _wait_for(process, lambda: starts() == 2)
    finally:
        _stop(process)

    assert not body.host_heartbeat_pending("disposable-session", "interrupted-turn")
    assert body.verify()["ok"]
    events, _ = body._vcw().events_after(limit=1000)
    assert sum(e["kind"] == "appai.response" for e in events) == 1
    assert any(e["kind"] == "heartbeat.completed" and
               e["data"]["mind"] == "interrupted-or-process-lost" for e in events)
    assert body.paths.primer.read_bytes() == primer_before
    assert native.read_bytes() == native_before
    native_result = subprocess.run(
        [sys.executable, "-I", str(native)], capture_output=True, text=True, timeout=10, check=True
    )
    assert native_result.stdout.strip() == "42"


@pytest.mark.skipif(os.name == "nt", reason="Windows terminate() is a forced kill, not SIGTERM delivery")
def test_real_sigterm_stops_idle_resident_without_extra_heartbeat(tmp_path):
    body, runner, native = _prepare_resident(tmp_path)
    primer_before = body.paths.primer.read_bytes()
    native_before = native.read_bytes()
    process = subprocess.Popen(
        [sys.executable, "-I", str(runner)], cwd=tmp_path,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        _wait_for(process, lambda: any(
            e["kind"] == "heartbeat.completed" and e["data"]["reason"] == "resident-startup"
            for e in body._vcw().events_after(limit=1000)[0]
        ))
        before, _ = body._vcw().events_after(limit=1000)
        process.terminate()
        stdout, stderr = process.communicate(timeout=5)
        assert process.returncode == 0, stderr
        assert json.loads(stdout) == {
            "status": "stopped", "reason": "SIGTERM", "shutdown": "cooperative-between-heartbeats",
        }
    finally:
        _stop(process)
    after, _ = body._vcw().events_after(limit=1000)
    assert after == before
    assert body.verify()["ok"]
    assert body.paths.primer.read_bytes() == primer_before
    assert native.read_bytes() == native_before
    result = subprocess.run(
        [sys.executable, "-I", str(native)], capture_output=True, text=True, timeout=10, check=True,
    )
    assert result.stdout.strip() == "42"
