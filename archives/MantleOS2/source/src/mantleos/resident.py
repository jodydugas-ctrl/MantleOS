"""Explicit user-level registration for a NEST-contained resident Heart."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import shlex
import signal
import subprocess
import sys
import threading
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from .runtime import MantleBody, MantleError, _atomic_write, utc_now

PLATFORM = os.name


class ResidentError(MantleError):
    pass


def watch_with_signals(
    body: MantleBody, *, interval: float, heartbeat_interval: float
) -> dict[str, Any]:
    """CLI-only cooperative stop; embedded hosts retain their own handlers.

    The handler changes one flag only: no locks, storage, provider calls or
    exceptions in a potentially interrupted Heartbeat. OS force termination
    remains distinct from this best-effort between-Heartbeat exit.
    """
    if threading.current_thread() is not threading.main_thread():
        raise ResidentError("Signal-managed watch requires the main thread")
    requested_signal: int | None = None
    previous = {}

    def request_stop(signum, _frame):
        nonlocal requested_signal
        if requested_signal is None:
            requested_signal = signum

    signals = [signal.SIGINT, signal.SIGTERM]
    if hasattr(signal, "SIGBREAK"):
        signals.append(signal.SIGBREAK)
    try:
        for signum in signals:
            previous[signum] = signal.signal(signum, request_stop)
        body.watch(
            interval=interval,
            heartbeat_interval=heartbeat_interval,
            stop_requested=lambda: requested_signal is not None,
        )
        return {
            "status": "stopped",
            "reason": (
                signal.Signals(requested_signal).name if requested_signal is not None else "watch-returned"
            ),
            "shutdown": "cooperative-between-heartbeats",
        }
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


def _registration_id(nest: Path) -> str:
    suffix = hashlib.sha256(str(nest).casefold().encode("utf-8")).hexdigest()[:12]
    return f"MantleOS2-{suffix}"


def _paths(nest: Path) -> tuple[Path, Path]:
    root = nest / ".mantle" / "resident"
    return root / "registration.json", root / "run-heart.py"


def _runner_text(nest: Path) -> str:
    return (
        "from pathlib import Path\n"
        "import sys\n\n"
        f"runtime = Path({str(nest)!r}) / 'mantle' / 'runtime'\n"
        "package = runtime / 'mantleos'\n"
        "if not all((package / name).is_file() for name in ('__init__.py', 'cli.py')):\n"
        "    raise SystemExit('Resident Heart stopped: NEST-local organs are missing')\n"
        "if runtime.resolve() != runtime or package.resolve() != package:\n"
        "    raise SystemExit('Resident Heart stopped: organ path is redirected')\n"
        "sys.path.insert(0, str(runtime))\n"
        "from mantleos.cli import main\n\n"
        f"raise SystemExit(main(['--nest', {str(nest)!r}, 'watch']))\n"
    )


def _run(arguments: list[str]) -> str:
    try:
        result = subprocess.run(
            arguments, check=True, capture_output=True, text=True, timeout=30,
            stdin=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ResidentError(
            f"Resident control failed ({type(exc).__name__}); inspect registration state"
        ) from None
    return result.stdout


def _plain_path(path: Path) -> Path:
    path = path.absolute()
    if path.resolve() != path or any(ord(char) < 32 for char in str(path)):
        raise ResidentError("Resident path is redirected or contains control characters")
    return path


def _unit_path(nest: Path) -> Path:
    config = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    if not config.is_absolute():
        raise ResidentError("Resident configuration directory must be absolute")
    return _plain_path(config / "systemd" / "user" / f"{_registration_id(nest)}.service")


def _unit_text(python: str, runner: Path) -> str:
    # Existing v2 format is retained; exotic systemd expansion paths are refused
    # until a separately tested unit-escaping profile is available.
    if any(c in python + str(runner) for c in "%$\n\r\"'"):
        raise ResidentError("Resident unit path needs an unsupported escaping profile")
    return (
        "[Unit]\nDescription=MantleOS 2 resident Heart\n\n"
        "[Service]\nType=simple\n"
        f"ExecStart={shlex.quote(python)} -I {shlex.quote(str(runner))}\nRestart=on-failure\n\n"
        "[Install]\nWantedBy=default.target\n"
    )


def _new_file(path: Path, data: bytes) -> None:
    _plain_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def _receipt_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate resident receipt field")
        value[key] = item
    return value


def _read_bounded(path: Path, limit: int = 32_768) -> bytes:
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ResidentError("Resident artifact exceeds its size limit")
    return data


def _verify_registration(receipt: dict[str, Any], nest: Path) -> None:
    """Check current OS registration before treating it as this NEST's target."""
    registration_id = _registration_id(nest)
    _, runner = _paths(nest)
    if PLATFORM == "nt":
        raw = _run(["schtasks.exe", "/Query", "/TN", registration_id, "/XML"])
        try:
            if len(raw) > 131_072 or "<!DOCTYPE" in raw or "<!ENTITY" in raw:
                raise ValueError("unsupported task XML")
            task = ET.fromstring(raw)
            actions = task.find("{*}Actions")
            principals = task.findall("{*}Principals/{*}Principal")
            if actions is None or len(actions) != 1 or len(principals) != 1:
                raise ValueError("unexpected task structure")
            action = actions[0]
            if action.tag.rsplit("}", 1)[-1] != "Exec":
                raise ValueError("unexpected task action")
            command = action.findtext("{*}Command", "")
            arguments = action.findtext("{*}Arguments", "")
            if command != receipt["python"] or arguments != subprocess.list2cmdline(["-I", str(runner)]):
                raise ValueError("task command drift")
            rows = list(csv.reader(io.StringIO(_run(["whoami", "/user", "/fo", "csv", "/nh"]))))
            sid = rows[0][1]
            if not sid.startswith("S-1-") or principals[0].findtext("{*}UserId") != sid:
                raise ValueError("task owner drift")
            # Windows may omit the optional default-valued element on export.
            # Only absence defaults; explicit empty/unknown/elevated values fail.
            if principals[0].findtext("{*}RunLevel", "LeastPrivilege") != "LeastPrivilege":
                raise ValueError("task privilege drift")
        except (ValueError, IndexError, ET.ParseError) as exc:
            raise ResidentError("Resident task does not match this NEST and current owner") from exc
    else:
        unit = _unit_path(nest)
        expected = _unit_text(receipt["python"], runner).encode("utf-8")
        if not unit.is_file() or _read_bounded(unit) != expected:
            raise ResidentError("Resident unit is missing or changed; removal refused")
        loaded = _run([
            "systemctl", "--user", "show", unit.name, "--property=FragmentPath", "--value",
        ]).strip()
        overrides = _run([
            "systemctl", "--user", "show", unit.name, "--property=DropInPaths", "--value",
        ]).strip()
        if loaded != str(unit) or overrides:
            raise ResidentError("Loaded resident unit is redirected or overridden")


def install_resident(nest: str | Path, *, approved: bool) -> dict[str, Any]:
    if not approved:
        raise ResidentError("Resident Heart installation requires --approve-install")
    nest = _plain_path(Path(nest))
    if not MantleBody(nest).is_born:
        raise ResidentError("A resident Heart can be installed only after birth")
    runtime = nest / "mantle" / "runtime"
    package = runtime / "mantleos"
    if not all((package / name).is_file() for name in ("__init__.py", "cli.py")):
        raise ResidentError("Resident Heart requires NEST-local organs; reconstruct the Body delta")
    if runtime.resolve() != runtime or package.resolve() != package:
        raise ResidentError("Resident Heart organ path is redirected")
    registration_path, runner = _paths(nest)
    for path in (registration_path, runner):
        _plain_path(path)
        if path.exists():
            raise ResidentError("Resident construction already exists; inspect it before retrying")
    registration_id = _registration_id(nest)
    if PLATFORM == "nt":
        mechanism, external = "windows-user-logon-task", registration_id
    else:
        mechanism, external = "systemd-user-service", str(_unit_path(nest))
        if Path(external).exists():
            raise ResidentError("Resident unit already exists; replacement refused")
        unit_text = _unit_text(sys.executable, runner)
    receipt = {
        "schema": "mantle.resident-heart.v2",
        "registration_id": registration_id,
        "mechanism": mechanism,
        "external_registration": external,
        "runner": str(runner),
        "nest": str(nest),
        "installed_at": utc_now(),
        "authority": "explicit-user-approval",
        "privilege": "user-level",
        "organ_runtime": str(runtime),
        "python": sys.executable,
        "isolated_python": True,
        "state": "registration-pending",
    }
    # Preserve intent before OS mutation. Failure keeps evidence; never blindly
    # retry an uncertain registration or delete a pre-existing host artifact.
    _new_file(registration_path, (json.dumps(receipt, indent=2) + "\n").encode("utf-8"))
    _new_file(runner, _runner_text(nest).encode("utf-8"))
    if PLATFORM == "nt":
        command = subprocess.list2cmdline([sys.executable, "-I", str(runner)])
        _run(
            [
                "schtasks.exe",
                "/Create",
                "/TN",
                registration_id,
                "/SC",
                "ONLOGON",
                "/TR",
                command,
                "/RL",
                "LIMITED",
            ]
        )
        _verify_registration(receipt, nest)
        _run(["schtasks.exe", "/Run", "/TN", registration_id])
    else:
        unit = Path(external)
        _new_file(unit, unit_text.encode("utf-8"))
        _run(["systemctl", "--user", "daemon-reload"])
        # Refuse redirected/overridden units before starting any service.
        _verify_registration(receipt, nest)
        _run(["systemctl", "--user", "enable", "--now", unit.name])
    receipt["state"] = "registered"
    _plain_path(registration_path.with_name(registration_path.name + ".tmp"))
    if registration_path.with_name(registration_path.name + ".tmp").exists():
        raise ResidentError("Resident receipt temporary file already exists")
    _atomic_write(
        registration_path,
        (json.dumps(receipt, indent=2, ensure_ascii=False) + "\n").encode("utf-8"),
    )
    return receipt


def resident_status(nest: str | Path) -> dict[str, Any]:
    nest = _plain_path(Path(nest))
    registration_path, runner = _paths(nest)
    _plain_path(registration_path)
    _plain_path(runner)
    if not registration_path.exists():
        return {"installed": False, "nest": str(nest)}
    if not registration_path.is_file():
        raise ResidentError("Resident receipt is not a regular file")
    try:
        raw = _read_bounded(registration_path)
        receipt = json.loads(raw.decode("utf-8"), object_pairs_hook=_receipt_object)
        expected = {
            "schema": "mantle.resident-heart.v2", "nest": str(nest),
            "registration_id": _registration_id(nest), "runner": str(runner),
            "organ_runtime": str(nest / "mantle" / "runtime"),
            "authority": "explicit-user-approval", "privilege": "user-level", "isolated_python": True,
            "mechanism": "windows-user-logon-task" if PLATFORM == "nt" else "systemd-user-service",
            "external_registration": _registration_id(nest) if PLATFORM == "nt" else str(_unit_path(nest)),
        }
        if not isinstance(receipt, dict) or any(receipt.get(k) != v for k, v in expected.items()):
            raise ValueError("receipt target mismatch")
        if receipt["isolated_python"] is not True:
            raise ValueError("invalid isolation flag")
        python = receipt.get("python")
        if not isinstance(python, str) or not Path(python).is_absolute() or any(ord(c) < 32 for c in python):
            raise ValueError("invalid interpreter path")
        if receipt.get("state", "registered") not in ("registered", "registration-pending"):
            raise ValueError("invalid registration state")
    except (OSError, ValueError, RecursionError) as exc:
        raise ResidentError("Resident Heart receipt is unreadable") from exc
    return {
        **receipt, "installed": receipt.get("state", "registered") == "registered",
        "runner_available": runner.is_file(), "registration_evidence": "receipt-only",
        "running": "unknown", "receipt_present": True,
    }


def remove_resident(nest: str | Path, *, approved: bool) -> dict[str, Any]:
    if not approved:
        raise ResidentError("Resident Heart removal requires --approve-remove")
    nest = _plain_path(Path(nest))
    receipt = resident_status(nest)
    if not receipt.get("receipt_present"):
        return {"removed": False, "reason": "not-installed", "nest": str(nest)}
    _, runner = _paths(nest)
    if runner.exists() and _read_bounded(runner) != _runner_text(nest).encode("utf-8"):
        raise ResidentError("Resident runner changed; removal refused")
    _verify_registration(receipt, nest)
    if receipt["mechanism"] == "windows-user-logon-task":
        _run(["schtasks.exe", "/End", "/TN", _registration_id(nest)])
        _run(["schtasks.exe", "/Delete", "/TN", receipt["registration_id"], "/F"])
    else:
        unit = _unit_path(nest)
        _run(["systemctl", "--user", "disable", "--now", unit.name])
        if unit.is_file():
            unit.unlink()
        _run(["systemctl", "--user", "daemon-reload"])
    registration_path, runner = _paths(nest)
    if runner.is_file():
        runner.unlink()
    if registration_path.is_file():
        registration_path.unlink()
    return {"removed": True, "registration_id": receipt["registration_id"], "nest": str(nest)}
