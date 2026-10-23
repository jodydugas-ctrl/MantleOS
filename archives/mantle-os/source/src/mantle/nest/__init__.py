"""
mantle.nest -- optional remote NEST residency (GitHub as a transport, never SELF).

This package is an OUTER adapter layer. It is never imported by the certified
Phase-1 core (``mantle.core``, ``mantle.organs``, ``mantle.vcw``). The Body only
ever operates on local bytes: a remote NEST is materialized into a private,
owner-local temporary directory before ``Organism.load`` runs, and a remote form
is sealed and published only after the Body has checkpointed locally.

The design rule, in one sentence:

  Materialize GitHub into a verified local NEST, let the deterministic Body live
  there, then publish a secret-free, SELF-sealed checkpoint through Limbs using
  exact-revision compare-and-swap -- never let GitHub become SELF, the Heart, or
  Phase-1 authority.

GitHub supplies storage, events, ephemeral workers, checks, and governance. It is
OTHER evidence until verified and adopted through Mantle's existing boundaries.
"""

from .target import NestTarget, parse_location  # noqa: F401
from .transport import (  # noqa: F401
    NestTransport,
    RemoteNestStatus,
    MaterializationReceipt,
    PublishReceipt,
    ReconcileReceipt,
    NestConflict,
)

__all__ = [
    "NestTarget",
    "parse_location",
    "NestTransport",
    "RemoteNestStatus",
    "MaterializationReceipt",
    "PublishReceipt",
    "ReconcileReceipt",
    "NestConflict",
]
