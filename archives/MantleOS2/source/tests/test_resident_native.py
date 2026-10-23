"""Opt-in real OS registration evidence on disposable GitHub-hosted runners only.

No provider or foreign Body code is executed; no living organism is imported.
The environment guard prevents accidental local runs, not malicious callers.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
from test_resident_process import _prepare_resident

from mantleos import resident as r

pytestmark = pytest.mark.skipif(
    os.environ.get("MANTLE_NATIVE_SERVICE_TESTS") != "1",
    reason="native registration requires the disposable hosted-runner gate",
)


def wait_for(condition, message, timeout=40):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if condition():
                return
        except json.JSONDecodeError:
            # A read can overlap an append; retry observation, never execution.
            pass
        time.sleep(0.2)
    pytest.fail(message)


def starts(body):
    return sum(
        event["kind"] == "heartbeat.completed" and event["data"]["reason"] == "resident-startup"
        for event in body._vcw().events_after(limit=1000)[0]
    )


def test_native_registration_start_communication_stop_restart_and_removal(tmp_path):
    if os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted":
        pytest.fail("Native service test refused: not a disposable GitHub-hosted runner")
    root = Path(os.environ["RUNNER_TEMP"]).resolve()
    if not tmp_path.resolve().is_relative_to(root):
        pytest.fail("Native service test NEST must be inside RUNNER_TEMP")
    body, runner, native = _prepare_resident(tmp_path, create_runner=False)
    nest = body.paths.nest
    primer_before = hashlib.sha256(body.paths.primer.read_bytes()).hexdigest()
    native_before = native.read_bytes()
    receipt_path, _ = r._paths(nest)
    registration_id = r._registration_id(nest)
    unit_name = registration_id + ".service"
    removed = False
    try:
        print("native-phase: install")
        receipt = r.install_resident(nest, approved=True)
        assert receipt["state"] == "registered"
        assert runner.is_file()
        r._verify_registration(receipt, nest)  # Actual OS replies, no mock.
        # Installation itself must start the Heart on both platforms.
        wait_for(lambda: starts(body) == 1, "No first OS-managed full Heartbeat")

        print("native-phase: communication")
        with body.paths.communication.open("a", encoding="utf-8") as stream:
            stream.write("USER> disposable native-service message\n")
        wait_for(lambda: "APPAI> Received and recorded." in
                 body.paths.communication.read_text(encoding="utf-8"), "No native communication reply")

        print("native-phase: stop-restart")
        if os.name == "nt":
            # Explicit forced stop/start, NOT automatic recovery or graceful stop.
            r._run(["schtasks.exe", "/End", "/TN", registration_id])
            r._run(["schtasks.exe", "/Run", "/TN", registration_id])
        else:
            # systemd's on-failure policy must actually restart the process.
            old_pid = r._run([
                "systemctl", "--user", "show", unit_name, "--property=MainPID", "--value",
            ]).strip()
            assert old_pid.isdecimal() and int(old_pid) > 0
            r._run(["systemctl", "--user", "kill", "--signal=SIGKILL", "--kill-whom=main", unit_name])
        wait_for(lambda: starts(body) == 2, "OS-managed restart did not complete a new Heartbeat")
        if os.name != "nt":
            new_pid = r._run([
                "systemctl", "--user", "show", unit_name, "--property=MainPID", "--value",
            ]).strip()
            assert new_pid.isdecimal() and int(new_pid) > 0 and new_pid != old_pid
            r._run(["systemctl", "--user", "stop", unit_name])
            assert r._run([
                "systemctl", "--user", "show", unit_name, "--property=ExecMainStatus", "--value",
            ]).strip() == "0"
        else:
            r._run(["schtasks.exe", "/End", "/TN", registration_id])

        print("native-phase: remove-already-stopped")
        assert r.remove_resident(nest, approved=True)["removed"]
        removed = True
        assert not receipt_path.exists() and not runner.exists()
        if os.name == "nt":
            with pytest.raises(r.ResidentError):
                r._run(["schtasks.exe", "/Query", "/TN", registration_id, "/XML"])
        else:
            assert not r._unit_path(nest).exists()
            assert r._run([
                "systemctl", "--user", "show", unit_name, "--property=LoadState", "--value",
            ]).strip() == "not-found"
        assert not r.resident_status(nest)["installed"]
        assert body.verify()["ok"]
        assert hashlib.sha256(body.paths.primer.read_bytes()).hexdigest() == primer_before
        assert native.read_bytes() == native_before
        result = subprocess.run(
            [sys.executable, "-I", str(native)], capture_output=True, text=True, timeout=10, check=True,
        )
        assert result.stdout.strip() == "42"
        assert starts(body) == 2
    finally:
        if not removed and receipt_path.exists():
            # Never weaken ownership checks to clean up after a failed test.
            # If cleanup refuses, the failed hosted VM is discarded, not reused.
            r.remove_resident(nest, approved=True)
