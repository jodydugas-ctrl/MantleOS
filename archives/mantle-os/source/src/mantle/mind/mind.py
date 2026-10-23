#!/usr/bin/env python3
"""
mantle.mind.mind  --  the reference MIND fusion, provider-agnostic (Mantle OS)

The MIND is a fused LLM, sharply bounded by the BODY -- and the boundary is executable:

  * it receives only the deterministically-assembled, already-resolved, already-veiled
    context snapshot (the Nervous System) -- never a raw reference;
  * it writes ONLY `thoughts` + `brain`, through one guarded choke point (containment.py);
    any other band is refused + immune-logged;
  * it PROPOSES Special Instructions; the Body applies them;
  * it cannot touch the Genome and cannot self-promote a skill: a cultivated skill must
    pass the static sandbox gate + `trial`, and then the BODY calcifies it (hash,
    signature, capability, provenance gates all enforced by the substrate);
  * its reflections are INFERRED (verified=False) -- never laundered into facts;
  * a waste budget caps thinking ("failure is not the end; waste is").

Fusion is performed by `fuse(organism, model, authorization=...)`, which refuses without
both a certified Stage-1 gate and explicit operator and guardian approval.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..vcw.entry import make_entry
from ..core.redact import redact
from .port import MindPort, require_mind_port
from .transport import complete_model, stub_mind
from .context import (
    ContextStrategy,
    ModelRequest,
    SnapshotContextStrategy,
    model_info_from_transport,
)


def _h(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


class Mind:
    def __init__(self, port: MindPort, model: Callable[[str], str], *,
                 max_thoughts: int = 64,
                 context_strategy: Optional[ContextStrategy] = None) -> None:
        self.port = require_mind_port(port, "Mind")
        self.model = model                  # the pluggable transport: prompt -> text
        self.max_thoughts = max_thoughts    # the waste budget: the MIND cannot spiral
        self.thoughts_written = 0
        # SnapshotContextStrategy reproduces the historical prompt path exactly.
        self.context_strategy = (
            context_strategy or SnapshotContextStrategy(self._frame)
        )

    # ---- the bounded write surface (Body-enforced) -----------------------
    def _guarded_write(self, band: str, entry: Dict[str, Any]) -> Dict[str, Any]:
        return self.port.write(band, entry)

    def _trace(self, kind: str, detail: Dict[str, Any]) -> None:
        """Record a model call to the brain band (the Body authors the trace; secrets
        redacted)."""
        self._guarded_write("brain", make_entry(
            {"MODEL." + kind: redact(detail)}, opcode="MODEL." + kind,
            author="BODY", authorship="BODY"))

    # ---- think: receive the assembled snapshot, reflect into thoughts ----
    def think(self, snapshot: Dict[str, Any], question: Optional[str] = None
              ) -> Optional[str]:
        if self.thoughts_written >= self.max_thoughts:
            self.port.immune_event("waste_guard",
                                   {"organ": "mind", "limit": self.max_thoughts})
            return None
        prepared = self.context_strategy.prepare(
            snapshot=snapshot,
            intent=question,
            model_info=model_info_from_transport(self.model),
        )
        self._trace("REQUEST", {
            "prompt_hash": _h(prepared.prompt),
            "request_hash": prepared.request_hash,
            "context_generation": prepared.generation,
            "context_sequence": prepared.sequence,
            "estimated_prompt_tokens": prepared.estimated_prompt_tokens,
        })
        try:
            response = complete_model(
                self.model,
                ModelRequest(
                    prompt=prepared.prompt,
                    metadata={
                        "context_generation": prepared.generation,
                        "context_sequence": prepared.sequence,
                        "stable_prefix_hash": prepared.prefix_hash,
                        "dynamic_suffix_hash": prepared.delta_hash,
                        "request_hash": prepared.request_hash,
                    },
                ),
            )
        except Exception as exc:
            self.context_strategy.commit_failure(prepared, error=exc)
            self._trace("FAILURE", {
                "request_hash": prepared.request_hash,
                "error": type(exc).__name__,
            })
            raise
        answer = response.text
        usage = dict(response.usage or getattr(self.model, "last_usage", None) or {})
        if prepared.generation:
            usage.update({
                "context_generation": prepared.generation,
                "context_sequence": prepared.sequence,
                "stable_prefix_hash": prepared.prefix_hash,
                "dynamic_suffix_hash": prepared.delta_hash,
                "context_request_hash": prepared.request_hash,
            })
        self.context_strategy.commit_success(
            prepared,
            answer=answer,
            usage=usage or None,
        )
        if usage:
            self._trace("USAGE", usage)
        self._trace("RESPONSE", {"answer_hash": _h(answer)})
        self.thoughts_written += 1
        # the MIND's reflection is private and INFERRED -- never a verified fact
        self._guarded_write("thoughts", make_entry(
            {"reflection": answer}, opcode="THINK", author="MIND",
            verified=False, confidence="inferred"))
        return answer

    def _frame(self, snapshot: Dict[str, Any]) -> str:
        return ("You are the fused MIND of a AppAI named %s. Your context has been "
                "assembled deterministically (every reference already resolved, the private "
                "`thoughts` band veiled). Reflect briefly; you may propose Body changes but "
                "you do not apply them.\n\nCONTEXT:\n%s"
                % (self.port.identity_name(),
                   json.dumps(snapshot, default=str)[:4000]))

    def _consolidation_frame(self, snapshot: Dict[str, Any], window: Dict[str, Any]) -> str:
        return (
            "You are the fused MIND of an AppAI. Perform retrospective interpretation only. "
            "Original records are immutable: do not request promotion, deletion, tombstoning, "
            "execution, or source coordinates not supplied below. Return JSON only with exactly "
            "this schema: {summary:string, reappraisals:[{subject:{generation,band,id}, "
            "status:supported|weakened|superseded|unresolved|later_significant, because:[{generation,band,id}], "
            "interpretation:string, confidence:strong|moderate|plausible|speculative, weight?:0..1}], "
            "open_questions:[string]}. A weight is permitted only for events, discoveries, or senses.\n\n"
            "BODY-SELECTED WINDOW:\n%s\n\nCONTEXT:\n%s"
            % (json.dumps(window, sort_keys=True, default=str),
               json.dumps(snapshot, sort_keys=True, default=str)[:4000])
        )

    def consolidate(self, snapshot: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Ask for bounded retrospective meaning; the Body validates every durable effect."""
        if self.thoughts_written >= self.max_thoughts:
            self.port.immune_event("waste_guard", {"organ": "mind", "limit": self.max_thoughts})
            return None
        window = self.port.consolidation_window(limit=48)
        if not window.get("entries"):
            return None
        prompt = self._consolidation_frame(snapshot, window)
        request_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        self._trace("REQUEST", {
            "prompt_hash": _h(prompt), "request_hash": request_hash,
            "context_generation": 0, "context_sequence": 0,
            "estimated_prompt_tokens": 0,
        })
        try:
            response = complete_model(self.model, ModelRequest(
                prompt=prompt,
                metadata={"request_hash": request_hash, "consolidation": True},
            ))
        except Exception as exc:
            self._trace("FAILURE", {"request_hash": request_hash,
                                    "error": type(exc).__name__})
            self.thoughts_written += 1
            raise
        answer = response.text
        usage = dict(response.usage or getattr(self.model, "last_usage", None) or {})
        if usage:
            self._trace("USAGE", usage)
        self._trace("RESPONSE", {"answer_hash": _h(answer)})
        self.thoughts_written += 1
        self._guarded_write("thoughts", make_entry(
            {"reflection": answer, "window": window.get("cursor_before")},
            opcode="CONSOLIDATE", author="MIND", verified=False, confidence="inferred"))
        try:
            proposal = json.loads(answer)
        except (TypeError, ValueError):
            self.port.immune_event("consolidation_refused", {"reason": "malformed JSON"})
            return None
        canonical = json.dumps(proposal, sort_keys=True, separators=(",", ":"),
                               ensure_ascii=False)
        proposal_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        try:
            return self.port.record_consolidation(proposal, window, proposal_hash)
        except (PermissionError, ValueError):
            return None

    # ---- propose Special Instructions (the Body applies) -----------------
    def propose_special(self, text: str) -> Dict[str, Any]:
        """The MIND may only PROPOSE. The returned intent is NOT written; the Body applies
        it via `body.apply_special`, keeping steering a Body action."""
        return self.port.propose_special(text)

    # ---- cultivate a skill (the Body calcifies, only after trial) --------
    def cultivate(self, band: str, code: str, entry: str,
                  cases: List[Tuple[Dict[str, Any], Any]],
                  signature: Dict[str, Any], capabilities: Dict[str, Any]
                  ) -> Optional[Dict[str, Any]]:
        """Learning -> instinct, under containment. The MIND cannot self-promote: the
        candidate must pass the static sandbox gate + `trial`; then the BODY calcifies
        (hash + signature + capability + provenance gates enforced by the substrate)."""
        return self.port.cultivate_skill(
            band, code, entry, cases, signature, capabilities
        )

    # ---- cognition: the Phase-2 heartbeat extension ----------------------
    def cognize(self, snapshot: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """One cognition pulse. The Heart passes the snapshot it already assembled; a
        direct call assembles one. Either way: fully resolved, veiled, deterministic."""
        if snapshot is None:
            snapshot = self.port.snapshot()
        stressor = snapshot.get("_stressor") or {}
        if stressor.get("reason") == "memory_consolidation":
            return self.consolidate(snapshot)
        return self.think(snapshot)


def fuse(organism: Any, model: Callable[[str], str] = stub_mind, *,
         authorization: Any = None, max_thoughts: int = 64,
         context_strategy: Optional[ContextStrategy] = None) -> Mind:
    """Fuse only after Stage-1 evidence and target-bound dual authorization."""
    mind = Mind(
        MindPort(organism),
        model,
        max_thoughts=max_thoughts,
        context_strategy=context_strategy,
    )
    organism.brain.fuse(
        mind,
        stage1_certified=organism.stage1_certified,
        authorization=authorization,
    )
    return mind
