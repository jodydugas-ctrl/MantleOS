"""Deterministic, read-only access to immutable ancestral evidence."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class AncestorEvidence:
    generation: int
    band: str
    entry_id: Any
    evidence_status: str
    sha256: str
    content: Any

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def query_ancestor(org: Any, generation: int, *, band: str = "facts",
                   entry_id: Optional[Any] = None, limit: int = 20) -> Tuple[AncestorEvidence, ...]:
    """Return bounded archive evidence without granting the ancestor authority."""
    if limit <= 0 or limit > 100:
        raise ValueError("ancestor query limit must be between 1 and 100")
    cube = org.cube_for_generation(int(generation))
    if cube is None or cube is org.prime:
        raise KeyError("requested generation is not an ancestral archive")
    rows = []
    for entry in cube.read(band):
        if entry_id is not None and entry.get("id") != entry_id:
            continue
        canonical = json.dumps(entry, sort_keys=True, separators=(",", ":"),
                               ensure_ascii=True, default=str).encode("utf-8")
        rows.append(AncestorEvidence(
            int(generation), band, entry.get("id"),
            "verified" if entry.get("verified") else "observed",
            hashlib.sha256(canonical).hexdigest(), entry.get("content"),
        ))
        if len(rows) >= limit:
            break
    return tuple(rows)


__all__ = ["AncestorEvidence", "query_ancestor"]
