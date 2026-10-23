"""Bounded, content-free serialization for diagnostic evidence."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

SECRET_KEY = re.compile(
    r"(?:password|passwd|secret|token|api[_-]?key|authorization|credential|cookie)",
    re.IGNORECASE,
)
CONTENT_KEY = re.compile(
    r"(?:file[_-]?content|snippet|raw[_-]?content|document[_-]?text)", re.IGNORECASE
)
SECRET_TEXT = (
    re.compile(r"(?i)bearer\s+[a-z0-9._~+/-]{8,}"),
    re.compile(r"(?i)\bsk-[a-z0-9_-]{8,}"),
    re.compile(r"(?i)(?:password|token|secret|api[_-]?key)\s*[:=]\s*\S+"),
    re.compile(r"(?i)([a-z][a-z0-9+.-]*://[^\s:/]+:)[^@\s]+@"),
)


def redact_text(value: str, *, limit: int = 512) -> str:
    result = value
    for pattern in SECRET_TEXT:
        if "@" in pattern.pattern:
            result = pattern.sub(r"\1<redacted>@", result)
        else:
            result = pattern.sub("<redacted>", result)
    if len(result) > limit:
        result = result[:limit] + "...<truncated>"
    return result


def display_path(value: str | Path, root: str | Path | None) -> str:
    path = Path(value).expanduser()
    try:
        resolved = path.resolve(strict=False)
    except OSError:
        return "<unresolved-path>"
    if root is None:
        return resolved.name or "."
    approved = Path(root).expanduser().resolve(strict=False)
    try:
        return resolved.relative_to(approved).as_posix() or "."
    except ValueError:
        return f"<outside-root>/{resolved.name}"


def sanitize(
    value: Any,
    *,
    root: str | Path | None = None,
    depth: int = 0,
    max_depth: int = 5,
    max_items: int = 40,
) -> Any:
    """Return JSON-compatible, redacted, size-bounded evidence.

    File contents are never opened. Paths become workspace-relative when possible.
    """

    if depth >= max_depth:
        return "<depth-limit>"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, Path):
        return display_path(value, root)
    if isinstance(value, str):
        if root is not None:
            try:
                if Path(value).is_absolute():
                    return display_path(value, root)
            except OSError:
                pass
        return redact_text(value)
    if isinstance(value, bytes):
        return f"<bytes:{len(value)}>"
    if isinstance(value, Mapping):
        result = {}
        for index, (key, item) in enumerate(
            sorted(value.items(), key=lambda pair: str(pair[0]))
        ):
            if index >= max_items:
                result["<truncated>"] = len(value) - max_items
                break
            name = str(key)
            result[name] = (
                "<redacted>"
                if SECRET_KEY.search(name)
                else "<redacted:file-content>"
                if CONTENT_KEY.search(name)
                else sanitize(
                    item,
                    root=root,
                    depth=depth + 1,
                    max_depth=max_depth,
                    max_items=max_items,
                )
            )
        return result
    if isinstance(value, (list, tuple, set, frozenset)):
        items = (
            sorted(value, key=str)
            if isinstance(value, (set, frozenset))
            else list(value)
        )
        return [
            sanitize(
                item,
                root=root,
                depth=depth + 1,
                max_depth=max_depth,
                max_items=max_items,
            )
            for item in items[:max_items]
        ] + (
            [f"<truncated:{len(items) - max_items}>"] if len(items) > max_items else []
        )
    return redact_text(str(value))
