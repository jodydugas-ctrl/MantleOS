"""Hermetic GHNEST envelope + materialization + sync tests (no network)."""
import os
import tempfile

import pytest

from mantle.nest.envelope import (
    AESGCMEnvelopeProvider,
    EnvelopeContext,
    EnvelopeKey,
    PlaintextRefusedError,
    enforce_publishable,
    scan_for_plaintext_secrets,
)
from mantle.nest.fake import FakeGithubTransport
from mantle.nest.github_runtime import _PrivateTemp, full_publish, full_pull
from mantle.nest.materialize import NestMaterializeError, hydrate
from mantle.nest.sync import build_completed_proof, build_intent_proof, prepare_publish
from mantle.nest.target import parse_location
from mantle.nest.transport import NestConflict


def _ctx():
    return EnvelopeContext(schema="mantle-github-nest-v1", repo_id=1,
                           key_fingerprint="k", manifest_hash="mh")


def test_envelope_roundtrip_and_tamper():
    prov = AESGCMEnvelopeProvider(EnvelopeKey.generate())
    sealed = prov.seal(b"SECRET BODY", _ctx())
    assert prov.open(sealed, _ctx()) == b"SECRET BODY"
    with pytest.raises(Exception):
        prov.open(b"garbage", _ctx())


def test_envelope_aad_binds_context():
    prov = AESGCMEnvelopeProvider(EnvelopeKey.generate())
    sealed = prov.seal(b"SECRET", _ctx())
    wrong = EnvelopeContext(schema="x", repo_id=2, key_fingerprint="z", manifest_hash="w")
    with pytest.raises(Exception):
        prov.open(sealed, wrong)


def test_plaintext_secret_refused():
    with pytest.raises(PlaintextRefusedError):
        enforce_publishable({"mantle-nest/organism.json": b'{"k":"sk-or-v1-abc"}'})
    with pytest.raises(PlaintextRefusedError):
        enforce_publishable({"mantle-nest/body.json": b'{"genesis_key":"k"}'})
    assert enforce_publishable({"mantle-nest/body.sealed": os.urandom(64)}) is None


def test_full_roundtrip_is_byte_equivalent():
    tr = FakeGithubTransport()
    tr.seed_repo(repo_id=7, full_name="o/r", visibility="private")
    tgt = parse_location("github:o/r").with_repo_id(7)
    prov = AESGCMEnvelopeProvider(EnvelopeKey.generate())
    local = tempfile.mkdtemp()
    with open(os.path.join(local, "body.json"), "w") as f:
        f.write('{"genesis_key":"UNIQUE","identity":{"name":"X"}}')
    full_publish(tr, tgt, local, prov, expected_parent="")
    dest = _PrivateTemp().path
    full_pull(tr, tgt, dest, prov)
    with open(os.path.join(dest, "body.json")) as f:
        assert "UNIQUE" in f.read()


def test_cas_rejects_stale_parent():
    tr = FakeGithubTransport()
    tr.seed_repo(repo_id=8, full_name="o/r", visibility="private")
    tgt = parse_location("github:o/r").with_repo_id(8)
    prov = AESGCMEnvelopeProvider(EnvelopeKey.generate())
    local = tempfile.mkdtemp()
    with open(os.path.join(local, "body.json"), "w") as f:
        f.write('{"genesis_key":"k"}')
    o1 = full_publish(tr, tgt, local, prov, expected_parent="")
    # another writer advances the branch before our stale publish
    tr.set_head(8, dict(tr._repos[8].files))
    with pytest.raises(NestConflict):
        full_publish(tr, tgt, local, prov, expected_parent=o1.receipt.commit)
    # fast-forward on the CURRENT parent remains legal (no conflict)
    head = tr._repos[8].head
    full_publish(tr, tgt, local, prov, expected_parent=head)


def test_visibility_flip_refused_before_open():
    import json as _json
    tr = FakeGithubTransport()
    tr.seed_repo(repo_id=9, full_name="o/r", visibility="private")
    tgt = parse_location("github:o/r").with_repo_id(9)
    prov = AESGCMEnvelopeProvider(EnvelopeKey.generate())
    local = tempfile.mkdtemp()
    with open(os.path.join(local, "body.json"), "w") as f:
        f.write('{"genesis_key":"k"}')
    full_publish(tr, tgt, local, prov, expected_parent="")
    files = dict(tr._repos[9].files)
    m = _json.loads(files["mantle-nest/nest.json"].decode())
    m["repository"]["visibility"] = "public"
    files["mantle-nest/nest.json"] = _json.dumps(m, sort_keys=True).encode()
    tr.set_head(9, files)
    dest = _PrivateTemp().path
    with pytest.raises(NestMaterializeError):
        hydrate(tr, tgt, dest, provider=prov, private=True)


def test_proofs_carry_binding_payload():
    intent = build_intent_proof(transaction_id="t", repo_id=1, expected_parent="p",
                                tree_hash="th", operation="publish",
                                capability="nest:publish", author="a", reason="r")
    completed = build_completed_proof(transaction_id="t", repo_id=1, commit="c",
                                      tree_hash="th", status="COMPLETED")
    assert b'"repository":{"id":1}' in intent and b'"transaction_id":"t"' in intent
    assert b'"status":"COMPLETED"' in completed


def test_scan_detects_provider_keys():
    assert scan_for_plaintext_secrets({"a.txt": b"deepseek_api_key = abc"}) is not None
    assert scan_for_plaintext_secrets({"a.txt": b"token sk-or-v1-abcdef"}) is not None
    assert scan_for_plaintext_secrets({"a.txt": b"benign body"}) is None
