"""Body-owned proof records for visible host operations."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Dict, Optional


class MutationClass(str, Enum):
    READ = "read"
    REVERSIBLE = "reversible"
    DESTRUCTIVE = "destructive"
    EXTERNAL = "external"


@dataclass(frozen=True)
class ActionExecutionProof:
    operation: str
    target_surface: str
    target_identity: str
    risk: str
    mutation_class: MutationClass
    pre_state: Dict[str, Any]
    attempt: Dict[str, Any]
    post_state: Optional[Dict[str, Any]]
    verifier: str
    verified: bool
    vcw_receipt_id: Optional[str] = None
    refusal_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["mutation_class"] = self.mutation_class.value
        return result

    @classmethod
    def refused(cls, operation: str, target_surface: str, target_identity: str,
                reason: str, *, risk: str = "high",
                mutation_class: MutationClass = MutationClass.DESTRUCTIVE) -> "ActionExecutionProof":
        return cls(operation, target_surface, target_identity, risk, mutation_class,
                   {}, {}, None, "body-policy", False, refusal_reason=reason)


def require_verified_post_state(proof: ActionExecutionProof) -> None:
    """Reject a visible success claim without Body-owned post-state evidence."""
    if not proof.verified or proof.post_state is None:
        raise ValueError("visible operation success requires verified post-state evidence")

