"""Authenticated, target-bound dual authority for MIND fusion."""

from __future__ import annotations

import base64
import binascii
from collections.abc import Mapping
import json
import os
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


class AuthorityError(PermissionError):
    """Fusion authority is absent, malformed, stale, or unauthenticated."""


def _canonical_payload(
    role: str,
    authorization: Mapping[str, Any],
    key_id: str,
) -> bytes:
    record = authorization.get(role)
    effective = authorization.get("effective_decision")
    if not isinstance(record, Mapping) or not isinstance(effective, Mapping):
        raise AuthorityError("fusion authorization is incomplete")
    payload = {
        "schema_version": "mantle-fusion-approval-v1",
        "role": role,
        "key_id": key_id,
        "fusion_decision": record.get("fusion_decision"),
        "recorded_at": authorization.get("recorded_at"),
        "target": authorization.get("target"),
        "mind_fusion_authorized": effective.get("mind_fusion_authorized"),
        "reproduction_activation_authorized": effective.get(
            "reproduction_activation_authorized"
        ),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


class Ed25519AuthorityProvider:
    """Verify approvals with public keys that cannot mint new approvals."""

    def __init__(
        self,
        *,
        operator_key_id: str,
        operator_public_key: bytes,
        guardian_key_id: str,
        guardian_public_key: bytes,
    ) -> None:
        if not operator_key_id or not guardian_key_id:
            raise ValueError("authority key ids must be non-empty")
        if operator_key_id == guardian_key_id:
            raise ValueError("operator and guardian key ids must be distinct")
        if len(operator_public_key) != 32 or len(guardian_public_key) != 32:
            raise ValueError("authority public keys must contain exactly 32 bytes")
        if operator_public_key == guardian_public_key:
            raise ValueError("operator and guardian keys must be independent")
        self._keys = {
            "operator": (
                operator_key_id,
                Ed25519PublicKey.from_public_bytes(operator_public_key),
            ),
            "guardian": (
                guardian_key_id,
                Ed25519PublicKey.from_public_bytes(guardian_public_key),
            ),
        }

    @classmethod
    def from_environment(
        cls, environment: Mapping[str, str] | None = None
    ) -> "Ed25519AuthorityProvider | None":
        """Load verifier-only public keys from the deployment environment."""
        env = environment or os.environ
        raw_values = {
            "operator_key_id": env.get("MANTLE_OPERATOR_KEY_ID", ""),
            "operator_public_key": env.get("MANTLE_OPERATOR_PUBLIC_KEY", ""),
            "guardian_key_id": env.get("MANTLE_GUARDIAN_KEY_ID", ""),
            "guardian_public_key": env.get("MANTLE_GUARDIAN_PUBLIC_KEY", ""),
        }
        if not any(raw_values.values()):
            return None
        try:
            return cls(
                operator_key_id=raw_values["operator_key_id"],
                operator_public_key=base64.b64decode(
                    raw_values["operator_public_key"], validate=True
                ),
                guardian_key_id=raw_values["guardian_key_id"],
                guardian_public_key=base64.b64decode(
                    raw_values["guardian_public_key"], validate=True
                ),
            )
        except (ValueError, binascii.Error) as exc:
            raise AuthorityError("fusion authority credentials are invalid") from exc

    def verify(self, authorization: Mapping[str, Any]) -> dict[str, Any]:
        """Authenticate both approvals and return a minimized core receipt."""
        if not isinstance(authorization, Mapping):
            raise AuthorityError("fusion authorization must be a mapping")
        target = authorization.get("target")
        effective = authorization.get("effective_decision")
        if not isinstance(target, Mapping) or not isinstance(effective, Mapping):
            raise AuthorityError("fusion authorization is incomplete")
        if (
            effective.get("mind_fusion_authorized") is not True
            or effective.get("reproduction_activation_authorized") is not False
        ):
            raise AuthorityError("fusion authorization has unsafe effective scope")

        for role, (expected_key_id, public_key) in self._keys.items():
            record = authorization.get(role)
            if not isinstance(record, Mapping):
                raise AuthorityError(f"{role} approval is missing")
            key_id = record.get("key_id")
            signature = record.get("signature")
            if key_id != expected_key_id or not isinstance(signature, str):
                raise AuthorityError(f"{role} approval key is not trusted")
            try:
                signature_bytes = base64.b64decode(signature, validate=True)
                public_key.verify(
                    signature_bytes,
                    _canonical_payload(role, authorization, expected_key_id),
                )
            except (InvalidSignature, ValueError, binascii.Error):
                raise AuthorityError(f"{role} approval signature is invalid")
            if record.get("fusion_decision") != "APPROVED":
                raise AuthorityError(f"{role} approval must explicitly approve fusion")

        return {
            "recorded_at": authorization.get("recorded_at"),
            "target": dict(target),
            "operator": {"fusion_decision": "APPROVED"},
            "guardian": {"fusion_decision": "APPROVED"},
            "effective_decision": {
                "mind_fusion_authorized": True,
                "reproduction_activation_authorized": False,
            },
        }
