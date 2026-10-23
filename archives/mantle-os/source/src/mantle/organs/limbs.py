#!/usr/bin/env python3
"""
mantle.organs.limbs  --  the Limbs organ: action, the ONLY outbound boundary (Mantle OS)

ALL outbound actions leave the organism through Limbs. It owns:

  the dispatch lifecycle   INTENTION -> DELEGATED -> NOTIFIED -> COMPLETED, each record
                           carrying an immutable `authorship` field (INSIDE the entry hash):
                             * the MIND owns INTENTION / DELEGATED   (Phase 2)
                             * the BODY owns NOTIFIED / COMPLETED     (Phase 1, permanently)
  the ControlBridge        an effector path for every human-visible control
  Action Execution Proof   a record (attempted/ok/method/ref/reason) for every effector use
  calcified reflexes       Limbs runs `exec` skills behind the hash/capability/trust gates

Phase 1 is dormant->active: effectors, actuation, proofs, and reflex invocation are built
and testable with no MIND. INTENTION/DELEGATED await the Brain; the Body never authors them.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from .contract import Organ, OrganContract
from ..vcw.drivers import trial, validate_public_grant
from ..vcw.entry import make_entry

DISPATCH_PHASES = ("INTENTION", "DELEGATED", "NOTIFIED", "COMPLETED")
_MIND_PHASES = ("INTENTION", "DELEGATED")     # authored only by a fused MIND (Phase 2)
_BODY_PHASES = ("NOTIFIED", "COMPLETED")      # authored by the Body (Phase 1, permanently)
MIND_SPECIAL_CONTROL = "mind.special_instruction"
MIND_DISCOVERY_CONTROL = "mind.discovery"
MIND_CULTIVATE_CONTROL = "mind.cultivate"
MIND_CONSOLIDATION_CONTROL = "mind.consolidation"

CONTRACT = OrganContract(
    "limbs", "action & surface actuation (efferent I/O) -- the only outbound boundary",
    reads=["brain"],
    writes=["brain"],
    reflexes=[
        {"name": "notify", "trigger": "a limb reports back", "effect": "Body records NOTIFIED"},
        {"name": "complete", "trigger": "a task finishes", "effect": "Body records COMPLETED"},
        {"name": "operate", "trigger": "a control must be driven",
         "effect": "ControlBridge actuation + an Action Execution Proof, fail-open"},
        {"name": "prove", "trigger": "every effector use",
         "effect": "record attempted/ok/method/ref/reason"},
        {"name": "invoke-reflex", "trigger": "a calcified skill is called",
         "effect": "run the exec layer behind hash/capability/provenance/trust gates + proof"},
    ],
    phase1="dormant->active",
    phase2_extension="the MIND authors INTENTION/DELEGATED; the Body keeps NOTIFIED/COMPLETED "
                     "and all actuation permanently (no private MIND I/O path)",
    audit=[
        "authorship field present and immutable (inside the entry hash)",
        "the Body never authors INTENTION/DELEGATED",
        "every effector use has an Action Execution Proof",
        "every human-visible control has a working ControlBridge path with a recorded proof",
    ],
)


class Limbs(Organ):
    contract = CONTRACT

    def __init__(self, organism) -> None:
        super().__init__(organism)
        self.bridges: Dict[str, Callable[[Any], Any]] = {}  # control_id -> effector

    # ---- surface wiring (efferent half; Senses holds the afferent map) -----
    def register_control(self, control_id: str, descriptor: Dict[str, Any],
                         bridge: Callable[[Any], Any]) -> None:
        """Every human-visible control gets both halves: Senses perceives it into the
        Surface Map (afferent); Limbs gets its ControlBridge (efferent)."""
        self.org.senses.map_control(control_id, descriptor)
        self.bridges[control_id] = bridge

    def surface_covered(self) -> bool:
        """True iff every control in the Human Surface Map has a ControlBridge path."""
        return all(cid in self.bridges for cid in self.org.senses.surface_map)

    # ---- dispatch lifecycle ---------------------------------------------------
    def _dispatch(self, phase: str, payload: Any) -> Dict[str, Any]:
        authorship = "MIND" if phase in _MIND_PHASES else "BODY"
        e = make_entry({"phase": phase, "payload": payload}, opcode="DISPATCH",
                       author=authorship, authorship=authorship)
        self.append("brain", e)
        self.bus.emit("dispatch", {"phase": phase, "authorship": authorship})
        return e

    def _mind_dispatch(self, phase: str, payload: Any) -> Dict[str, Any]:
        if not self.org.brain.fused:
            self.org.immune_event("mind_dispatch_refused", {
                "phase": phase, "reason": "no MIND fused"})
            raise PermissionError("%s requires a fused MIND" % phase)
        return self._dispatch(phase, payload)

    # Phase-1 (Body-owned)
    def notify(self, payload: Any) -> Dict[str, Any]:
        return self._dispatch("NOTIFIED", payload)

    def complete(self, payload: Any) -> Dict[str, Any]:
        return self._dispatch("COMPLETED", payload)

    # Phase-2 (MIND-owned) -- present so the lifecycle is whole; the Body never calls these.
    def intend(self, payload: Any) -> Dict[str, Any]:
        return self._mind_dispatch("INTENTION", payload)

    def delegate(self, payload: Any) -> Dict[str, Any]:
        return self._mind_dispatch("DELEGATED", payload)

    # ---- actuation + proof -------------------------------------------------------
    def operate(self, control_id: str, value: Any) -> Dict[str, Any]:
        """Drive a human-visible control through its ControlBridge and record an Action
        Execution Proof. Fail-open: a failing effector records a failed proof."""
        if control_id not in self.bridges:
            self.org.immune_event("unmapped_control", {"control_id": control_id})
            return self._prove(control_id, attempted=False, ok=False,
                               method=None, ref=None, reason="no ControlBridge")
        try:
            bridge_result = self.bridges[control_id](value)
            if isinstance(bridge_result, dict):
                attempted = bool(bridge_result.get("attempted", True))
                ok = bool(bridge_result.get("ok", True))
                method = bridge_result.get("method") or "ControlBridge"
                ref = bridge_result.get("ref") or control_id
                reason = bridge_result.get("reason") or ("ok" if ok else "not verified")
                extra = {
                    key: val for key, val in bridge_result.items()
                    if key not in {"attempted", "ok", "method", "ref", "reason"}
                }
                return self._prove(
                    control_id, attempted=attempted, ok=ok,
                    method=method, ref=ref, reason=reason, **extra,
                )
            return self._prove(control_id, attempted=True, ok=True,
                               method="ControlBridge", ref=control_id, reason="ok")
        except Exception as ex:                  # noqa: BLE001 -- fail-open at the effector
            return self._prove(control_id, attempted=True, ok=False,
                               method="ControlBridge", ref=control_id,
                               reason=type(ex).__name__)

    def _prove(self, control_id: str, **proof: Any) -> Dict[str, Any]:
        rec: Dict[str, Any] = {"control": control_id}
        rec.update(proof)
        self.append("brain", make_entry({"action_proof": rec}, opcode="PROOF",
                                        author="BODY", authorship="BODY"))
        return rec

    # ---- model-caused mutation ceremonies ---------------------------------------
    def _require_fused_mind(self, control_id: str) -> None:
        if self.org.brain.fused:
            return
        self.org.immune_event(
            "mind_mutation_refused",
            {"control_id": control_id, "reason": "no MIND fused"},
        )
        raise PermissionError("%s requires a fused MIND" % control_id)

    def apply_mind_special(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a MIND steering proposal, apply it as Body, and prove the mutation."""
        self._require_fused_mind(MIND_SPECIAL_CONTROL)
        text = intent.get("text") if isinstance(intent, dict) else None
        valid = (
            isinstance(intent, dict)
            and intent.get("intent") == "special_instruction"
            and intent.get("author") == "MIND"
            and isinstance(text, str)
            and bool(text.strip())
            and len(text) <= 4096
            and not any(ord(character) < 32 and character not in "\n\t" for character in text)
        )
        if not valid:
            self._prove(
                MIND_SPECIAL_CONTROL, attempted=False, ok=False,
                method="BodyMutationBridge", ref="body.special", reason="invalid proposal",
            )
            raise ValueError("invalid MIND special-instruction proposal")
        applied = self.org.body.apply_special(text, source="MIND")
        proof = self._prove(
            MIND_SPECIAL_CONTROL, attempted=True, ok=True,
            method="BodyMutationBridge", ref="body.special", reason="ok",
        )
        return {"intent": intent, "applied": applied, "proof": proof}

    def record_mind_discovery(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Persist one inferred inner-voice result through Limbs, never as a fact."""
        self._require_fused_mind(MIND_DISCOVERY_CONTROL)
        valid = (
            isinstance(record, dict)
            and record.get("author") == "MIND"
            and record.get("verified") is False
            and record.get("confidence") == "inferred"
            and record.get("opcode") == "INNER_VOICE"
        )
        if not valid:
            self._prove(
                MIND_DISCOVERY_CONTROL, attempted=False, ok=False,
                method="BodyMutationBridge", ref="discoveries", reason="invalid proposal",
            )
            raise ValueError("invalid inferred-discovery proposal")
        self.org.memory.append("discoveries", record)
        return self._prove(
            MIND_DISCOVERY_CONTROL, attempted=True, ok=True,
            method="BodyMutationBridge", ref="discoveries", reason="ok",
        )

    def record_mind_consolidation(self, proposal: Dict[str, Any], window: Dict[str, Any],
                                  proposal_hash: str) -> Dict[str, Any]:
        """Validate retrospective proposals before any Body memory mutation."""
        if not self.org.brain.fused:
            self._prove(MIND_CONSOLIDATION_CONTROL, attempted=False, ok=False,
                        method="BodyMutationBridge", ref="discoveries", reason="no MIND fused")
        self._require_fused_mind(MIND_CONSOLIDATION_CONTROL)
        # A completed hash is safe to acknowledge even after its source window has moved.
        # This preserves retry idempotency without reopening any mutation surface.
        if any(receipt.get("content", {}).get("proposal_hash") == proposal_hash
               for receipt in self.org.memory._successful_receipts()):
            result = self.org.memory.record_consolidation(
                proposal, cursor_after=(window or {}).get("cursor_after", {}),
                proposal_hash=proposal_hash)
            result["proof"] = self._prove(
                MIND_CONSOLIDATION_CONTROL, attempted=True, ok=True,
                method="BodyMutationBridge", ref="discoveries", reason="idempotent")
            return result
        reason = self._validate_consolidation(proposal, window, proposal_hash)
        if reason:
            self.org.immune_event("consolidation_refused", {"reason": reason})
            self._prove(MIND_CONSOLIDATION_CONTROL, attempted=False, ok=False,
                        method="BodyMutationBridge", ref="discoveries", reason=reason)
            raise ValueError("invalid MIND consolidation proposal: %s" % reason)
        result = self.org.memory.record_consolidation(
            proposal, cursor_after=window["cursor_after"], proposal_hash=proposal_hash)
        result["proof"] = self._prove(
            MIND_CONSOLIDATION_CONTROL, attempted=True, ok=True,
            method="BodyMutationBridge", ref="discoveries", reason="ok")
        return result

    @staticmethod
    def _valid_text(value: Any, limit: int) -> bool:
        return (isinstance(value, str) and bool(value.strip()) and len(value) <= limit
                and not any(ord(char) < 32 and char not in "\n\t" for char in value))

    def _validate_consolidation(self, proposal: Any, window: Any, proposal_hash: Any) -> str:
        if not isinstance(proposal, dict) or set(proposal) != {"summary", "reappraisals", "open_questions"}:
            return "unknown or missing top-level keys"
        if not isinstance(proposal_hash, str) or len(proposal_hash) != 64:
            return "invalid proposal hash"
        if not self._valid_text(proposal.get("summary"), 2048):
            return "invalid summary"
        reappraisals, questions = proposal.get("reappraisals"), proposal.get("open_questions")
        if not isinstance(reappraisals, list) or len(reappraisals) > 24:
            return "invalid reappraisals"
        if not isinstance(questions, list) or len(questions) > 24 or not all(
                self._valid_text(question, 512) for question in questions):
            return "invalid open questions"
        if not isinstance(window, dict) or not isinstance(window.get("entries"), list):
            return "invalid Body window"
        if window != self.org.memory.consolidation_window(limit=48):
            return "stale or forged Body window"
        allowed = {
            (item["ref"].get("generation"), item["ref"].get("band"), item["ref"].get("id"))
            for item in window["entries"] if isinstance(item, dict)
            and isinstance(item.get("ref"), dict)
        }
        keys = {"subject", "status", "because", "interpretation", "confidence", "weight"}
        for item in reappraisals:
            if not isinstance(item, dict) or set(item) - keys or not {"subject", "status", "because", "interpretation", "confidence"} <= set(item):
                return "invalid reappraisal keys"
            subject = item["subject"]
            if not self._valid_consolidation_ref(subject, allowed):
                return "invented subject reference"
            if item["status"] not in {"supported", "weakened", "superseded", "unresolved", "later_significant"}:
                return "invalid status"
            if item["confidence"] not in {"strong", "moderate", "plausible", "speculative"}:
                return "invalid confidence"
            if not self._valid_text(item["interpretation"], 2048):
                return "invalid interpretation"
            if any(token in item["interpretation"].lower() for token in (
                    "promote", "delete", "tombstone", "calcify", "execute", "write")):
                return "forbidden mutation instruction"
            because = item["because"]
            if not isinstance(because, list) or len(because) > 16 or not all(
                    self._valid_consolidation_ref(ref, allowed) for ref in because):
                return "invented because reference"
            if "weight" in item:
                value = item["weight"]
                if subject["band"] not in ("events", "discoveries", "senses"):
                    return "fact weight changes are forbidden"
                if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0.0 <= value <= 1.0:
                    return "invalid weight"
        if any(any(token in text.lower() for token in (
                "promote", "delete", "tombstone", "calcify", "execute", "write"))
               for text in [proposal["summary"]] + questions):
            return "forbidden mutation instruction"
        return ""

    @staticmethod
    def _valid_consolidation_ref(ref: Any, allowed: set) -> bool:
        return (isinstance(ref, dict) and set(ref) == {"generation", "band", "id"}
                and (ref.get("generation"), ref.get("band"), ref.get("id")) in allowed)

    def cultivate_mind_skill(
        self,
        band: str,
        code: str,
        entry: str,
        cases: List[Tuple[Dict[str, Any], Any]],
        signature: Dict[str, Any],
        capabilities: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Trial and calcify one MIND proposal as a proven Body mutation."""
        self._require_fused_mind(MIND_CULTIVATE_CONTROL)
        try:
            result = trial(code, entry, cases)
            if not result["ok"]:
                raise ValueError("skill trial failed")
            self.org.prime.calcify(
                band,
                code,
                entry=entry,
                signature=signature,
                capabilities=capabilities,
                provenance={"author": "MIND", "born_gen": self.org.prime.generation},
            )
        except Exception as exc:  # noqa: BLE001 -- refusal is a proved, fail-open outcome
            self.org.immune_event(
                "skill_refused", {"entry": entry, "reason": type(exc).__name__}
            )
            self._prove(
                MIND_CULTIVATE_CONTROL, attempted=True, ok=False,
                method="BodyMutationBridge", ref=band, reason=type(exc).__name__,
            )
            return None
        self._prove(
            MIND_CULTIVATE_CONTROL, attempted=True, ok=True,
            method="BodyMutationBridge", ref=band, reason="ok",
        )
        return result

    # ---- calcified reflex invocation (zombie-state capability) -----------------
    def invoke_reflex(self, band: str, args: Dict[str, Any],
                      granted: Optional[Dict[str, Any]] = None) -> Any:
        """Run a calcified exec-layer skill through the Limb (with a proof). Works with NO
        MIND; the substrate's hash/capability/provenance/trust gates apply unchanged."""
        try:
            granted = validate_public_grant(granted)
            result = self.org.prime.invoke(band, args, granted)
            self._prove(band, attempted=True, ok=True, method="exec-reflex",
                        ref=band, reason="ok")
            return result
        except Exception as ex:
            self._prove(band, attempted=True, ok=False, method="exec-reflex",
                        ref=band, reason=type(ex).__name__)
            self.org.immune_event("reflex_invoke_failed",
                                  {"band": band, "error": type(ex).__name__})
            raise
