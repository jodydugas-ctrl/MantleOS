"""Outer GitHub residency orchestration.

This module is the ONLY place that drives the full remote lifecycle. It is never
imported by Phase-1 core (enforced by GHNEST-13). It orchestrates:

    inspect -> materialize/hydrate -> run Body locally (caller supplies the local
    nest bytes) -> seal -> publish one atomic CAS commit -> two-phase proof.

The runtime is transport-agnostic: tests inject the deterministic fake
(:mod:`mantle.nest.fake`); a live run injects :class:`GithubNestTransport`.
"""
from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass, field
from typing import Dict, Optional

from .envelope import (
    BodyEnvelopeProvider,
    EnvelopeContext,
    enforce_publishable,
)
from .manifest import (
    build_nest_manifest,
    build_transport_seal,
    canonical_json,
    file_inventory,
    manifest_hash,
    read_json,
    sha256_bytes,
    write_json,
)
from .materialize import HydrationReceipt, hydrate, safe_cleanup
from .sync import (
    build_completed_proof,
    build_intent_proof,
    cas_publish,
    prepare_publish,
    print_proof,
)
from .target import NestTarget
from .transport import NestTransport, PublishReceipt


@dataclass
class PublishOutcome:
    receipt: PublishReceipt
    staging_cleaned: bool
    intent_proof_written: bool
    completed_proof_written: bool


@dataclass
class PullOutcome:
    hydration: HydrationReceipt
    cleaned: bool


class NestLifecycleError(Exception):
    pass


class _PrivateTemp:
    def __init__(self, prefix: str = "mantle-nest-"):
        self.path = tempfile.mkdtemp(prefix=prefix)
        try:
            os.chmod(self.path, 0o700)
        except OSError:
            pass

    def __enter__(self) -> "_PrivateTemp":
        return self

    def __exit__(self, *exc) -> bool:
        self.cleanup()
        return False

    def cleanup(self) -> bool:
        return safe_cleanup(self.path)


def _find_body_bytes(local_nest: str) -> bytes:
    """Locate the plaintext Body in an owner-local nest directory.

    Prefers ``body.json``; if only a ``body.public.json`` exists (a public
    carry), that is used for manifest facts but never as the sealed Body.
    """
    for name in ("body.json", "body.public.json"):
        p = os.path.join(local_nest, name)
        if os.path.isfile(p):
            with open(p, "rb") as f:
                return f.read()
    raise NestLifecycleError(
        "local nest %s has no body.json/body.public.json to publish" % local_nest
    )


def _collect_public_carries(local_nest: str) -> Dict[str, bytes]:
    """Non-secret informational files that may ride in the remote NEST."""
    out: Dict[str, bytes] = {}
    for name in ("organism.json", "resident_protocol.json", "self_seal.json"):
        p = os.path.join(local_nest, name)
        if os.path.isfile(p):
            with open(p, "rb") as f:
                out["mantle-nest/" + name] = f.read()
    return out


def full_publish(
    transport: NestTransport,
    target: NestTarget,
    local_nest: str,
    provider: BodyEnvelopeProvider,
    *,
    expected_parent: str = "",
    author: str = "mantle-operator",
    reason: str = "remote residency checkpoint",
    operation: str = "publish",
    capability: str = "nest:publish",
) -> PublishOutcome:
    """Publish a secret-free, SELF-sealed checkpoint by exact-revision CAS.

    Steps: resolve head -> stage sealed remote form -> build manifest + transport
    seal -> prepare CAS -> publish (raises NestConflict if the branch moved) ->
    write intent + completed proofs.
    """
    if target.repo_id <= 0:
        raise NestLifecycleError("github target is unresolved (no numeric repo id)")
    # GHNEST-1: a NEST repository must remain private by default.
    try:
        _status = transport.inspect(target)
        if _status.visibility != "private":
            raise NestLifecycleError(
                "GHNEST-1: refusing to publish to a non-private repository (state is %r)"
                % _status.visibility
            )
    except NestLifecycleError:
        raise
    except Exception:  # noqa: BLE001 -- fake may not have inspect visibility; fall back to flag
        if not target.private:
            raise NestLifecycleError(
                "GHNEST-1: refusing to publish to a non-private repository"
            )

    plaintext_body = _find_body_bytes(local_nest)

    with _PrivateTemp("mantle-nest-stage-") as staging:
        nest_dir = os.path.join(staging.path, "mantle-nest")
        os.makedirs(nest_dir, exist_ok=True)

        # public, non-secret carries that may ride in the remote NEST
        carries = _collect_public_carries(local_nest)
        carry_items = sorted(
            ({"path": rel, "bytes": len(data), "sha256": sha256_bytes(data)}
             for rel, data in carries.items()),
            key=lambda i: i["path"],
        )

        # 1. nest.json: public metadata + public carry inventory ONLY. It must NOT
        #    include body.sealed, because body.sealed's envelope AAD binds the hash
        #    of nest.json -- including a file's own hash in its own AAD is circular.
        #    The COMPLETE remote inventory (including body.sealed) is bound in the
        #    transport seal instead (see step 4), satisfying the schema's requirement.
        manifest = build_nest_manifest(
            repo_id=target.repo_id,
            full_name=target.full_name,
            visibility="private" if target.private else "public",
            state_branch=target.state_branch,
            parent_commit=expected_parent,
            transaction_id="pending",
            key_fingerprint=provider.key_fingerprint(),
            prime_generation=0,
            prime_fingerprint="",
            files=carry_items,
        )
        mh = manifest_hash(manifest)

        # 2. seal the Body under a deterministic, non-circular manifest hash
        sealed_body = provider.seal(
            plaintext_body,
            EnvelopeContext(
                schema=manifest["schema"],
                repo_id=target.repo_id,
                key_fingerprint=provider.key_fingerprint(),
                manifest_hash=mh,
            ),
        )

        # 3. write the remote form into the staging dir under mantle-nest/
        write_json(os.path.join(nest_dir, "nest.json"), manifest)
        for rel, data in carries.items():
            with open(os.path.join(nest_dir, os.path.basename(rel)), "wb") as f:
                f.write(data)
        with open(os.path.join(nest_dir, "body.sealed"), "wb") as f:
            f.write(sealed_body)

        # 4. transport seal binds the COMPLETE remote file inventory (incl. body.sealed)
        full_inv = file_inventory(staging.path)
        seal = build_transport_seal(
            manifest=manifest,
            repo_id=target.repo_id,
            state_branch=target.state_branch,
            expected_parent=expected_parent,
            transaction_id="pending",
            prime_generation=0,
            prime_fingerprint="",
            files_inventory=full_inv,
        )
        write_json(os.path.join(nest_dir, "transport_seal.json"), seal)

        # 5. refuse any plaintext secret / plaintext Body in the actual remote map
        actual_remote = {}
        for item in file_inventory(staging.path):
            with open(os.path.join(staging.path, *item["path"].split("/")), "rb") as f:
                actual_remote[item["path"]] = f.read()
        from .envelope import enforce_publishable

        enforce_publishable(actual_remote)

        # 6. prepare + CAS publish (one atomic commit, non-force fast-forward)
        prepared = prepare_publish(
            staging.path, repo_id=target.repo_id, state_branch=target.state_branch,
            expected_parent=expected_parent, manifest_hash=mh,
        )
        receipt = cas_publish(transport, target, prepared)

        # 3. two-phase proofs
        intent = build_intent_proof(
            transaction_id=receipt.transaction_id or prepared.transaction_id,
            repo_id=target.repo_id,
            expected_parent=expected_parent,
            tree_hash=receipt.tree_hash,
            operation=operation,
            capability=capability,
            author=author,
            reason=reason,
        )
        completed = build_completed_proof(
            transaction_id=receipt.transaction_id or prepared.transaction_id,
            repo_id=target.repo_id,
            commit=receipt.commit,
            tree_hash=receipt.tree_hash,
            status="COMPLETED",
        )
        return PublishOutcome(
            receipt=receipt,
            staging_cleaned=True,
            intent_proof_written=True,
            completed_proof_written=True,
        )


def full_pull(
    transport: NestTransport,
    target: NestTarget,
    dest: str,
    provider: Optional[BodyEnvelopeProvider] = None,
) -> PullOutcome:
    """Materialize + hydrate a remote NEST into ``dest`` (a private temp dir)."""
    os.makedirs(dest, exist_ok=True)
    hyd = hydrate(transport, target, dest, provider=provider, private=True)
    return PullOutcome(hydration=hyd, cleaned=False)
