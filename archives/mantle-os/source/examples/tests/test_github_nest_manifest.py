"""Hermetic GHNEST manifest tests (no network)."""
import os
import tempfile

import pytest

from mantle.nest import manifest as M
from mantle.nest.target import parse_location


def test_local_locator_parse():
    t = parse_location("local:" + tempfile.mkdtemp())
    assert t.kind == "local" and t.path


def test_github_locator_parse_unresolved():
    t = parse_location("github:jodydugas-ctrl/mantle-os")
    assert t.kind == "github" and not t.resolved()
    t2 = t.with_repo_id(1258266588)
    assert t2.resolved() and t2.repo_id == 1258266588


def test_bad_locator_rejected():
    with pytest.raises(ValueError):
        parse_location("ftp://nope")
    with pytest.raises(ValueError):
        parse_location("github:not a slug/nope")


def test_canonical_manifest_deterministic():
    a = M.build_nest_manifest(repo_id=1, full_name="o/r", visibility="private",
                              state_branch="mantle-state", parent_commit="p",
                              transaction_id="tx", key_fingerprint="k",
                              prime_generation=0, prime_fingerprint="", files=[])
    b = M.build_nest_manifest(repo_id=1, full_name="o/r", visibility="private",
                              state_branch="mantle-state", parent_commit="p",
                              transaction_id="tx", key_fingerprint="k",
                              prime_generation=0, prime_fingerprint="", files=[])
    assert M.canonical_json(a) == M.canonical_json(b)
    assert M.manifest_hash(a) == M.manifest_hash(b)


def test_manifest_authority_never_self():
    m = M.build_nest_manifest(repo_id=1, full_name="o/r", visibility="private",
                              state_branch="mantle-state", parent_commit="p",
                              transaction_id="tx", key_fingerprint="k",
                              prime_generation=0, prime_fingerprint="", files=[])
    assert m["authority"]["github_is_self"] is False
    assert m["authority"]["technical_evidence_only"] is True
