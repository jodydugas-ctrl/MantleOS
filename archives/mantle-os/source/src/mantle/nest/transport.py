"""Remote NEST transport interface.

The remote transport lives OUTSIDE ``Organism``. The Body never sees the network;
it sees only the local bytes a transport materializes. This module defines the
narrow ``NestTransport`` Protocol plus the typed receipts and the conflict error.

Real transports (see :mod:`mantle.nest.github`) use a lazy stdlib ``urllib``
client and never open a socket at import time. Tests inject a deterministic
in-memory fake (see :mod:`mantle.nest.fake`) so no invariant or unit test needs
the network.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Protocol

from .target import NestTarget


class NestConflict(Exception):
    """The remote state branch moved: an expected-parent CAS refused.

    This is NOT forceable. Callers must never silently rebase or discard either
    history; they fetch the new head, replay idempotent inputs, and require
    explicit operator resolution for non-idempotent work.
    """

    def __init__(self, message: str, *, expected_parent: str = "", actual_head: str = ""):
        super().__init__(message)
        self.expected_parent = expected_parent
        self.actual_head = actual_head


@dataclass(frozen=True)
class RemoteNestStatus:
    exists: bool
    repo_id: int
    full_name: str
    visibility: str
    state_branch: str
    head_commit: str = ""
    manifest_present: bool = False
    manifest_hash: str = ""
    details: Dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class MaterializationReceipt:
    transaction_id: str
    repo_id: int
    head_commit: str
    manifest_hash: str
    destination: str
    opened_envelope: bool = False
    file_count: int = 0
    details: Dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class PublishReceipt:
    transaction_id: str
    repo_id: int
    parent_commit: str
    commit: str
    tree_hash: str
    manifest_hash: str
    details: Dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ReconcileReceipt:
    transaction_id: str
    repo_id: int
    head_commit: str
    request_verified: bool
    tree_matches: bool
    completed: bool
    details: Dict[str, object] = field(default_factory=dict)


class NestTransport(Protocol):
    """The narrow transport surface an outer runtime drives.

    Implementations must be deterministic and injectable; they never interpret
    Body content beyond carrying bytes.
    """

    def inspect(self, target: NestTarget) -> RemoteNestStatus: ...

    def materialize(
        self, target: NestTarget, destination: str
    ) -> MaterializationReceipt: ...

    def publish(
        self, target: NestTarget, source: str, expected_parent: str
    ) -> PublishReceipt: ...

    def reconcile(self, target: NestTarget, transaction_id: str) -> ReconcileReceipt: ...
