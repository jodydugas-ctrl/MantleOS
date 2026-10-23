from __future__ import annotations

from pathlib import Path
from typing import Any


# These locations are evidence-bearing parts of the repository, but a language appearing only here is
# not enough to conclude that the application runtime uses that substrate. The canonical scan remains
# unchanged; this classification is used only to decide whether an LLM adaptation workbench is warranted.
_NON_RUNTIME_PATH_PARTS = {
    ".github", "docs", "doc", "documentation",
    "test", "tests", "testing", "fixtures",
    "thirdparty", "third_party", "third-party", "3rdparty",
    "vendor", "vendors", "translations", "translation",
    "installer", "installers", "deploy", "deployment",
}


def is_runtime_candidate_path(path: str) -> bool:
    parts = {part.lower() for part in Path(path).parts[:-1]}
    return not bool(parts.intersection(_NON_RUNTIME_PATH_PARTS))


def files_for_assimilation_detection(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a secondary copy suitable for substrate-gap detection.

    Non-runtime support files remain present so manifest/framework hints can still be collected, but their
    language is normalized to an already-supporting documentation class. This prevents e.g. a PowerShell
    screenshot helper under `docs/` from opening a PowerShell runtime-adapter task while a real root/runtime
    PowerShell program still does.
    """
    out: list[dict[str, Any]] = []
    for row in files:
        item = dict(row)
        path = str(item.get("path") or "")
        if path and not is_runtime_candidate_path(path):
            item["assimilation_original_language"] = item.get("language")
            item["assimilation_context"] = "non_runtime_support"
            item["language"] = "Markdown"
        out.append(item)
    return out
