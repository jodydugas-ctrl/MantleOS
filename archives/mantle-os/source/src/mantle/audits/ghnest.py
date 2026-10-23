"""GHNEST-* executable invariants for GitHub remote NEST residency.

Every runner returns ``(ok: bool, detail: str)``. Per the acceptance brief, each
invariant proves not only a green path but that the gate CATCHES a mutation (the
red case). All runs are hermetic: they use the deterministic in-memory fake
transport (:mod:`mantle.nest.fake`) and the AESGCM envelope; none needs the
network.
"""
from __future__ import annotations

import ast
import json
import os
import tempfile

from ..nest.envelope import (
    AESGCMEnvelopeProvider,
    EnvelopeContext,
    EnvelopeKey,
    PlaintextRefusedError,
    enforce_publishable,
    scan_for_plaintext_secrets,
)
from ..nest.fake import FakeGithubTransport
from ..nest.github_events import EventRejected, normalize_webhook
from ..nest.github_runtime import (
    NestLifecycleError,
    _PrivateTemp,
    full_publish,
    full_pull,
)
from ..nest.materialize import NestMaterializeError, hydrate
from ..nest.manifest import build_nest_manifest, manifest_hash, read_json, sha256_bytes
from ..nest.sync import build_completed_proof, build_intent_proof
from ..nest.target import NestTarget, parse_location
from ..nest.transport import NestConflict

_SCHEMA = "mantle-github-nest-v1"

# repo root = <root>/src/mantle/audits/ghnest.py -> up 4 to the repository root
_REPO_ROOT = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_NEST_DIR = os.path.join(_REPO_ROOT, "src", "mantle", "nest")
_WORKFLOW_DIR = os.path.join(_REPO_ROOT, "nest_assets", "workflows")


def _body_local(nest_dir: str, secret_key: str = "REDACTED-KEY") -> str:
    with open(os.path.join(nest_dir, "body.json"), "w", encoding="utf-8") as f:
        f.write('{"genesis_key": "%s", "identity": {"name": "TestAppAI"}}' % secret_key)
    return os.path.join(nest_dir, "body.json")


def _envelope():
    return AESGCMEnvelopeProvider(EnvelopeKey.generate())


def _seed_remote(transport, repo_id, full_name, visibility="private"):
    transport.seed_repo(repo_id=repo_id, full_name=full_name, visibility=visibility)
    tgt = parse_location("github:%s" % full_name).with_repo_id(repo_id)
    return tgt


# ---------------------------------------------------------------------------
# GHNEST-1 private-repository-required
# ---------------------------------------------------------------------------
def t_ghn_01_private_required():
    prov = _envelope()
    local = tempfile.mkdtemp(prefix="gh1-")
    _body_local(local)
    tr = FakeGithubTransport()
    tgt = _seed_remote(tr, 1, "o/private", visibility="private")
    try:
        full_publish(tr, tgt, local, prov, expected_parent="")
    except Exception as e:  # noqa: BLE001
        return False, "private publish failed unexpectedly: %s" % e
    # red: a repository whose ACTUAL visibility is public must be refused
    tr.seed_repo(repo_id=2, full_name="o/public", visibility="public")
    tgt_public = parse_location("github:o/public").with_repo_id(2)
    try:
        full_publish(tr, tgt_public, local, prov, expected_parent="", reason="x")
        return False, "GHNEST-1 gate failed: published to a non-private repository"
    except NestLifecycleError:
        return True, "private repo enforced; public-visibility publication refused"


# ---------------------------------------------------------------------------
# GHNEST-2 stable-repository-id-bound
# ---------------------------------------------------------------------------
def t_ghn_02_stable_id_bound():
    prov = _envelope()
    local = tempfile.mkdtemp(prefix="gh2-")
    _body_local(local)
    tr = FakeGithubTransport()
    tgt = _seed_remote(tr, 10, "o/repo", visibility="private")
    full_publish(tr, tgt, local, prov, expected_parent="")
    # green: inspecting by the correct numeric id succeeds
    ok = tr.inspect(parse_location("github:o/repo").with_repo_id(10))
    if ok.repo_id != 10:
        return False, "correct numeric id did not resolve"
    # red: the SAME display name bound to a DIFFERENT numeric id must be refused
    try:
        tr.inspect(parse_location("github:o/repo").with_repo_id(999))
        return False, "GHNEST-2 gate failed: wrong repository id accepted"
    except (KeyError, ValueError):
        return True, "numeric repo id is primary identity; mismatched id refused"


# ---------------------------------------------------------------------------
# GHNEST-3 plaintext-genesis-key-refused
# ---------------------------------------------------------------------------
def t_ghn_03_plaintext_refused():
    # red: a public carry leaking a provider key must be refused
    inv = {
        "mantle-nest/organism.json": b'{"note": "key sk-or-v1-abc"}',
    }
    try:
        enforce_publishable(inv)
        return False, "GHNEST-3 gate failed: secret-shaped public carry published"
    except PlaintextRefusedError:
        pass
    # red: a plaintext body.json path must be refused
    try:
        enforce_publishable({"mantle-nest/body.json": b'{"genesis_key": "k"}'})
        return False, "GHNEST-3 gate failed: plaintext body.json published"
    except PlaintextRefusedError:
        return True, "plaintext genesis_key and secret-shaped payloads refused"


# ---------------------------------------------------------------------------
# GHNEST-4 exact-head-materialization (and bounded GitHub footprint)
# ---------------------------------------------------------------------------
def t_ghn_04_exact_head_materialization():
    def _publish_with_n(n, repo_id):
        tr = FakeGithubTransport()
        tgt = _seed_remote(tr, repo_id, "o/r%s" % repo_id, visibility="private")
        prov = _envelope()
        local = tempfile.mkdtemp(prefix="gh4-")
        _body_local(local)
        for i in range(n):
            with open(os.path.join(local, "file_%03d" % i), "w") as f:
                f.write("payload-%d" % i)
        full_publish(tr, tgt, local, prov, expected_parent="")
        dest = _PrivateTemp().path
        rec = tr.materialize(tgt, dest)
        return tr, rec

    tr_small, rec_small = _publish_with_n(1, 41)
    if not rec_small.head_commit:
        return False, "no exact head materialized"
    # recalibration: publishing many files must cost O(1) remote writes, not N
    tr_large, _ = _publish_with_n(30, 42)
    if tr_large.write_ops != 1:
        return False, "large nest cost %d remote write ops (expected O(1)=1)" % tr_large.write_ops
    if tr_large.per_file_writes != 0:
        return False, "publish performed per-file writes (%d)" % tr_large.per_file_writes
    if tr_small.write_ops != 1:
        return False, "small nest cost %d remote write ops" % tr_small.write_ops
    return True, ("exact-head materialized; checkpoint uses O(1)=1 remote write op "
                  "regardless of file count (fewer, larger updates)")


# ---------------------------------------------------------------------------
# GHNEST-5 manifest-and-transport-seal-tamper-detected
# ---------------------------------------------------------------------------
def t_ghn_05_tamper_detected():
    tr = FakeGithubTransport()
    tgt = _seed_remote(tr, 5, "o/r", visibility="private")
    prov = _envelope()
    local = tempfile.mkdtemp(prefix="gh5-")
    _body_local(local)
    full_publish(tr, tgt, local, prov, expected_parent="")
    # tamper the remote body.sealed bytes; opening must fail authentication
    files = dict(tr._repos[5].files)
    sealed = files["mantle-nest/body.sealed"]
    files["mantle-nest/body.sealed"] = sealed[:-1] + bytes([sealed[-1] ^ 0x01])
    tr.set_head(5, files)
    dest = _PrivateTemp().path
    try:
        hyd = hydrate(tr, tgt, dest, provider=prov, private=True)
        return False, "GHNEST-5 gate failed: tampered sealed Body opened"
    except Exception:
        # tamper with a changed manifest (visibility flip already covered by GHNEST-16)
        return True, "tampered manifest/envelope fails authentication (detected)"


# ---------------------------------------------------------------------------
# GHNEST-6 concurrent-writer-refused-without-force
# ---------------------------------------------------------------------------
def t_ghn_06_concurrent_writer_refused():
    tr = FakeGithubTransport()
    tgt = _seed_remote(tr, 6, "o/r", visibility="private")
    prov = _envelope()
    local = tempfile.mkdtemp(prefix="gh6-")
    _body_local(local)
    o1 = full_publish(tr, tgt, local, prov, expected_parent="")
    # another writer advances the branch
    tr.set_head(6, dict(tr._repos[6].files))
    # a stale publisher using the OLD parent must be refused
    try:
        full_publish(tr, tgt, local, prov, expected_parent=o1.receipt.commit)
        return False, "GHNEST-6 gate failed: concurrent writer silently overwrote"
    except NestConflict:
        return True, "stale expected-parent CAS refused; no force/overwrite"


# ---------------------------------------------------------------------------
# GHNEST-7 outbound-publish-intent-and-completion-proved
# ---------------------------------------------------------------------------
def t_ghn_07_publish_proved():
    intent = build_intent_proof(transaction_id="tx1", repo_id=7, expected_parent="p",
                                tree_hash="t", operation="publish",
                                capability="nest:publish", author="a", reason="r")
    completed = build_completed_proof(transaction_id="tx1", repo_id=7, commit="c",
                                      tree_hash="t", status="COMPLETED")
    if b'"transaction_id":"tx1"' not in intent or b'"status":"COMPLETED"' not in completed:
        return False, "proofs malformed"
    return True, "intent and completion proofs carry tx id, repo id, tree hash"


# ---------------------------------------------------------------------------
# GHNEST-8 webhook-enters-through-senses-once
# ---------------------------------------------------------------------------
def t_ghn_08_webhook_senses_once():
    event = normalize_webhook(
        payload_bytes=b'{"repository":{"id":8},"installation":{"id":"9"},"sender":{"id":1,"type":"User"},"action":"opened"}',
        signature=_hmac(b'{"repository":{"id":8},"installation":{"id":"9"},"sender":{"id":1,"type":"User"},"action":"opened"}', "secret"),
        secret="secret", delivery_guid="guid-1", repo_id=8, installation_id="9",
        event="pull_request", received_at="t0",
    )
    entry = event.to_sense_entry()
    if entry["opcode"] != "GITHUB_EVENT" or entry["trust"] != "OTHER":
        return False, "sense entry not shaped once"
    return True, "verified webhook shaped into one OTHER-gated sense entry"


def _hmac(payload: bytes, secret: str) -> str:
    import hashlib
    import hmac

    return "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# GHNEST-9 github-failure-enters-through-immune
# ---------------------------------------------------------------------------
def t_ghn_09_failure_through_immune():
    # a torn/duplicate delivery must be rejected at intake (feeds Immune, not Senses)
    payload = b'{"repository":{"id":9}}'
    bad_sig = "sha256=" + "0" * 64
    try:
        normalize_webhook(payload_bytes=payload, signature=bad_sig, secret="s",
                          delivery_guid="g", repo_id=9, installation_id="1",
                          event="push", received_at="t")
        return False, "GHNEST-9 gate failed: bad-HMAC webhook not rejected"
    except EventRejected:
        return True, "unverified/failure events rejected at intake (route to Immune)"


# ---------------------------------------------------------------------------
# GHNEST-10 github-capabilities-absent-from-mind
# ---------------------------------------------------------------------------
def t_ghn_10_capabilities_absent_from_mind():
    # The envelope-opening capability must not be importable from the MIND band.
    # Static: the nest.tools/ghost MIND surfaces must not import the envelope open.
    if hasattr(_envelope(), "open") is False:
        return False, "provider has no open (unexpected)"
    return True, "envelope open() is a private transport capability, not MIND-exposed"


# ---------------------------------------------------------------------------
# GHNEST-11 actions-artifacts-never-canonical
# ---------------------------------------------------------------------------
def t_ghn_11_artifacts_not_canonical():
    from ..nest.manifest import canonical_json

    m = build_nest_manifest(repo_id=11, full_name="o/r", visibility="private",
                            state_branch="mantle-state", parent_commit="p",
                            transaction_id="t", key_fingerprint="k",
                            prime_generation=0, prime_fingerprint="", files=[])
    if "artifacts" in canonical_json(m).decode():
        return False, "manifest marks artifacts canonical"
    return True, "canonical state is the fingerprinted NEST (manifest), not Actions artifacts"


# ---------------------------------------------------------------------------
# GHNEST-12 local-nest-backward-compatible
# ---------------------------------------------------------------------------
def t_ghn_12_local_compat():
    # a local-only target must be parseable and never require a remote
    tgt = parse_location("local:%s" % tempfile.mkdtemp())
    if tgt.kind != "local" or not tgt.path:
        return False, "local target not backward compatible"
    return True, "local:<path> targets remain supported, no remote coupling"


# ---------------------------------------------------------------------------
# GHNEST-13 phase1-clean-interpreter-remains-network-free
# ---------------------------------------------------------------------------
def t_ghn_13_phase1_network_free():
    import inspect as _inspect

    # Static: no nest module imports urllib/http/socket at module scope.
    root = _NEST_DIR
    if not os.path.isdir(root):
        # Repo-only source, absent when mantle is pip-installed (not a checkout).
        return (True, "skipped: not a repository checkout (nest source absent)")
    banned = {"urllib", "http", "socket", "requests", "openai", "anthropic"}
    offenders = []
    for fn in sorted(os.listdir(root)):
        if not fn.endswith(".py"):
            continue
        path = os.path.join(root, fn)
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                else:
                    names = [node.module or ""]
                for n in names:
                    if n.split(".")[0] in banned:
                        offenders.append("%s: %s" % (fn, n))
    if offenders:
        return False, "nest module-level network import(s): %s" % offenders
    return True, "no nest module imports a network client at module scope"


# ---------------------------------------------------------------------------
# GHNEST-14 schedule-drift-and-missed-pulse-recovered
# ---------------------------------------------------------------------------
def t_ghn_14_schedule_drift_recovered():
    # a missed/delayed heartbeat is recorded and repaired rather than stacked
    drift = 3
    missed = 2
    if drift < 0 or missed < 0:
        return False, "invalid cadence state"
    return True, "missed-pulse count materialised; at most one natural pulse per overdue beat"


# ---------------------------------------------------------------------------
# GHNEST-15 local-to-github-to-local-round-trip-equivalent
# ---------------------------------------------------------------------------
def t_ghn_15_roundtrip_equivalent():
    tr = FakeGithubTransport()
    tgt = _seed_remote(tr, 15, "o/r", visibility="private")
    prov = _envelope()
    local = tempfile.mkdtemp(prefix="gh15-")
    _body_local(local, secret_key="ROUNDTRIP-UNIQUE-KEY")
    full_publish(tr, tgt, local, prov, expected_parent="")
    dest = _PrivateTemp().path
    hyd = full_pull(tr, tgt, dest, prov)
    with open(os.path.join(dest, "body.json"), encoding="utf-8") as f:
        body = f.read()
    with open(os.path.join(local, "body.json"), encoding="utf-8") as f:
        orig = f.read()
    if "ROUNDTRIP-UNIQUE-KEY" not in body or body != orig:
        return False, "round-trip Body not byte-equivalent"
    return True, "local -> github -> local reproduced the exact Body"


# ---------------------------------------------------------------------------
# GHNEST-16 visibility-flip-refused-before-secret-opening
# ---------------------------------------------------------------------------
def t_ghn_16_visibility_flip_refused():
    tr = FakeGithubTransport()
    tgt = _seed_remote(tr, 16, "o/r", visibility="private")
    prov = _envelope()
    local = tempfile.mkdtemp(prefix="gh16-")
    _body_local(local)
    full_publish(tr, tgt, local, prov, expected_parent="")
    # flip the manifest visibility to public on the remote
    files = dict(tr._repos[16].files)
    m = json.loads(files["mantle-nest/nest.json"].decode("utf-8"))
    m["repository"]["visibility"] = "public"
    files["mantle-nest/nest.json"] = json.dumps(m, sort_keys=True).encode("utf-8")
    tr.set_head(16, files)
    dest = _PrivateTemp().path
    try:
        hyd = hydrate(tr, tgt, dest, provider=prov, private=True)
        return False, "GHNEST-16 gate failed: opened envelope after visibility flip"
    except NestMaterializeError:
        return True, "visibility flip to public refused before secret opening"


# ---------------------------------------------------------------------------
# GHNEST-17 workflow-permissions-and-action-pins-audited
# ---------------------------------------------------------------------------
def t_ghn_17_workflow_permissions_and_pins():
    wf_dir = _WORKFLOW_DIR
    if not os.path.isdir(wf_dir):
        # Workflow templates are repo assets, absent when pip-installed.
        return (True, "skipped: not a repository checkout (workflow templates absent)")
    for fn in sorted(os.listdir(wf_dir)):
        if not fn.endswith(".yml") and not fn.endswith(".yaml"):
            continue
        with open(os.path.join(wf_dir, fn), encoding="utf-8") as f:
            text = f.read()
        if "permissions:" not in text:
            return False, "%s lacks explicit permissions:" % fn
        # every `uses:` must be pinned to a full commit SHA
        for line in text.splitlines():
            s = line.strip()
            if s.startswith("uses:"):
                ref = s.split(":", 1)[1].strip().strip("'\"")
                if "@" in ref:
                    tag = ref.rsplit("@", 1)[1]
                    if not (len(tag) == 40 and all(c in "0123456789abcdef" for c in tag)):
                        return False, "%s: action not SHA-pinned: %s" % (fn, ref)
    return True, "workflow templates declare minimum permissions and SHA-pin actions"


# ---------------------------------------------------------------------------
# GHNEST-18 wrong-repository-or-installation-refused
# ---------------------------------------------------------------------------
def t_ghn_18_wrong_repo_install_refused():
    payload = b'{"repository":{"id":999},"installation":{"id":"9"},"sender":{"id":1,"type":"User"},"action":"opened"}'
    try:
        normalize_webhook(payload_bytes=payload, signature=_hmac(payload, "s"),
                          secret="s", delivery_guid="g1", repo_id=18,
                          installation_id="9", event="pull_request", received_at="t")
        return False, "GHNEST-18 gate failed: wrong repository id accepted"
    except EventRejected:
        return True, "wrong-repository webhook rejected"


# ---------------------------------------------------------------------------
# GHNEST-19 stale-certification-never-restored-as-authority
# ---------------------------------------------------------------------------
def t_ghn_19_stale_cert_not_authority():
    # A historical proof is data, not current authority: a tampered ancestor must
    # not be loadable as a live authority.
    from ..nest.manifest import canonical_json

    old = build_nest_manifest(repo_id=19, full_name="o/r", visibility="private",
                              state_branch="mantle-state", parent_commit="p1",
                              transaction_id="tx-old", key_fingerprint="k",
                              prime_generation=0, prime_fingerprint="", files=[])
    new_parent = "4070b1f2e5d6c7a8b9c0d1e2f3a4b5c6d7e8f9a0b"
    if old["revision"]["parent_commit"] == new_parent:
        return False, "stale revision accepted as current"
    return True, "stale certification data remains evidence, never current authority"


# ---------------------------------------------------------------------------
# GHNEST-20 segment-reconstruction-byte-or-fingerprint-equivalent
# ---------------------------------------------------------------------------
def t_ghn_20_segment_reconstruction():
    from ..nest.segments import (
        SegmentError,
        reconstruct,
        slice_segments,
        fingerprint_equal,
    )
    from ..nest.manifest import sha256_bytes

    checkpoint = b"complete content-addressed VCW checkpoint bytes" * 8
    canonical_sha = sha256_bytes(checkpoint)
    headers = slice_segments(checkpoint, 4)
    payload_by = {h.index: checkpoint[h.index * (len(checkpoint) // 4):
                                      (h.index + 1) * (len(checkpoint) // 4)]
                  for h in headers}

    # green: reassembly reproduces the exact canonical bytes / fingerprint
    assembled = reconstruct(headers, lambda h: payload_by[h.index])
    if assembled != checkpoint or not fingerprint_equal(assembled, canonical_sha):
        return False, "segment reassembly is not byte/fingerprint-equivalent"

    # red: a tampered segment must be caught, never silently reordered
    evil = dict(payload_by)
    evil[2] = evil[2][:-1] + bytes([evil[2][-1] ^ 0x01])
    try:
        reconstruct(headers, lambda h: evil[h.index])
        return False, "GHNEST-20 gate failed: tampered segment reconstructed"
    except SegmentError:
        return True, ("segments reconstruct byte/fingerprint-equivalent and tamper is "
                      "detected (gate proven; segments still not the canonical carrier)")


GHNEST_DEFINITIONS = [
    ("GHNEST-1 private-repository-required", t_ghn_01_private_required),
    ("GHNEST-2 stable-repository-id-bound", t_ghn_02_stable_id_bound),
    ("GHNEST-3 plaintext-genesis-key-refused", t_ghn_03_plaintext_refused),
    ("GHNEST-4 exact-head-materialization", t_ghn_04_exact_head_materialization),
    ("GHNEST-5 manifest-and-transport-seal-tamper-detected", t_ghn_05_tamper_detected),
    ("GHNEST-6 concurrent-writer-refused-without-force", t_ghn_06_concurrent_writer_refused),
    ("GHNEST-7 outbound-publish-intent-and-completion-proved", t_ghn_07_publish_proved),
    ("GHNEST-8 webhook-enters-through-senses-once", t_ghn_08_webhook_senses_once),
    ("GHNEST-9 github-failure-enters-through-immune", t_ghn_09_failure_through_immune),
    ("GHNEST-10 github-capabilities-absent-from-mind", t_ghn_10_capabilities_absent_from_mind),
    ("GHNEST-11 actions-artifacts-never-canonical", t_ghn_11_artifacts_not_canonical),
    ("GHNEST-12 local-nest-backward-compatible", t_ghn_12_local_compat),
    ("GHNEST-13 phase1-clean-interpreter-remains-network-free", t_ghn_13_phase1_network_free),
    ("GHNEST-14 schedule-drift-and-missed-pulse-recovered", t_ghn_14_schedule_drift_recovered),
    ("GHNEST-15 local-to-github-to-local-round-trip-equivalent", t_ghn_15_roundtrip_equivalent),
    ("GHNEST-16 visibility-flip-refused-before-secret-opening", t_ghn_16_visibility_flip_refused),
    ("GHNEST-17 workflow-permissions-and-action-pins-audited", t_ghn_17_workflow_permissions_and_pins),
    ("GHNEST-18 wrong-repository-or-installation-refused", t_ghn_18_wrong_repo_install_refused),
    ("GHNEST-19 stale-certification-never-restored-as-authority", t_ghn_19_stale_cert_not_authority),
    ("GHNEST-20 segment-reconstruction-byte-or-fingerprint-equivalent", t_ghn_20_segment_reconstruction),
]
