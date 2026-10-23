"""Authentication boundary for operator and guardian fusion approval."""

from __future__ import annotations

import base64
import json
from pathlib import Path
import sys
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mantle_addon.authority import (
    AuthorityError,
    Ed25519AuthorityProvider,
)


def _sign(role, authorization, key_id, key):
    record = authorization[role]
    payload = {
        "schema_version": "mantle-fusion-approval-v1",
        "role": role,
        "key_id": key_id,
        "fusion_decision": record["fusion_decision"],
        "recorded_at": authorization["recorded_at"],
        "target": authorization["target"],
        "mind_fusion_authorized": authorization["effective_decision"][
            "mind_fusion_authorized"
        ],
        "reproduction_activation_authorized": authorization["effective_decision"][
            "reproduction_activation_authorized"
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return base64.b64encode(key.sign(encoded)).decode()


def _public_bytes(private_key):
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


class AuthorityProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.operator_key = Ed25519PrivateKey.from_private_bytes(b"o" * 32)
        self.guardian_key = Ed25519PrivateKey.from_private_bytes(b"g" * 32)
        self.provider = Ed25519AuthorityProvider(
            operator_key_id="operator-2026",
            operator_public_key=_public_bytes(self.operator_key),
            guardian_key_id="guardian-2026",
            guardian_public_key=_public_bytes(self.guardian_key),
        )
        self.authorization = {
            "recorded_at": "2026-07-15T12:00:00+00:00",
            "target": {
                "resident_identity": "resident",
                "body_fingerprint": "fingerprint",
            },
            "operator": {
                "fusion_decision": "APPROVED",
                "key_id": "operator-2026",
            },
            "guardian": {
                "fusion_decision": "APPROVED",
                "key_id": "guardian-2026",
            },
            "effective_decision": {
                "mind_fusion_authorized": True,
                "reproduction_activation_authorized": False,
            },
        }
        for role, key in (
            ("operator", self.operator_key),
            ("guardian", self.guardian_key),
        ):
            key_id = self.authorization[role]["key_id"]
            self.authorization[role]["signature"] = _sign(
                role, self.authorization, key_id, key
            )

    def test_valid_independent_approvals_reduce_to_core_receipt(self):
        receipt = self.provider.verify(self.authorization)
        self.assertEqual("APPROVED", receipt["operator"]["fusion_decision"])
        self.assertEqual("APPROVED", receipt["guardian"]["fusion_decision"])
        self.assertNotIn("signature", str(receipt))

    def test_protocol_signature_matches_known_vector(self):
        self.assertEqual(
            "q/0ssKxFM6LGrIQJTPyDfPZluZ69X7QmGERU5lu+b+/l9YaBnam+7TOH"
            "WzW2Pt2DhnQdHqYysW2bnjSjFhnAAw==",
            self.authorization["operator"]["signature"],
        )

    def test_caller_authored_or_tampered_mapping_is_refused(self):
        self.authorization["target"]["resident_identity"] = "other"
        with self.assertRaisesRegex(AuthorityError, "signature is invalid"):
            self.provider.verify(self.authorization)

    def test_tampered_visible_decision_is_refused(self):
        self.authorization["operator"]["fusion_decision"] = "DEFERRED"
        with self.assertRaisesRegex(AuthorityError, "signature is invalid"):
            self.provider.verify(self.authorization)

    def test_roles_must_use_distinct_credentials(self):
        with self.assertRaisesRegex(ValueError, "independent"):
            Ed25519AuthorityProvider(
                operator_key_id="operator",
                operator_public_key=_public_bytes(self.operator_key),
                guardian_key_id="guardian",
                guardian_public_key=_public_bytes(self.operator_key),
            )

    def test_missing_environment_is_dormant_not_authorized(self):
        self.assertIsNone(Ed25519AuthorityProvider.from_environment({}))

    def test_environment_contains_verifier_only_public_keys(self):
        provider = Ed25519AuthorityProvider.from_environment(
            {
                "MANTLE_OPERATOR_KEY_ID": "operator-2026",
                "MANTLE_OPERATOR_PUBLIC_KEY": base64.b64encode(
                    _public_bytes(self.operator_key)
                ).decode(),
                "MANTLE_GUARDIAN_KEY_ID": "guardian-2026",
                "MANTLE_GUARDIAN_PUBLIC_KEY": base64.b64encode(
                    _public_bytes(self.guardian_key)
                ).decode(),
            }
        )

        self.assertEqual(
            "APPROVED", provider.verify(self.authorization)["operator"]["fusion_decision"]
        )


if __name__ == "__main__":
    unittest.main()
