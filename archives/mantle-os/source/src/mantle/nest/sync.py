"""Compare-and-swap transaction and reconciliation.

A GitHub commit cannot contain its own resulting SHA. We use a two-phase,
transaction-bound proof: before publication append a Body-authored intent/proof;
publish one atomic commit whose parent is the remembered state-branch head;
then on the next materialization (or a separate reconcile step) verify the
transaction ID and tree against GitHub's response and append the COMPLETED proof.
We never advance a remote cursor before the matching request, response, receipt,
and durable commit are verified.
"""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional

from .manifest import canonical_json, file_inventory, sha256_bytes
from .target import NestTarget
from .transport import NestConflict, NestTransport


@dataclass(frozen=True)
class CasPrepared:
    transaction_id: str
    staging_dir: str
    tree_hash: str
    expected_parent: str
    manifest_hash: str


def new_transaction_id() -> str:
    return uuid.uuid4().hex


def build_intent_proof(
    *,
    transaction_id: str,
    repo_id: int,
    expected_parent: str,
    tree_hash: str,
    operation: str,
    capability: str,
    author: str,
    reason: str,
) -> bytes:
    """Body-authored intent proof appended before publication (see section 9)."""
    obj = {
        "kind": "github-nest-intent",
        "transaction_id": transaction_id,
        "repository": {"id": int(repo_id)},
        "revision": {"expected_parent": str(expected_parent)},
        "tree": {"hash": str(tree_hash)},
        "operation": str(operation),
        "capability": str(capability),
        "author": str(author),
        "reason": str(reason),
    }
    return canonical_json(obj)


def build_completed_proof(
    *,
    transaction_id: str,
    repo_id: int,
    commit: str,
    tree_hash: str,
    status: str,
) -> bytes:
    obj = {
        "kind": "github-nest-completed",
        "transaction_id": transaction_id,
        "repository": {"id": int(repo_id)},
        "commit": str(commit),
        "tree": {"hash": str(tree_hash)},
        "status": str(status),
    }
    return canonical_json(obj)


def print_proof(proof: bytes, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(proof)


def prepare_publish(
    staging_dir: str,
    *,
    repo_id: int,
    state_branch: str,
    expected_parent: str,
    manifest_hash: str,
) -> CasPrepared:
    inventory = file_inventory(staging_dir)
    tree_obj = {"files": inventory}
    tree_hash = sha256_bytes(canonical_json({"tree": tree_obj}))
    return CasPrepared(
        transaction_id=new_transaction_id(),
        staging_dir=staging_dir,
        tree_hash=tree_hash,
        expected_parent=expected_parent,
        manifest_hash=manifest_hash,
    )


def cas_publish(
    transport: NestTransport,
    target: NestTarget,
    prepared: CasPrepared,
) -> object:
    """Advance the ref only as a non-force fast-forward on the expected parent.

    Raises :class:`NestConflict` if the branch moved (no force, no rebase, no
    silent discard). The caller is responsible for turning the conflict into an
    ``github_state_conflict`` Immune event.
    """
    return transport.publish(target, prepared.staging_dir, prepared.expected_parent)
