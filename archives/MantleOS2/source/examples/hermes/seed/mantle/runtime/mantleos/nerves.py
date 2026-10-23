"""Direct host-to-Body nerve endpoints.

Host source calls these functions directly at mapped lifecycle seams.  They
never register with a plugin manager.  Every endpoint fails closed for motor
actions and fails harmlessly for observation so the native Body remains usable.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .runtime import MantleBody


def _nest() -> Path:
    configured = os.environ.get("MANTLE_NEST")
    if configured:
        return Path(configured).resolve()
    return Path.cwd().resolve()


def _body() -> MantleBody | None:
    try:
        body = MantleBody(_nest())
        return body if body.is_born else None
    except Exception:
        return None


def _direct_message(message: Any) -> tuple[bool, str]:
    if not isinstance(message, str):
        return False, ""
    stripped = message.lstrip()
    if stripped == "/mantle":
        return True, ""
    if stripped.startswith("/mantle "):
        return True, stripped[len("/mantle ") :]
    return False, message


def sense(kind: str, data: dict[str, Any], *, layer: str = "layer-0") -> None:
    body = _body()
    if body is not None:
        body.record_observation(layer, kind, data)


def session_started(*, session_id: str, model: str, surface: str) -> None:
    body = _body()
    if body is None:
        return
    body.recover_host_heartbeats()
    sense(
        "body.session.started",
        {"session_id": session_id, "model": model, "surface": surface},
    )


def before_mind(
    *,
    user_message: Any,
    session_id: str,
    turn_id: str,
    surface: str,
) -> dict[str, Any]:
    """Sense a committed host turn and prepare Primer-first AppAI context."""
    direct, message = _direct_message(user_message)
    body = _body()
    if body is None:
        return {"direct": False, "context": "", "message": message}
    if not direct:
        sense(
            "body.user.turn",
            {"session_id": session_id, "surface": surface, "message": message},
        )
        return {"direct": False, "context": "", "message": message}

    sense(
        "communication.user.message",
        {"session_id": session_id, "surface": surface, "message": message},
        layer="communication",
    )
    beat = body.begin_host_heartbeat(session_id, turn_id)
    update = body.prepare_mind_update(session_id, turn_id)
    context = body.primer_context(update["events"])
    return {
        "direct": True,
        "context": context,
        "message": message,
        "heartbeat_id": beat["heartbeat_id"],
    }


def after_mind(
    *,
    user_message: Any,
    assistant_response: Any,
    session_id: str,
    turn_id: str,
    surface: str,
) -> None:
    direct, message = _direct_message(user_message)
    body = _body()
    if body is None:
        return
    body.record_observation(
        "communication" if direct else "layer-0",
        "appai.mind.turn" if direct else "body.native-mind.turn",
        {
            "session_id": session_id,
            "surface": surface,
            "user_message": message,
            "assistant_response": str(assistant_response or ""),
        },
    )
    if direct:
        body.acknowledge_mind_update(session_id, turn_id)
        body.complete_host_heartbeat(session_id, turn_id, mind_status="responded")


def tool_completed(
    *,
    tool_name: str,
    arguments: dict[str, Any] | None,
    status: str,
    duration_ms: int,
    session_id: str = "",
    turn_id: str = "",
) -> None:
    """Record semantic tool completion without copying values or results."""
    values = arguments or {}
    digest = hashlib.sha256(
        json.dumps(values, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    body = _body()
    if body is None:
        return
    appai_action = body.host_heartbeat_pending(session_id, turn_id)
    body.record_observation(
        "actions" if appai_action else "layer-0",
        "appai.limb.completed" if appai_action else "body.tool.completed",
        {
            "tool": tool_name,
            "argument_keys": sorted(str(key) for key in values),
            "arguments_sha256": digest,
            "status": status,
            "duration_ms": int(duration_ms),
        },
    )


def authorize_tool(
    *,
    tool_name: str,
    arguments: dict[str, Any] | None,
    session_id: str,
    turn_id: str,
) -> str | None:
    """Route an AppAI action proposal through Body-owned native authority."""
    body = _body()
    if body is None or not body.host_heartbeat_pending(session_id, turn_id):
        return None
    values = arguments or {}
    digest = hashlib.sha256(
        json.dumps(values, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    physiology = body.status().get("physiology", {}).get("state", "active")
    body.record_observation(
        "actions",
        "appai.limb.proposed",
        {
            "tool": tool_name,
            "argument_keys": sorted(str(key) for key in values),
            "arguments_sha256": digest,
            "authority": "native-body-guardrails",
            "physiology": physiology,
        },
    )
    if physiology != "active":
        return f"Mantle Body refused AppAI Limb action while physiology is {physiology}"
    return None


def turn_ended(
    *,
    session_id: str,
    turn_id: str,
    completed: bool,
    failed: bool,
    interrupted: bool,
) -> None:
    body = _body()
    if body is None:
        return
    sense(
        "body.turn.ended",
        {
            "session_id": session_id,
            "completed": completed,
            "failed": failed,
            "interrupted": interrupted,
        },
    )
    try:
        state = "responded" if completed and not failed and not interrupted else "unavailable"
        body.complete_host_heartbeat(session_id, turn_id, mind_status=state)
    except Exception:
        pass


def session_ended(*, session_id: str, surface: str, reason: str) -> None:
    """Record an actual host session boundary and close interrupted Heartbeats."""
    body = _body()
    if body is None:
        return
    body.recover_host_heartbeats()
    body.record_observation(
        "layer-0",
        "body.session.ended",
        {"session_id": session_id, "surface": surface, "reason": reason},
    )
