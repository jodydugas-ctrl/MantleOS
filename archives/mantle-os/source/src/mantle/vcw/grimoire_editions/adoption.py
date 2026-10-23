"""Operator-authorized Grimoire edition adoption for new tissue."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict

from .registry import get_edition


DEFAULT_NEW_TISSUE_PROFILE = "grimoire-v0.10"
PRIOR_PROFILE = "grimoire-v0.9"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def adopt_v010(*, body: Any, operator_authorized: bool, commit: str,
               repository_root: str | Path = ".") -> Dict[str, Any]:
    """Record the adoption event; only an explicit operator authorization may call it."""
    if operator_authorized is not True:
        raise PermissionError("Grimoire adoption requires operator authorization")
    root = Path(repository_root)
    edition = get_edition(DEFAULT_NEW_TISSUE_PROFILE)
    source = root / edition.document_path
    runtime = root / "src" / "mantle" / "vcw" / "grimoire_editions" / "v010.py"
    verifier = root / "tools" / "grimoire_tool.py"
    receipt = {
        "kind": "grimoire_edition_adoption",
        "edition": DEFAULT_NEW_TISSUE_PROFILE,
        "source_sha256": _sha256(source),
        "runtime_sha256": _sha256(runtime),
        "independent_verifier_sha256": _sha256(verifier),
        "operator_authorized": True,
        "default_scope": "new-tissue-only",
        "prior_default": PRIOR_PROFILE,
        "legacy_reinterpretation": False,
        "commit": str(commit),
    }
    return body.record_edition_adoption(receipt)


def new_grimoire_params(profile: str = DEFAULT_NEW_TISSUE_PROFILE) -> Dict[str, str]:
    """Return explicit carrier params for a newly created Grimoire band."""
    get_edition(profile)
    return {"profile": profile}


# ---------------------------------------------------------------------------
# Semantic-memory adoption: the one-step entry -> Grimoire statement profile
# ---------------------------------------------------------------------------
SEMANTIC_MEMORY_PROFILE = "grimoire-v0.10-entry"
SEMANTIC_MEMORY_BASE_EDITION = DEFAULT_NEW_TISSUE_PROFILE


def new_semantic_genome_params() -> Dict[str, str]:
    """Driver params for a semantic-memory band (the one-step entry encoder)."""
    get_edition(SEMANTIC_MEMORY_BASE_EDITION)
    return {"profile": SEMANTIC_MEMORY_PROFILE}


def adopt_semantic_memory(*, body: Any, operator_authorized: bool, commit: str,
                          repository_root: str | Path = ".") -> Dict[str, Any]:
    """Record the semantic-memory adoption event; only an explicit operator
    authorization may call it. Scope is new-tissue-only: existing organisms and
    carriers are untouched."""
    if operator_authorized is not True:
        raise PermissionError("semantic-memory adoption requires operator authorization")
    root = Path(repository_root)
    # Runtime files resolve from the implementing modules themselves so the receipt
    # works identically from a source checkout (<root>/src/mantle) and from a
    # vendored runtime (<root>/runtime/mantle). Never assume a layout.
    from . import semantic as _semantic_module
    encoder = Path(_semantic_module.__file__).resolve()
    vcw_dir = encoder.parents[1]
    mantle_dir = encoder.parents[2]
    driver = vcw_dir / "drivers.py"
    cube = vcw_dir / "cube.py"
    invariants = mantle_dir / "audits" / "invariants.py"
    companion = root / "documents" / "grimoire" / "semantic-memory" / "semantic-memory-v1.md"
    receipt = {
        "kind": "semantic_memory_adoption",
        "profile": SEMANTIC_MEMORY_PROFILE,
        "base_edition": SEMANTIC_MEMORY_BASE_EDITION,
        "encoder_sha256": _sha256(encoder),
        "driver_sha256": _sha256(driver),
        "cube_sha256": _sha256(cube),
        "invariants_sha256": _sha256(invariants),
        "companion_sha256": _sha256(companion) if companion.is_file() else None,
        "companion_present": companion.is_file(),
        "operator_authorized": True,
        "default_scope": "new-tissue-only",
        "legacy_reinterpretation": False,
        "commit": str(commit),
    }
    return body.record_edition_adoption(receipt)
