from __future__ import annotations

from mantleos import nerves


class _FakeBody:
    def __init__(self, *, pending: bool, physiology: str = "active"):
        self.pending = pending
        self.physiology = physiology
        self.observations = []
        self.recovered = False

    def host_heartbeat_pending(self, session_id, turn_id):
        assert session_id == "session"
        assert turn_id == "turn"
        return self.pending

    def status(self):
        return {"physiology": {"state": self.physiology}}

    def record_observation(self, layer, kind, data):
        self.observations.append((layer, kind, data))

    def recover_host_heartbeats(self):
        self.recovered = True
        return []


def test_unborn_or_absent_body_is_native_noop(monkeypatch, tmp_path):
    monkeypatch.setenv("MANTLE_NEST", str(tmp_path))
    result = nerves.before_mind(
        user_message="ordinary host turn",
        session_id="s",
        turn_id="t",
        surface="cli",
    )
    assert result == {"direct": False, "context": "", "message": "ordinary host turn"}


def test_explicit_route_is_not_inferred_from_agentic_body():
    assert nerves._direct_message("hello") == (False, "hello")
    assert nerves._direct_message("/mantle hello") == (True, "hello")


def test_native_tool_dispatch_is_unchanged(monkeypatch):
    body = _FakeBody(pending=False)
    monkeypatch.setattr(nerves, "_body", lambda: body)
    result = nerves.authorize_tool(
        tool_name="terminal",
        arguments={"command": "value-never-recorded"},
        session_id="session",
        turn_id="turn",
    )
    assert result is None
    assert body.observations == []


def test_appai_tool_dispatch_uses_body_authority_without_raw_arguments(monkeypatch):
    body = _FakeBody(pending=True)
    monkeypatch.setattr(nerves, "_body", lambda: body)
    result = nerves.authorize_tool(
        tool_name="terminal",
        arguments={"command": "value-never-recorded"},
        session_id="session",
        turn_id="turn",
    )
    assert result is None
    layer, kind, data = body.observations[0]
    assert (layer, kind) == ("actions", "appai.limb.proposed")
    assert data["authority"] == "native-body-guardrails"
    assert data["argument_keys"] == ["command"]
    assert "value-never-recorded" not in str(data)


def test_appai_tool_dispatch_is_refused_in_stasis(monkeypatch):
    body = _FakeBody(pending=True, physiology="stasis")
    monkeypatch.setattr(nerves, "_body", lambda: body)
    result = nerves.authorize_tool(
        tool_name="terminal",
        arguments={},
        session_id="session",
        turn_id="turn",
    )
    assert result == "Mantle Body refused AppAI Limb action while physiology is stasis"
    assert body.observations[0][2]["physiology"] == "stasis"


def test_actual_session_end_recovers_pending_heartbeats(monkeypatch):
    body = _FakeBody(pending=False)
    monkeypatch.setattr(nerves, "_body", lambda: body)
    nerves.session_ended(session_id="session", surface="cli", reason="shutdown")
    assert body.recovered is True
    assert body.observations == [
        (
            "layer-0",
            "body.session.ended",
            {"session_id": "session", "surface": "cli", "reason": "shutdown"},
        )
    ]
