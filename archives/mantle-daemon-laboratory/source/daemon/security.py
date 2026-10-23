from __future__ import annotations

import json
import re
from pathlib import Path

_SECRET_KEY = re.compile(r"(secret|token|password|credential|api[_-]?key)", re.IGNORECASE)


def redact(value, secret_values=()):
    """Redact credential-shaped fields before they can enter durable evidence."""
    secrets = [str(item) for item in secret_values if item]
    if isinstance(value, dict):
        return {key: ("[REDACTED]" if _SECRET_KEY.search(str(key)) else redact(item, secrets))
                for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item, secrets) for item in value]
    if isinstance(value, tuple):
        return tuple(redact(item, secrets) for item in value)
    if isinstance(value, str):
        for secret in secrets:
            value = value.replace(secret, "[REDACTED]")
    return value


def confined_path(root: Path, relative: str) -> Path:
    root = Path(root).resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise PermissionError("path escapes the permitted NEST") from exc
    return candidate


def authority(root: Path, capability: str) -> dict:
    data = json.loads((Path(root) / "genome/authority.json").read_text(encoding="utf-8"))
    return dict(data.get("capabilities", {}).get(capability,
                {"granted": False, "denied": True, "authority": "unavailable"}))


def may_write_specimen(root: Path) -> bool:
    item = authority(root, "write_specimen")
    return item.get("granted") is True and item.get("authority") == "body-authorized" and not item.get("expired", False)
