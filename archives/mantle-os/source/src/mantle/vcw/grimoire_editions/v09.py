"""The frozen v0.9 registry adapter.

The compatibility module remains the semantic implementation until G-02 freezes
its golden surface. This adapter makes edition selection explicit without changing
the old public import path or output.
"""
from __future__ import annotations

from typing import Any

from .. import grimoire as legacy

PROFILE = "grimoire-v0.9"
DOCUMENT_PATH = "documents/grimoire/editions/grimoire-v0.9.md"
SELFTEST_VECTORS = tuple(legacy.SELFTEST_VECTORS)
COMPOSITION_COUNT = 295
STATEMENT_COUNT = len(SELFTEST_VECTORS)


def decode_statement(raw: Any, **context: Any) -> dict[str, Any]:
    context.pop("profile", None)
    return legacy.decode_statement(raw, **context)
