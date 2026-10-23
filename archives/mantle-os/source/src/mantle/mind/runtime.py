#!/usr/bin/env python3
"""
mantle.mind.runtime  --  the AppAI runtime: how an agent thinks AS the organism (Mantle OS)

A coding agent (or any LLM-driven operator) should experience the organism FROM INSIDE --
through Body APIs, never raw file mutation. AppAIRuntime is that surface. Everything it
exposes is mediated:

  inspect       the Body's boot order, organ contracts, lineage, band pressures, reflex
                surface -- the whole anatomy, read-only
  perceive      visible VCW memory through the veil (private/tombstoned/quarantined hidden)
  orient        assemble the deterministic context snapshot (what a MIND would receive)
  act           propose actions THROUGH Limbs (dispatch + proofs); never a private I/O path
  steer         propose Special Instructions; the Body applies them
  learn         request skill cultivation; the Body trials, gates, and calcifies
  wonder        self-inquiry via the Inner Voice; answers stay INFERRED, never facts

The runtime exposes no public raw-organism handle.  It holds an ``OperatorPort`` whose
enumerated methods route effects through the same organ reflexes and containment gates as
other callers.  This is a least-authority API boundary, not a Python sandbox: the trusted
port retains a private ``_org`` reference.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from .mind import Mind
from .inner_voice import InnerVoice
from .port import OperatorPort, operator_port
from .transport import stub_mind


class AppAIRuntime:
    def __init__(self, organism: Any, model: Optional[Callable[[str], str]] = None) -> None:
        self.port: OperatorPort = operator_port(organism)
        self.model = model or stub_mind
        self._inner: Optional[InnerVoice] = None

    # ================= inspect: the anatomy, read-only ======================
    def inspect_body(self) -> Dict[str, Any]:
        """The whole anatomy at a glance: identity, boot order, lineage, organ contracts,
        reflex surface, band map + pressures, certification state."""
        return self.port.inspect()

    # ================= perceive: visible memory, through the veil ============
    def read_band(self, band: str) -> Any:
        """Visible entries only -- the veil, tombstones, and quarantine always apply.
        (Lifting the veil on `thoughts` is a MIND privilege exercised via cognition, not
        a runtime bypass.)"""
        return self.port.read(band)

    def resolve(self, ref: str) -> Any:
        """Resolve a `<...>` reference; a dangling reference becomes an immune event."""
        return self.port.resolve(ref)

    # ================= orient: the deterministic snapshot =====================
    def assemble_context(self) -> Dict[str, Any]:
        return self.port.snapshot()

    # ================= act: through Limbs, with proofs ========================
    def sense(self, signal: Dict[str, Any]) -> str:
        """Feed an inbound signal through the ONLY inbound boundary (Senses)."""
        return self.port.inhale(signal)

    def operate(self, control_id: str, value: Any) -> Dict[str, Any]:
        """Drive a mapped control through its ControlBridge (proof recorded)."""
        return self.port.operate(control_id, value)

    def invoke_skill(self, band: str, args: Dict[str, Any],
                     granted: Optional[Dict[str, Any]] = None) -> Any:
        """Run a calcified reflex through the Limb (gates + proof apply)."""
        return self.port.invoke_reflex(band, args, granted)

    # ================= plan ahead: schedule a future wake ======================
    def schedule_pulse(self, reason: str = "scheduled", after: Optional[int] = None,
                       at: Optional[int] = None, band: Optional[str] = None,
                       ref: Optional[str] = None) -> int:
        """Plan ahead: annotate a future baseline cognition beat -- a countdown
        (`after=N`) or a scheduled beat (`at=K`). The natural ten-minute MIND call remains
        unconditional; scheduling adds the bounded continuation stressor on the due beat.
        Returns the beat it will fire on."""
        return self.port.schedule_pulse(reason, after=after, at=at, band=band, ref=ref)

    def scheduled_pulses(self) -> list:
        """Inspect the planning queue (future wakes not yet fired)."""
        return self.port.scheduled_pulses()

    # ================= steer: propose; the Body applies ========================
    def propose_special_instruction(self, text: str) -> Dict[str, Any]:
        """Returns the intent AND the Body's application of it -- the two-step made
        visible: the proposal is authored MIND, the applied entry is authored BODY."""
        mind = self._require_mind()
        intent = mind.propose_special(text)
        return self.port.apply_mind_special(intent)

    # ================= learn: request cultivation; the Body gates ==============
    def request_skill(self, band: str, code: str, entry: str,
                      cases: List[Tuple[Dict[str, Any], Any]],
                      signature: Optional[Dict[str, Any]] = None,
                      capabilities: Optional[Dict[str, Any]] = None
                      ) -> Optional[Dict[str, Any]]:
        """Propose a skill. The Body trials it (static sandbox first), then calcifies it
        behind the hash/signature/capability/provenance gates. A refused or failing
        candidate is an immune event and never becomes an instinct."""
        mind = self._require_mind()
        return mind.cultivate(band, code, entry, cases,
                              signature or {"by": "appai-runtime"},
                              capabilities or {})

    # ================= wonder: self-inquiry, honestly inferred ==================
    def self_inquire(self, question: str, mode: str = "neutral"):
        """Ask the Inner Voice. The answer is tagged inferred and lands in discoveries
        (or private thoughts for `oppose`) -- NEVER in facts."""
        self._require_mind()
        if self._inner is None:
            self._inner = InnerVoice(self.port.mind_port(), self.model)
        return self._inner.ask(question, mode)

    # ================= cognition plumbing ========================================
    def _require_mind(self) -> Mind:
        if not self.port.mind_fused():
            raise PermissionError("no MIND fused: certify Stage 1, then fuse() "
                                  "(audit before fusion)")
        return self.port.mind()

    def fuse_mind(self, model: Optional[Callable[[str], str]] = None, *,
                  authorization: Any = None, max_thoughts: int = 64,
                  context_strategy: Any = None) -> Mind:
        """Fuse only with Stage-1 evidence and explicit operator + guardian approval."""
        return self.port.fuse(model or self.model, authorization=authorization,
                              max_thoughts=max_thoughts,
                              context_strategy=context_strategy)
