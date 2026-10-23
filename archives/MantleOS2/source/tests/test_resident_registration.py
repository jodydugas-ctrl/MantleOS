"""Registration boundary tests; OS replies are fixtures, not native certification."""

from __future__ import annotations

import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from unittest import mock

import pytest

from mantleos import resident as r


@pytest.fixture
def registration(tmp_path, monkeypatch):
    monkeypatch.setattr(r, "PLATFORM", "nt")
    package = tmp_path / "mantle" / "runtime" / "mantleos"
    package.mkdir(parents=True)
    for name in ("__init__.py", "cli.py"):
        (package / name).write_bytes(b"")
    with (
        mock.patch.object(r.MantleBody, "is_born", new_callable=mock.PropertyMock, return_value=True),
        mock.patch.object(r, "_run", return_value="") as run,
        mock.patch.object(r, "_verify_registration"),
    ):
        receipt = r.install_resident(tmp_path, approved=True)
        assert "/F" not in run.call_args_list[0].args[0]
        assert run.call_args.args[0][1] == "/Run"
    return tmp_path, receipt


def task_xml(nest, receipt):
    task = ET.Element("Task", xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task")
    principal = ET.SubElement(ET.SubElement(task, "Principals"), "Principal")
    ET.SubElement(principal, "UserId").text = "S-1-5-21-123"
    ET.SubElement(principal, "RunLevel").text = "LeastPrivilege"
    action = ET.SubElement(ET.SubElement(task, "Actions"), "Exec")
    ET.SubElement(action, "Command").text = receipt["python"]
    ET.SubElement(action, "Arguments").text = subprocess.list2cmdline(["-I", str(r._paths(nest)[1])])
    return ET.tostring(task, encoding="unicode")


def test_windows_live_shape_is_checked_before_stop_and_delete(registration, monkeypatch):
    nest, receipt = registration
    responses = [task_xml(nest, receipt), '"user","S-1-5-21-123"', "", ""]
    with mock.patch.object(r, "_run", side_effect=responses) as run:
        assert r.remove_resident(nest, approved=True)["removed"]
    assert [call.args[0][1] for call in run.call_args_list] == ["/Query", "/user", "/End", "/Delete"]
    assert not r._paths(nest)[0].exists()


@pytest.mark.parametrize("level", [None, "", "HighestAvailable", "unknown"])
def test_windows_omitted_default_privilege_but_not_explicit_invalid_values(registration, level):
    nest, receipt = registration
    task = ET.fromstring(task_xml(nest, receipt))
    principal = task.find("{*}Principals/{*}Principal")
    element = principal.find("{*}RunLevel")
    if level is None:
        principal.remove(element)
    else:
        element.text = level
    with mock.patch.object(r, "_run", side_effect=[
        ET.tostring(task, encoding="unicode"), '"user","S-1-5-21-123"',
    ]):
        if level is None:
            r._verify_registration(receipt, nest)
        else:
            with pytest.raises(r.ResidentError, match="does not match"):
                r._verify_registration(receipt, nest)


@pytest.mark.parametrize("change", ["command", "arguments", "owner", "privilege", "extra-action"])
def test_windows_registration_drift_never_stops_or_deletes(registration, change):
    nest, receipt = registration
    task = ET.fromstring(task_xml(nest, receipt))
    paths = {
        "command": "{*}Actions/{*}Exec/{*}Command",
        "arguments": "{*}Actions/{*}Exec/{*}Arguments",
        "owner": "{*}Principals/{*}Principal/{*}UserId",
        "privilege": "{*}Principals/{*}Principal/{*}RunLevel",
    }
    if change == "extra-action":
        ET.SubElement(task.find("{*}Actions"), "Exec")
    else:
        task.find(paths[change]).text = "unrelated"
    with (
        mock.patch.object(r, "_run", side_effect=[
            ET.tostring(task, encoding="unicode"), '"user","S-1-5-21-123"',
        ]) as run,
        pytest.raises(r.ResidentError, match="does not match"),
    ):
        r.remove_resident(nest, approved=True)
    assert all(call.args[0][1] in ("/Query", "/user") for call in run.call_args_list)
    assert all(path.is_file() for path in r._paths(nest))


@pytest.mark.parametrize("raw", ["<invalid", "<!DOCTYPE Task><Task/>", "x" * 131_073],
                         ids=["malformed", "doctype", "oversize"])
def test_task_xml_is_bounded_and_rejects_entities(registration, raw):
    nest, receipt = registration
    with (
        mock.patch.object(r, "_run", return_value=raw) as run,
        pytest.raises(r.ResidentError, match="does not match"),
    ):
        r._verify_registration(receipt, nest)
    assert run.call_count == 1


@pytest.mark.parametrize("field,value", [
    ("nest", "elsewhere"), ("runner", "elsewhere"), ("registration_id", "Other-task"),
    ("external_registration", "Other-task"), ("organ_runtime", "elsewhere"),
    ("mechanism", "systemd-user-service"), ("privilege", "elevated"),
    ("isolated_python", 1), ("python", "relative-python"), ("state", []),
])
def test_receipt_cannot_redirect_removal(registration, field, value):
    nest, receipt = registration
    receipt[field] = value
    r._paths(nest)[0].write_text(json.dumps(receipt), encoding="utf-8")
    with mock.patch.object(r, "_run") as run:
        with pytest.raises(r.ResidentError, match="unreadable"):
            r.remove_resident(nest, approved=True)
        run.assert_not_called()


@pytest.mark.parametrize("raw", [b"[]", b"\xff", b'{"schema":1,"schema":2}', b"x" * 32_769],
                         ids=["array", "encoding", "duplicate", "oversize"])
def test_unreadable_receipt_does_not_touch_os(registration, raw):
    nest, _ = registration
    r._paths(nest)[0].write_bytes(raw)
    with mock.patch.object(r, "_run") as run:
        with pytest.raises(r.ResidentError):
            r.remove_resident(nest, approved=True)
        run.assert_not_called()


def test_existing_local_registration_is_not_overwritten(registration):
    nest, _ = registration
    before = [path.read_bytes() for path in r._paths(nest)]
    with (
        mock.patch.object(r.MantleBody, "is_born", new_callable=mock.PropertyMock, return_value=True),
        mock.patch.object(r, "_run") as run,
    ):
        with pytest.raises(r.ResidentError, match="already exists"):
            r.install_resident(nest, approved=True)
        run.assert_not_called()
    assert before == [path.read_bytes() for path in r._paths(nest)]


def test_failed_registration_preserves_pending_evidence(registration):
    nest, _ = registration
    for path in r._paths(nest):
        path.unlink()
    with (
        mock.patch.object(r.MantleBody, "is_born", new_callable=mock.PropertyMock, return_value=True),
        mock.patch.object(r, "_run", side_effect=r.ResidentError("registration refused")) as run,
        pytest.raises(r.ResidentError, match="registration refused"),
    ):
        r.install_resident(nest, approved=True)
    assert run.call_count == 1  # No speculative rollback or retry.
    status = r.resident_status(nest)
    assert status["state"] == "registration-pending"
    assert status["installed"] is False
    assert status["runner_available"] is True
    assert status["running"] == "unknown"


def test_failed_windows_start_retains_intent_after_verified_creation(registration):
    nest, _ = registration
    for path in r._paths(nest):
        path.unlink()
    with (
        mock.patch.object(r.MantleBody, "is_born", new_callable=mock.PropertyMock, return_value=True),
        mock.patch.object(r, "_verify_registration") as verify,
        mock.patch.object(r, "_run", side_effect=["", r.ResidentError("start failed")]) as run,
        pytest.raises(r.ResidentError, match="start failed"),
    ):
        r.install_resident(nest, approved=True)
    verify.assert_called_once()
    assert [call.args[0][1] for call in run.call_args_list] == ["/Create", "/Run"]
    assert r.resident_status(nest)["state"] == "registration-pending"


def test_windows_verification_failure_prevents_start(registration):
    nest, _ = registration
    for path in r._paths(nest):
        path.unlink()
    with (
        mock.patch.object(r.MantleBody, "is_born", new_callable=mock.PropertyMock, return_value=True),
        mock.patch.object(r, "_verify_registration", side_effect=r.ResidentError("verification failed")),
        mock.patch.object(r, "_run", return_value="") as run,
        pytest.raises(r.ResidentError, match="verification failed"),
    ):
        r.install_resident(nest, approved=True)
    assert run.call_count == 1 and run.call_args.args[0][1] == "/Create"
    assert r.resident_status(nest)["state"] == "registration-pending"


def test_legacy_receipt_remains_readable_and_missing_runner_does_not_hide_registration(registration):
    nest, receipt = registration
    receipt.pop("state")
    path, runner = r._paths(nest)
    path.write_text(json.dumps(receipt), encoding="utf-8")
    original = path.read_bytes()
    runner.unlink()
    status = r.resident_status(nest)
    assert status["installed"] and not status["runner_available"]
    assert status["registration_evidence"] == "receipt-only"
    assert path.read_bytes() == original
    with mock.patch.object(r, "_run", side_effect=[
        task_xml(nest, receipt), '"user","S-1-5-21-123"', "", "",
    ]):
        assert r.remove_resident(nest, approved=True)["removed"]


def test_changed_runner_is_preserved_without_os_calls(registration):
    nest, _ = registration
    r._paths(nest)[1].write_bytes(b"changed runner")
    with mock.patch.object(r, "_run") as run:
        with pytest.raises(r.ResidentError, match="runner changed"):
            r.remove_resident(nest, approved=True)
        run.assert_not_called()
    assert r._paths(nest)[1].read_bytes() == b"changed runner"


def test_stop_failure_preserves_receipt_and_never_deletes_task(registration):
    nest, receipt = registration
    before = [path.read_bytes() for path in r._paths(nest)]
    with (
        mock.patch.object(r, "_run", side_effect=[
            task_xml(nest, receipt), '"user","S-1-5-21-123"', r.ResidentError("stop failed"),
        ]) as run,
        pytest.raises(r.ResidentError, match="stop failed"),
    ):
        r.remove_resident(nest, approved=True)
    assert not any("/Delete" in call.args[0] for call in run.call_args_list)
    assert before == [path.read_bytes() for path in r._paths(nest)]


def test_receipt_directory_is_not_reported_as_absent(registration):
    nest, _ = registration
    path, _ = r._paths(nest)
    path.unlink()
    path.mkdir()
    with pytest.raises(r.ResidentError, match="not a regular file"):
        r.resident_status(nest)


@pytest.mark.parametrize("fault", ["bytes", "fragment", "dropin", "none"])
def test_linux_unit_and_loaded_configuration_must_match(registration, monkeypatch, fault):
    nest, receipt = registration
    monkeypatch.setattr(r, "PLATFORM", "posix")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(nest / "config"))
    unit = r._unit_path(nest)
    r._new_file(unit, r._unit_text(receipt["python"], r._paths(nest)[1]).encode())
    if fault == "bytes":
        unit.write_bytes(b"unrelated unit")
    replies = [str(unit) if fault != "fragment" else "/other/unit", "override" if fault == "dropin" else ""]
    with mock.patch.object(r, "_run", side_effect=replies) as run:
        if fault == "none":
            r._verify_registration(receipt, nest)
        else:
            with pytest.raises(r.ResidentError):
                r._verify_registration(receipt, nest)
        assert all(call.args[0][2] == "show" for call in run.call_args_list)


def test_linux_rejects_overrides_before_service_start(registration, monkeypatch):
    nest, _ = registration
    for path in r._paths(nest):
        path.unlink()
    monkeypatch.setattr(r, "PLATFORM", "posix")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(nest / "config"))
    unit = r._unit_path(nest)
    with (
        mock.patch.object(r.MantleBody, "is_born", new_callable=mock.PropertyMock, return_value=True),
        mock.patch.object(r, "_run", side_effect=["", str(unit), "overridden"]) as run,
        pytest.raises(r.ResidentError, match="overridden"),
    ):
        r.install_resident(nest, approved=True)
    assert not any("enable" in call.args[0] for call in run.call_args_list)
    assert r.resident_status(nest)["state"] == "registration-pending"


def test_linux_existing_unit_is_not_replaced(registration, monkeypatch):
    nest, _ = registration
    for path in r._paths(nest):
        path.unlink()
    monkeypatch.setattr(r, "PLATFORM", "posix")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(nest / "config"))
    unit = r._unit_path(nest)
    r._new_file(unit, b"unrelated unit")
    with (
        mock.patch.object(r.MantleBody, "is_born", new_callable=mock.PropertyMock, return_value=True),
        mock.patch.object(r, "_run") as run,
    ):
        with pytest.raises(r.ResidentError, match="replacement refused"):
            r.install_resident(nest, approved=True)
        run.assert_not_called()
    assert unit.read_bytes() == b"unrelated unit"
    assert not r._paths(nest)[0].exists()


@pytest.mark.parametrize("char", ["%", "$", "\n", "\r", "\"", "'"])
def test_unsupported_systemd_expansion_is_refused(tmp_path, char):
    with pytest.raises(r.ResidentError, match="escaping profile"):
        r._unit_text(sys.executable, tmp_path / ("runner" + char))


def test_redirected_paths_are_refused(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation unavailable to test account")
    with pytest.raises(r.ResidentError, match="redirected"):
        r.resident_status(link)
    assert not list(target.iterdir())


@pytest.mark.parametrize("failure", [
    OSError("sensitive output"), subprocess.TimeoutExpired("sensitive command", 30),
    subprocess.CalledProcessError(1, "sensitive command", stderr="sensitive output"),
])
def test_os_commands_are_noninteractive_bounded_and_errors_are_redacted(failure):
    with (
        mock.patch.object(r.subprocess, "run", side_effect=failure) as run,
        pytest.raises(r.ResidentError) as caught,
    ):
        r._run(["test-command"])
    assert "sensitive" not in str(caught.value)
    assert run.call_args.kwargs["timeout"] == 30
    assert run.call_args.kwargs["stdin"] == subprocess.DEVNULL
    assert "shell" not in run.call_args.kwargs
