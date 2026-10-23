from __future__ import annotations

from bisect import bisect_right
from pathlib import Path
import re

from .base import Adapter
from ..inventory import FileRecord
from ..model import Edge, Evidence, ExtractionResult, Node, stable_id


PATTERNS = {
    "url": re.compile(r"https?://[^\s\"'<>]+"),
    "environment_reference": re.compile(r"\b(?:PATH|HOME|USERPROFILE|APPDATA|XDG_[A-Z_]+|ANDROID_[A-Z_]+)\b"),
    "extension_keyword": re.compile(r"\b(?:plugin|plugins|extension|extensions|add-?on|hook|hooks)\b", re.IGNORECASE),
}

BUILD_LANGUAGES = {"CMake", "QMake", "Make", "Dockerfile", "Gradle"}
DOCUMENT_LANGUAGES = {"Markdown"}
NON_RUNTIME_PARTS = {
    ".github", "docs", "doc", "documentation", "thirdparty", "third_party", "third-party", "3rdparty",
    "vendor", "vendors", "external", "externals", "translations", "translation",
    "test", "tests", "testing", "fixtures", "installer", "installers", "deploy", "deployment",
    "icon", "icons", "assets",
}
REFERENCE_FILE_PREFIXES = ("license", "copying", "notice", "authors", "changelog", "readme")
C_STYLE_COMMENT_LANGUAGES = {
    "C", "C/C++ Header", "C++", "C++ Header", "C#", "Go", "Java", "JavaScript",
    "Kotlin", "Objective-C", "Rust", "Swift", "TypeScript",
}


def reference_context(record: FileRecord) -> str:
    path = Path(record.path)
    parts = {part.lower() for part in path.parts}
    if path.name.lower().startswith(REFERENCE_FILE_PREFIXES):
        return "project_documentation"
    if record.language in BUILD_LANGUAGES or ".github" in parts:
        return "build_or_workflow_metadata"
    if record.language in DOCUMENT_LANGUAGES or parts.intersection({"docs", "doc", "documentation"}):
        return "documentation"
    if parts.intersection({"thirdparty", "third_party", "third-party", "3rdparty", "vendor", "vendors", "external", "externals"}):
        return "vendored_source"
    if parts.intersection({"translations", "translation"}):
        return "localization_resource"
    if parts.intersection({"test", "tests", "testing", "fixtures"}):
        return "test_fixture"
    if parts.intersection({"installer", "installers", "deploy", "deployment"}):
        return "deployment_metadata"
    if parts.intersection({"icon", "icons", "assets"}):
        return "static_asset"
    return "runtime_candidate"


def _c_style_comment_spans(text: str) -> list[tuple[int, int]]:
    """Return C-family comment spans while ignoring comment markers inside strings."""
    spans: list[tuple[int, int]] = []
    i = 0
    size = len(text)
    while i < size:
        char = text[i]
        if char in {'"', "'"}:
            quote = char
            i += 1
            while i < size:
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == quote:
                    i += 1
                    break
                i += 1
            continue
        if text.startswith("//", i):
            end = text.find("\n", i + 2)
            if end < 0:
                end = size
            spans.append((i, end))
            i = end
            continue
        if text.startswith("/*", i):
            end = text.find("*/", i + 2)
            end = size if end < 0 else end + 2
            spans.append((i, end))
            i = end
            continue
        i += 1
    return spans


def _comment_spans(record: FileRecord, text: str) -> list[tuple[int, int]]:
    if record.language in C_STYLE_COMMENT_LANGUAGES:
        return _c_style_comment_spans(text)
    return []


def _span_contains(spans: list[tuple[int, int]], starts: list[int], position: int) -> bool:
    index = bisect_right(starts, position) - 1
    return index >= 0 and position < spans[index][1]


class GenericTextAdapter(Adapter):
    name = "generic_text"
    version = "4"

    def accepts(self, record: FileRecord) -> bool:
        return not record.is_binary

    def extract(self, root: Path, record: FileRecord, text: str) -> ExtractionResult:
        out = ExtractionResult()
        file_context = reference_context(record)
        comment_spans = _comment_spans(record, text) if file_context == "runtime_candidate" else []
        comment_starts = [start for start, _ in comment_spans]
        newline_offsets = [index for index, char in enumerate(text) if char == "\n"]
        for kind, rx in PATTERNS.items():
            for m in rx.finditer(text):
                context = (
                    "source_comment"
                    if _span_contains(comment_spans, comment_starts, m.start())
                    else file_context
                )
                runtime_candidate = context == "runtime_candidate"
                line = bisect_right(newline_offsets, m.start()) + 1
                token = m.group(0)[:300]
                eid = stable_id("evidence", record.id, self.name, kind, line, token)
                out.evidence.append(Evidence(eid, record.id, record.path, line, line, "DIRECT", self.name, token))
                nid = stable_id("node", record.id, kind, line, token)
                if runtime_candidate:
                    mapped_kind = "nest_boundary" if kind in {"url", "environment_reference"} else "extension_receptor_candidate"
                    coverage = "PARTIAL"
                else:
                    mapped_kind = "repository_reference"
                    coverage = "MAPPED"
                out.nodes.append(Node(
                    nid, mapped_kind, token, record.id, record.path, coverage,
                    {
                        "generic_kind": kind,
                        "reference_context": context,
                        "runtime_boundary_candidate": runtime_candidate,
                        "meaning": (
                            "token occurs in runtime-relevant source and may represent a BODY/NEST seam"
                            if runtime_candidate
                            else "token is preserved as repository evidence but is not promoted to an application-runtime boundary"
                        ),
                    },
                    [eid],
                ))
        return out
