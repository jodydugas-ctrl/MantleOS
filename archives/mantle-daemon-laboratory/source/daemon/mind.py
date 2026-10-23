from __future__ import annotations

from typing import Protocol


class Mind(Protocol):
    provider_id: str

    def propose(self, context: dict) -> dict: ...


class FakeMind:
    provider_id = "fake-offline-v1"

    def propose(self, context: dict) -> dict:
        return {"opcode": "MIND_NOTE", "content": {"summary": "deterministic proposal",
                "event_count": len(context.get("events", []))}}


class AlternateFakeMind:
    """A second deterministic provider-shaped implementation for replacement tests."""

    provider_id = "fake-offline-v2"

    def propose(self, context: dict) -> dict:
        return {"opcode": "MIND_NOTE", "content": {"summary": "alternate deterministic proposal",
                "context_events": len(context.get("events", []))}}


class ProposalAdmission:
    def __init__(self, body):
        self.body = body

    def admit(self, proposal: dict) -> dict:
        if proposal.get("opcode") != "MIND_NOTE" or not isinstance(proposal.get("content"), dict):
            self.body.immune.event("mind_write_refused", {"reason": "invalid proposal"})
            return {"admitted": False, "reason": "invalid proposal"}
        entry = self.body.memory.append("events", "MIND_NOTE", proposal["content"], "fake-mind")
        return {"admitted": True, "entry_id": entry["id"]}
