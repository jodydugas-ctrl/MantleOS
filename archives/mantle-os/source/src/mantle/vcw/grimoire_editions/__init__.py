"""Explicit, concurrent Grimoire edition packages."""
from .common import GrimoireEdition, GrimoireEditionError
from .registry import decode_statement, get_edition, known_editions
from .adoption import (DEFAULT_NEW_TISSUE_PROFILE, PRIOR_PROFILE,
                       adopt_v010, new_grimoire_params,
                       adopt_semantic_memory, new_semantic_genome_params,
                       SEMANTIC_MEMORY_PROFILE)

__all__ = [
    "GrimoireEdition",
    "GrimoireEditionError",
    "decode_statement",
    "get_edition",
    "known_editions",
    "DEFAULT_NEW_TISSUE_PROFILE",
    "PRIOR_PROFILE",
    "adopt_v010",
    "new_grimoire_params",
    "adopt_semantic_memory",
    "new_semantic_genome_params",
    "SEMANTIC_MEMORY_PROFILE",
]
