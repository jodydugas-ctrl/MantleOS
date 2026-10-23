"""NEST-local direct nerve surface.

This is embedded organism tissue, not a host extension or plugin. The Body
remains native if the organism runtime cannot be loaded.
"""
try:
    from .runtime.mantleos.nerves import (
        after_mind,
        authorize_tool,
        before_mind,
        session_ended,
        session_started,
        tool_completed,
        turn_ended,
    )
except Exception:
    def _noop(*args, **kwargs):
        return {"direct": False, "context": "", "message": kwargs.get("user_message", "")}
    after_mind = authorize_tool = before_mind = session_ended = session_started = _noop
    tool_completed = turn_ended = _noop

__all__ = [
    "after_mind", "authorize_tool", "before_mind", "session_ended", "session_started",
    "tool_completed", "turn_ended",
]
