"""Edition metadata shared by the explicit Grimoire registry."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


class GrimoireEditionError(ValueError):
    """A requested Grimoire edition is unknown or not yet executable."""


@dataclass(frozen=True)
class GrimoireEdition:
    profile: str
    document_path: str
    decoder: Callable[..., dict[str, Any]]
    selftest_vectors: tuple[str, ...]
    composition_count: int
    statement_count: int
