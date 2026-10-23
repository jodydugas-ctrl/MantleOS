"""Explicit Grimoire edition registry."""
from __future__ import annotations

from typing import Any

from .common import GrimoireEdition, GrimoireEditionError
from . import v09, v010

_EDITIONS = {
    v09.PROFILE: GrimoireEdition(
        profile=v09.PROFILE,
        document_path=v09.DOCUMENT_PATH,
        decoder=v09.decode_statement,
        selftest_vectors=v09.SELFTEST_VECTORS,
        composition_count=v09.COMPOSITION_COUNT,
        statement_count=v09.STATEMENT_COUNT,
    ),
    v010.PROFILE: GrimoireEdition(
        profile=v010.PROFILE,
        document_path=v010.DOCUMENT_PATH,
        decoder=v010.decode_statement,
        selftest_vectors=v010.SELFTEST_VECTORS,
        composition_count=v010.COMPOSITION_COUNT,
        statement_count=v010.STATEMENT_COUNT,
    ),
}


def get_edition(profile: str) -> GrimoireEdition:
    try:
        return _EDITIONS[profile]
    except (KeyError, TypeError):
        raise GrimoireEditionError("unknown Grimoire edition %r" % (profile,)) from None


def known_editions() -> tuple[str, ...]:
    return tuple(_EDITIONS)


def decode_statement(raw: Any, *, profile: str, **context: Any) -> dict[str, Any]:
    edition = get_edition(profile)
    return edition.decoder(raw, **context)
