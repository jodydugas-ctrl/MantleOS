"""Capability façades for Body-side cognition wrappers.

These classes remove convenient *public* raw-organism handles from ``Mind``,
``InnerVoice``, and ``AppAIRuntime``. They are least-authority API structure, not a
Python sandbox: each port necessarily stores the organism in ``_org``, and trusted
in-process Python can reflect into that storage.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .containment import guarded_write
from ..vcw.drivers import validate_public_grant


class _Port:
    __slots__ = ("_org",)

    def __init__(self, organism: Any) -> None:
        object.__setattr__(self, "_org", organism)

    def __repr__(self) -> str:
        return "<%s public-raw-handle=absent>" % type(self).__name__


class MindPort(_Port):
    """Capabilities required by ``Mind`` and ``InnerVoice``—no public organ handles."""

    __slots__ = ()

    def write(self, band: str, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Use the existing Body-enforced cognition write gate."""
        return guarded_write(object.__getattribute__(self, "_org"), band, entry)

    def immune_event(self, kind: str, detail: Any) -> None:
        object.__getattribute__(self, "_org").immune_event(kind, detail)

    def identity_name(self) -> str:
        return object.__getattribute__(self, "_org").body.identity_name()

    def snapshot(self) -> Dict[str, Any]:
        return object.__getattribute__(self, "_org").nervous.assemble()

    def propose_special(self, text: str) -> Dict[str, Any]:
        return object.__getattribute__(self, "_org").body.mind_propose_special(text)

    def cultivate_skill(self, band: str, code: str, entry: str,
                        cases: List[Tuple[Dict[str, Any], Any]],
                        signature: Dict[str, Any],
                        capabilities: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return object.__getattribute__(self, "_org").limbs.cultivate_mind_skill(
            band, code, entry, cases, signature, capabilities)

    def record_discovery(self, record: Dict[str, Any]) -> Any:
        return object.__getattribute__(self, "_org").limbs.record_mind_discovery(record)

    def consolidation_window(self, limit: int = 48) -> Dict[str, Any]:
        return object.__getattribute__(self, "_org").memory.consolidation_window(limit=limit)

    def record_consolidation(self, proposal: Dict[str, Any], window: Dict[str, Any],
                             proposal_hash: str) -> Any:
        return object.__getattribute__(self, "_org").limbs.record_mind_consolidation(
            proposal, window, proposal_hash)


class OperatorPort(_Port):
    """Enumerated operator capabilities used by ``AppAIRuntime``."""

    __slots__ = ()

    def inspect(self) -> Dict[str, Any]:
        org = object.__getattribute__(self, "_org")
        prime = org.prime
        return {
            "identity": org.body.identity_name(),
            "boot_order": org.body.boot_order(),
            "prime_generation": prime.generation,
            "lineage_index": org.body.lineage_index,
            "stage1_certified": org.stage1_certified,
            "mind_fused": org.brain.fused,
            "organ_contracts": org.manifests(),
            "reflex_surface": org.bus.reflex_surface(),
            "bands": {
                name: {
                    "head": boot["head"], "span": boot["span"],
                    "encoding": boot["encoding"], "private": boot["private"],
                    "purpose": boot["purpose"],
                    "pressure": round(prime.pressure(name), 3),
                }
                for name, boot in prime.bands.items()
            },
        }

    def read(self, band: str) -> Any:
        return object.__getattribute__(self, "_org").prime.read(band)

    def resolve(self, ref: str) -> Any:
        return object.__getattribute__(self, "_org").resolve(ref)

    def snapshot(self) -> Dict[str, Any]:
        return object.__getattribute__(self, "_org").nervous.assemble()

    def inhale(self, signal: Dict[str, Any]) -> str:
        return object.__getattribute__(self, "_org").senses.inhale(signal)

    def operate(self, control_id: str, value: Any) -> Dict[str, Any]:
        return object.__getattribute__(self, "_org").limbs.operate(control_id, value)

    def invoke_reflex(self, band: str, args: Dict[str, Any],
                      granted: Optional[Dict[str, Any]] = None) -> Any:
        granted = validate_public_grant(granted)
        return object.__getattribute__(self, "_org").limbs.invoke_reflex(
            band, args, granted)

    def apply_mind_special(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        return object.__getattribute__(self, "_org").limbs.apply_mind_special(intent)

    def schedule_pulse(self, reason: str = "scheduled", after: Optional[int] = None,
                       at: Optional[int] = None, band: Optional[str] = None,
                       ref: Optional[str] = None) -> int:
        return object.__getattribute__(self, "_org").heart.schedule_pulse(
            reason, after=after, at=at, band=band, ref=ref)

    def schedule_consolidation(self, after: Optional[int] = None,
                               at: Optional[int] = None) -> int:
        return object.__getattribute__(self, "_org").heart.schedule_consolidation(
            after=after, at=at)

    def scheduled_pulses(self) -> list:
        return object.__getattribute__(self, "_org").heart.scheduled()

    def mind_fused(self) -> bool:
        return bool(object.__getattribute__(self, "_org").brain.fused)

    def mind(self) -> Any:
        return object.__getattribute__(self, "_org").brain.mind

    def mind_port(self) -> MindPort:
        return MindPort(object.__getattribute__(self, "_org"))

    def fuse(self, model: Any, *, authorization: Any = None,
             max_thoughts: int = 64, context_strategy: Any = None) -> Any:
        from .mind import fuse
        return fuse(object.__getattribute__(self, "_org"), model,
                    authorization=authorization, max_thoughts=max_thoughts,
                    context_strategy=context_strategy)


def require_mind_port(value: Any, holder: str) -> MindPort:
    if not isinstance(value, MindPort):
        raise TypeError("%s requires MindPort; raw %s is not accepted"
                        % (holder, type(value).__name__))
    return value


def operator_port(value: Any) -> OperatorPort:
    if isinstance(value, OperatorPort):
        return value
    if isinstance(value, MindPort):
        raise TypeError("operator runtime requires OperatorPort, not MindPort")
    return OperatorPort(value)
