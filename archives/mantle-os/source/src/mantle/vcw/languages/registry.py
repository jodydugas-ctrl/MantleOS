#!/usr/bin/env python3
"""mantle.vcw.languages.registry

The generic Book registry (Forge v0.2 §5).

Only explicit boot declarations may select a Book. A Book is an exact
(book_id, book_edition, dialect_id, dialect_edition) key resolving to a
validated manifest + codec + registries.

Registration refuses when:
  * schema is wrong
  * registry digest does not match the declared registries
  * codec digest does not match the pinned implementation
  * a FROZEN Book has missing digest fields
  * a duplicate key is registered with different bytes
  * a Book claims FROZEN but its selftests fail
  * a Book uses an unknown framing or integrity member
  * a CANDIDATE is requested as governing tissue

No filename, layer number, or band name ever selects a Book.
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .canonical import canonical_json_bytes, is_valid_digest, registry_digest
from .codec import BookCodec
from .errors import EncodingRefused
from .manifest import manifest_from_dict, validate_frozen_completeness
from .types import (
    LIFECYCLE_STATES,
    BookKey,
    BookManifest,
    key_tuple,
)

BookKeyTuple = Tuple[str, str, str, str]


def make_key(*, book_id: str, book_edition: str,
             dialect_id: str, dialect_edition: str) -> BookKey:
    return BookKey(book_id=book_id, book_edition=book_edition,
                   dialect_id=dialect_id, dialect_edition=dialect_edition)


@dataclass
class RegisteredBook:
    """A fully validated Book in the registry.

    manifest:   the immutable BookManifest (identity + contract)
    codec:      the executable codec (BookCodec protocol)
    registries: the Book's lane registries as an ordinary object
    codec_source: pinned bytes the codec digest was computed over
    """
    manifest: BookManifest
    codec: BookCodec
    registries: Any = None
    codec_source: bytes = b""


class BookRegistry:
    """Process-local registry of forged Books.

    Deterministic and stdlib-only. Call register_book() at import time from
    the Book packages so the registry is populated before any driver boots.
    """

    def __init__(self) -> None:
        self._books: Dict[BookKeyTuple, RegisteredBook] = {}
        self._by_id: Dict[str, List[BookKeyTuple]] = {}

    # -- registration ------------------------------------------------------ #

    def register_book(self, book: RegisteredBook) -> None:
        key = key_tuple(book.manifest.key)
        if key in self._books:
            existing = self._books[key]
            same = (existing.manifest == book.manifest
                    and existing.codec_source == book.codec_source)
            if same:
                return  # idempotent re-registration
            raise EncodingRefused(
                "duplicate-forbidden-role",
                "duplicate Book key %s registered with different bytes"
                % (book.manifest.key,))

        manifest = book.manifest
        validate_frozen_completeness(manifest)

        # registry digest must match declared registries (when provided)
        if book.registries is not None and manifest.registry_digest:
            actual = registry_digest(book.registries)
            if actual != manifest.registry_digest:
                raise EncodingRefused(
                    "registry-missing",
                    "registry digest mismatch for %s: declared %s, actual %s"
                    % (manifest.key, manifest.registry_digest, actual))

        # codec digest must match pinned implementation (when provided)
        if book.codec_source and manifest.codec_digest:
            from .canonical import codec_digest as _codec_digest
            actual = _codec_digest(book.codec_source)
            if actual != manifest.codec_digest:
                raise EncodingRefused(
                    "unknown-value",
                    "codec digest mismatch for %s: declared %s, actual %s"
                    % (manifest.key, manifest.codec_digest, actual))

        # a FROZEN Book must pass its own selftests
        if manifest.status == "FROZEN":
            try:
                self._run_selftest(book.codec, manifest.key)
            except Exception as exc:
                raise EncodingRefused(
                    "round-trip-mismatch",
                    "FROZEN Book %s fails selftest: %s" % (manifest.key, exc))

        self._books[key] = book
        self._by_id.setdefault(manifest.key.book_id, []).append(key)

    def _run_selftest(self, codec: BookCodec, key: BookKey) -> dict:
        if not hasattr(codec, "selftest"):
            raise EncodingRefused("registry-missing",
                                  "Book %s has no selftest" % key)
        report = codec.selftest()
        if not isinstance(report, dict):
            raise EncodingRefused("registry-missing",
                                  "Book %s selftest must return a dict" % key)
        return report

    # -- lookup ------------------------------------------------------------- #

    def get_book(self, book_id: str, book_edition: str,
                 dialect_id: str, dialect_edition: str) -> RegisteredBook:
        key = (book_id, book_edition, dialect_id, dialect_edition)
        book = self._books.get(key)
        if book is None:
            raise EncodingRefused(
                "book-missing",
                "no Book %s@%s/%s@%s registered"
                % (book_id, book_edition, dialect_id, dialect_edition))
        return book

    def get_by_bookkey(self, key: BookKey) -> RegisteredBook:
        return self.get_book(key.book_id, key.book_edition,
                             key.dialect_id, key.dialect_edition)

    def known_books(self) -> List[str]:
        out = []
        for key_tuple_val in sorted(self._books):
            bid, bed, did, ded = key_tuple_val
            out.append("%s@%s/%s@%s" % (bid, bed, did, ded))
        return out

    def has(self, book_id: str, book_edition: str,
            dialect_id: str, dialect_edition: str) -> bool:
        key = (book_id, book_edition, dialect_id, dialect_edition)
        return key in self._books

    def verify_registered_book(self, book_id: str, book_edition: str,
                               dialect_id: str, dialect_edition: str) -> dict:
        """Re-verify an already-registered Book: digests + selftest."""
        book = self.get_book(book_id, book_edition, dialect_id, dialect_edition)
        validate_frozen_completeness(book.manifest)
        if book.manifest.status == "FROZEN":
            report = self._run_selftest(book.codec, book.manifest.key)
            return {"key": str(book.manifest.key), "status": "FROZEN",
                    "selftest": "ok", "details": report}
        return {"key": str(book.manifest.key), "status": book.manifest.status,
                "selftest": "not-required"}

    # -- governing-gate ----------------------------------------------------- #

    def require_governing_capable(self, book_id: str, book_edition: str,
                                  dialect_id: str, dialect_edition: str) -> None:
        """A CANDIDATE Book must never be requested as governing tissue."""
        book = self.get_book(book_id, book_edition, dialect_id, dialect_edition)
        if book.manifest.status != "FROZEN":
            raise EncodingRefused(
                "book-missing",
                "Book %s is %s; only FROZEN may govern new tissue"
                % (book.manifest.key, book.manifest.status))

    def adopt(self, key: BookKey, *, scope: str = "new-tissue-only",
              operator_authorized: bool = True) -> dict:
        """Body/operator adoption receipt (Forge v0.2 §3 axis b).

        Reflects the registry view only; the Body owns the durable receipt.
        """
        book = self.get_book(key.book_id, key.book_edition,
                             key.dialect_id, key.dialect_edition)
        if book.manifest.status != "FROZEN":
            raise EncodingRefused(
                "book-missing",
                "cannot adopt %s in state %s" % (key, book.manifest.status))
        return {
            "kind": "vcw_book_adoption",
            "book": key_tuple(key),
            "status": "FROZEN",
            "registry_sha256": book.manifest.registry_digest,
            "codec_sha256": book.manifest.codec_digest,
            "operator_authorized": bool(operator_authorized),
            "default_scope": scope,
            "legacy_reinterpretation": False,
        }


# --------------------------------------------------------------------------- #
# Module-level singleton (the Body-approved registry).                         #
# --------------------------------------------------------------------------- #

REGISTRY = BookRegistry()


def register_book(book: RegisteredBook) -> None:
    REGISTRY.register_book(book)


def get_book(book_id: str, book_edition: str,
             dialect_id: str, dialect_edition: str) -> RegisteredBook:
    return REGISTRY.get_book(book_id, book_edition,
                             dialect_id, dialect_edition)


def known_books() -> List[str]:
    return REGISTRY.known_books()


def verify_registered_book(book_id: str, book_edition: str,
                           dialect_id: str, dialect_edition: str) -> dict:
    return REGISTRY.verify_registered_book(book_id, book_edition,
                                           dialect_id, dialect_edition)
