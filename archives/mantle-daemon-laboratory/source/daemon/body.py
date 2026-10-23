from __future__ import annotations

from pathlib import Path

from .constitution import validate
from .security import redact
from .stack import Stack, make_entry


class Memory:
    def __init__(self, body: "Body"):
        self.body = body

    def append(self, band: str, opcode: str, content: dict, source: str = "") -> dict:
        return self.body.stack.append(band, make_entry(opcode, "BODY", content, source))

    def events(self) -> list[dict]:
        return self.body.stack.read("events")


class Immune:
    def __init__(self, body: "Body"):
        self.body = body
        self.events: list[dict] = []

    def verify(self) -> list[str]:
        problems = self.body.stack.verify()
        for problem in problems:
            self.event("integrity", {"problem": problem})
        return problems

    def event(self, kind: str, detail: dict) -> None:
        event = {"kind": kind, "detail": redact(detail)}
        self.events.append(event)
        try:
            self.body.stack.append("immune", "IMMUNE", event, "immune")
        except Exception:
            pass


class Senses:
    def __init__(self, body: "Body"):
        self.body = body

    def inhale(self, event: dict) -> dict:
        if not isinstance(event, dict) or not event.get("event_type"):
            raise ValueError("Senses requires a structured event_type")
        return self.body.memory.append("events", "SENSE", event, "senses")


class Nervous:
    def __init__(self, body: "Body"):
        self.body = body

    def assemble(self) -> dict:
        identity = self.body.identity["stable_id"]
        return {"stable_id": identity, "events": self.body.memory.events()[-10:], "mind": "absent"}


class Limbs:
    def __init__(self, body: "Body"):
        self.body = body

    def receipt_only(self, content: dict) -> dict:
        return {"action": "receipt-only", "content": content}


class Body:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.stack = Stack(self.root)
        self.identity = __import__("json").loads((self.root / "genome/identity.json").read_text(encoding="utf-8"))
        self.memory = Memory(self)
        self.immune = Immune(self)
        self.senses = Senses(self)
        self.nervous = Nervous(self)
        self.limbs = Limbs(self)

    @classmethod
    def reconstruct(cls, root: Path) -> "Body":
        problems = validate(Path(root))
        if problems:
            raise ValueError("constitutional validation failed: " + "; ".join(problems))
        body = cls(root)
        problems = body.stack.verify()
        if problems:
            raise ValueError("VCW validation failed: " + "; ".join(problems))
        return body
