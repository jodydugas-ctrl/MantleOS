"""Small stdlib-only regression checks for Mantle 2 public contracts."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from mantle.assimilator.coverage import CoverageState, SubstrateCoverage
from mantle.contracts import ClaimStatus, EvidenceRef, ResidentRuntime
from mantle.core.authority import build_fusion_authorization
from mantle.lifecycle import (LifecycleAction, LifecycleAuthorization,
                              LifecycleAuthorizationError,
                              validate_authorization)
from mantle.proofs import ActionExecutionProof, MutationClass, require_verified_post_state


def main() -> int:
    ref = EvidenceRef("test", "stable-1", "contract-test")
    claim = ResidentRuntime.classify_claim("measured", ClaimStatus.VERIFIED, (ref,))
    assert claim.status is ClaimStatus.VERIFIED
    assert ResidentRuntime.classify_claim("unsupported", ClaimStatus.VERIFIED).status is ClaimStatus.REFUSED
    assert SubstrateCoverage("rust", 8, 100, 0, total_first_party_files=10,
                             total_first_party_bytes=150).state is CoverageState.BLOCKED
    auth = build_fusion_authorization("resident", operator_approved=True, guardian_approved=True)
    assert auth["effective_decision"]["mind_fusion_authorized"] is True
    proof = ActionExecutionProof("read", "surface", "target", "low", MutationClass.READ,
                                 {"before": True}, {"attempted": True}, {"after": True},
                                 "test", True)
    require_verified_post_state(proof)
    with tempfile.TemporaryDirectory() as tmp:
        artifact = Path(tmp) / "artifact"
        artifact.write_text("carrier", encoding="utf-8")
        issued = LifecycleAuthorization.issue(LifecycleAction.HATCH, str(artifact), "nest")
        validate_authorization(issued, LifecycleAction.HATCH, str(artifact), "nest")
        try:
            validate_authorization(issued, LifecycleAction.GRAFT, str(artifact), "nest")
        except LifecycleAuthorizationError:
            pass
        else:
            raise AssertionError("wrong lifecycle action must be refused")
    print(json.dumps({"ok": True, "checks": 6}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

