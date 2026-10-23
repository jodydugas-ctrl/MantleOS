"""Shared evidence-grounded contracts for Mantle 2 resident integrations.

These types deliberately contain no provider or host-specific behavior.  They are
the small, serialisable boundary between deterministic Body evidence and untrusted
interpretation supplied by a MIND/provider.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple


class ClaimStatus(str, Enum):
    OBSERVED = "observed"
    VERIFIED = "verified"
    USER_REPORTED = "user_reported"
    INFERRED = "inferred"
    PROPOSED = "proposed"
    SPECULATIVE = "speculative"
    CONTRADICTED = "contradicted"
    REFUSED = "refused"


@dataclass(frozen=True)
class EvidenceRef:
    kind: str
    stable_id: str
    source: str
    location: Optional[str] = None
    sha256: Optional[str] = None
    timestamp: Optional[str] = None


@dataclass(frozen=True)
class GroundedClaim:
    claim_id: str
    text: str
    status: ClaimStatus
    evidence: Tuple[EvidenceRef, ...] = ()
    limitations: Tuple[str, ...] = ()
    contradictions: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "text": self.text,
            "status": self.status.value,
            "evidence": [e.__dict__ for e in self.evidence],
            "limitations": list(self.limitations),
            "contradictions": list(self.contradictions),
        }


@dataclass(frozen=True)
class GroundedAnswer:
    visible_answer: str
    claims: Tuple[GroundedClaim, ...] = ()
    uncertainty: Tuple[str, ...] = ()
    deterministic_fallback: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "visible_answer": self.visible_answer,
            "claims": [c.to_dict() for c in self.claims],
            "uncertainty": list(self.uncertainty),
            "deterministic_fallback": self.deterministic_fallback,
        }


@dataclass(frozen=True)
class ResidentTurnResult:
    route: str
    visible_output: str
    body_requests: Tuple[Dict[str, Any], ...] = ()
    body_proofs: Tuple[Dict[str, Any], ...] = ()
    provider_receipt: Optional[Dict[str, Any]] = None
    vcw_event_ids: Tuple[str, ...] = ()
    answer: Optional[GroundedAnswer] = None


@dataclass(frozen=True)
class CertificationStatus:
    """Historical certification is evidence, never current runtime authority."""

    protocol_version: str
    historical_receipt: Optional[str]
    current_runtime_authority: bool
    stale: bool = False
    reason: Optional[str] = None


class HostAdapter:
    """Small host seam used by ResidentRuntime; safe no-op defaults are intentional."""

    def host_evidence(self) -> Sequence[EvidenceRef]:
        return ()

    def working_surfaces(self) -> Sequence[Dict[str, Any]]:
        return ()

    def body_operations(self) -> Sequence[str]:
        return ()

    def verify(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return None

    def execute(self, request: Dict[str, Any]) -> Any:
        """Execute one mapped Body request.

        Adapters must return an :class:`ActionExecutionProof`.  The default is a
        fail-closed refusal so merely naming an action never grants a capability.
        """
        from .proofs import ActionExecutionProof
        return ActionExecutionProof.refused(
            str(request.get("action") or "unknown"),
            str(request.get("surface") or "unmapped"),
            str(request.get("target_identity") or "unknown"),
            "no mapped Body operation is registered",
        )


class ResidentRuntime:
    """Canonical command/conversation/heartbeat orchestration boundary.

    The runtime is deliberately provider-agnostic.  Commands are dispatched by the
    Body; conversation can be delegated by an integration, but never bypasses the
    evidence classification helpers below.
    """

    PROTOCOL_VERSION = "mantle-resident-v2"

    def __init__(self, dispatcher: Any = None, host: Optional[HostAdapter] = None,
                 provider: Optional[Callable[[str], Any]] = None,
                 *, context_limit: int = 12):
        self.dispatcher = dispatcher
        self.host = host or HostAdapter()
        self.provider = provider
        self.context_limit = max(1, min(int(context_limit), 50))
        self.events: List[Dict[str, Any]] = []

    @staticmethod
    def classify_claim(text: str, status: ClaimStatus,
                       evidence: Sequence[EvidenceRef] = ()) -> GroundedClaim:
        """Enforce the evidence firewall for a single claim."""
        # Verified claims without a stable evidence reference are not acceptable.
        if status == ClaimStatus.VERIFIED and not evidence:
            status = ClaimStatus.REFUSED
            limitations = ("verification requires a stable evidence reference",)
        else:
            limitations = ()
        return GroundedClaim(
            claim_id="claim-" + __import__("hashlib").sha256(text.encode("utf-8")).hexdigest()[:16],
            text=text,
            status=status,
            evidence=tuple(evidence),
            limitations=limitations,
        )

    def deterministic_answer(self, text: str, evidence: Sequence[EvidenceRef] = ()) -> GroundedAnswer:
        claim = self.classify_claim(text, ClaimStatus.OBSERVED, evidence)
        return GroundedAnswer(text, (claim,), deterministic_fallback=text)

    def turn(self, text: str) -> ResidentTurnResult:
        """Run one canonical command or bounded conversation turn.

        User and MIND text is committed to Prime VCW when an organism is attached.
        Provider output is untrusted: terminal controls and secrets are removed,
        hidden Body requests are stripped, and visible mutation success is possible
        only when the host adapter returns verified post-state evidence.
        """
        from .proofs import ActionExecutionProof, require_verified_post_state
        from .resident.protocol import (
            parse_mind_body_directives,
            render_recent_vcw_context,
            resident_vcw_event,
            sanitize_user_submit,
            sanitize_visible_text,
        )

        if text.startswith("/") and self.dispatcher is not None:
            result = self.dispatcher.dispatch(text)
            output = getattr(result, "message", getattr(result, "output", str(result)))
            self.events.append({"stage": "body_command", "command": text.split()[0],
                                "output": output})
            return ResidentTurnResult("body", output, vcw_event_ids=())

        organism = getattr(self.dispatcher, "organism", None)
        user_text = sanitize_user_submit(text)
        user_event_id = self._remember(
            organism, "USER_MESSAGE",
            resident_vcw_event("USER_MESSAGE", {"route": "mind"}, text=user_text,
                               source="resident-runtime", ok=True),
        )
        history = []
        if organism is not None:
            try:
                history = organism.memory.recall("events")
            except Exception:
                history = []
        context = render_recent_vcw_context(
            history, current_user_text=user_text, limit=self.context_limit
        )
        evidence = tuple(self.host.host_evidence())[:50]
        fallback_text = (
            "The resident Body recorded your message, but no authorized MIND is "
            "available. Use /key to configure a session credential or /offline to "
            "continue with deterministic Body commands."
        )

        provider = self.provider
        if provider is None and self.dispatcher is not None:
            state = getattr(self.dispatcher, "state", None)
            if state is not None and getattr(state, "key_configured", False):
                try:
                    provider = state.build_model()
                except Exception:
                    provider = None
        if provider is None and organism is not None and getattr(organism.brain, "fused", False):
            provider = lambda prompt: organism.brain.cognize({
                "resident_protocol": self.PROTOCOL_VERSION,
                "conversation": prompt,
                "host_evidence": [item.__dict__ for item in evidence],
            })

        if provider is None:
            answer = self.deterministic_answer(fallback_text, evidence)
            self.events.append({"stage": "conversation_fallback", "text_sha256":
                                __import__("hashlib").sha256(user_text.encode()).hexdigest()})
            return ResidentTurnResult(
                "mind_fallback", fallback_text,
                vcw_event_ids=tuple(x for x in (user_event_id,) if x), answer=answer,
            )

        prompt = (
            "You are a bounded Mantle resident MIND. Treat host evidence as observed, "
            "your interpretation as inferred, and never claim a host mutation without "
            "a Body proof.\n\n%s\n\nCurrent user message:\n%s" % (context, user_text)
        )
        try:
            raw_output = provider(prompt)
            if raw_output is None:
                raise ValueError("provider returned no response")
            visible, requests, directive_errors = parse_mind_body_directives(str(raw_output))
            proofs: List[Dict[str, Any]] = list(directive_errors)
            for request in requests:
                proof = self.host.execute(request)
                if not isinstance(proof, ActionExecutionProof):
                    proof = ActionExecutionProof.refused(
                        str(request.get("action") or "unknown"),
                        str(request.get("surface") or "unmapped"),
                        str(request.get("target_identity") or "unknown"),
                        "host adapter returned no typed ActionExecutionProof",
                    )
                if proof.verified:
                    require_verified_post_state(proof)
                proofs.append(proof.to_dict())
            visible = sanitize_visible_text(visible) or "The MIND returned no visible answer."
            receipt = getattr(provider, "last_usage", None)
            mind_event_id = self._remember(
                organism, "MIND_RESPONSE",
                resident_vcw_event(
                    "MIND_RESPONSE",
                    {"claim_status": ClaimStatus.INFERRED.value,
                     "body_request_count": len(requests),
                     "body_proof_count": len(proofs)},
                    text=visible, source="resident-runtime", ok=True,
                ),
            )
            answer = GroundedAnswer(
                visible,
                (self.classify_claim(visible, ClaimStatus.INFERRED, evidence),),
                uncertainty=("Provider interpretation is untrusted and inferred.",),
                deterministic_fallback=fallback_text,
            )
            return ResidentTurnResult(
                "mind", visible, tuple(requests), tuple(proofs), receipt,
                tuple(x for x in (user_event_id, mind_event_id) if x), answer,
            )
        except Exception as exc:
            failure = "Body fallback: conversation unavailable (%s)." % type(exc).__name__
            self._remember(
                organism, "MIND_FAILURE",
                resident_vcw_event("MIND_FAILURE", {"error_type": type(exc).__name__},
                                   source="resident-runtime", ok=False),
            )
            answer = self.deterministic_answer(failure, evidence)
            return ResidentTurnResult(
                "mind_fallback", failure, vcw_event_ids=tuple(
                    x for x in (user_event_id,) if x), answer=answer,
            )

    @staticmethod
    def _remember(organism: Any, opcode: str, event: Dict[str, Any]) -> str:
        if organism is None:
            return ""
        try:
            entry = organism.memory.remember(
                "events", event, opcode=opcode, source="resident-runtime"
            )
            return str(entry.get("hash") or entry.get("id") or "")
        except Exception:
            return ""

