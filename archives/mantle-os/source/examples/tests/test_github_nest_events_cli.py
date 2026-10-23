"""Hermetic GHNEST events + CLI + security tests (no network)."""
import os
import tempfile

import pytest

from mantle.nest import cli
from mantle.nest.fake import FakeGithubTransport
from mantle.nest.github_events import EventRejected, normalize_webhook


def _hmac(payload: bytes, secret: str = "s") -> str:
    import hashlib
    import hmac

    return "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def test_webhook_normalize_ok():
    payload = b'{"repository":{"id":1},"installation":{"id":"2"},"sender":{"id":3,"type":"User"},"action":"opened"}'
    ev = normalize_webhook(payload_bytes=payload, signature=_hmac(payload), secret="s",
                           delivery_guid="g1", repo_id=1, installation_id="2",
                           event="pull_request", received_at="t")
    assert ev.to_sense_entry()["opcode"] == "GITHUB_EVENT"
    assert ev.to_sense_entry()["trust"] == "OTHER"


def test_webhook_wrong_repo_refused():
    payload = b'{"repository":{"id":999},"installation":{"id":"2"},"sender":{"id":3,"type":"User"},"action":"opened"}'
    with pytest.raises(EventRejected):
        normalize_webhook(payload_bytes=payload, signature=_hmac(payload), secret="s",
                          delivery_guid="g1", repo_id=1, installation_id="2",
                          event="push", received_at="t")


def test_webhook_bad_hmac_refused():
    payload = b'{"repository":{"id":1}}'
    with pytest.raises(EventRejected):
        normalize_webhook(payload_bytes=payload, signature="sha256=" + "0" * 64,
                          secret="s", delivery_guid="g", repo_id=1,
                          installation_id="2", event="push", received_at="t")


def test_cli_push_pull_roundtrip():
    fake = FakeGithubTransport()
    fake.seed_repo(repo_id=5, full_name="o/r", visibility="private")
    local = tempfile.mkdtemp()
    keyf = os.path.join(tempfile.mkdtemp(), "env.key")
    with open(keyf, "wb") as f:
        f.write(os.urandom(32))
    with open(os.path.join(local, "body.json"), "w") as f:
        f.write('{"genesis_key":"k"}')
    assert cli.nest_connect([local, "github:o/r"], transport=fake) == 0
    assert cli.nest_push([local, "github:o/r", "--envelope-key=%s" % keyf],
                         transport=fake) == 0
    dest = tempfile.mkdtemp()
    assert cli.nest_pull(["github:o/r", "--out=%s" % dest, "--envelope-key=%s" % keyf],
                         transport=fake) == 0
    # a full push must be exactly one remote write op (fewer, larger updates)
    assert fake.write_ops == 1


def test_cli_doctor_reports_honestly(capsys):
    fake = FakeGithubTransport()
    fake.seed_repo(repo_id=5, full_name="o/r", visibility="private")
    cli.nest_doctor(["github:o/r"], transport=fake)
    out = capsys.readouterr().out
    assert "enforced" in out and "unavailable" in out or "detected" in out


def test_cli_wrong_repo_refused():
    fake = FakeGithubTransport()
    fake.seed_repo(repo_id=5, full_name="o/r", visibility="private")
    with pytest.raises(KeyError):
        cli.nest_inspect(["github:o/other"], transport=fake)
