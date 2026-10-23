"""Grammar-specific validation for generated assimilation artifacts."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any, Dict, Tuple
from xml.etree import ElementTree


@dataclass(frozen=True)
class ArtifactValidation:
    artifact_kind: str
    valid: bool
    checks: Tuple[str, ...]
    problems: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _balanced(text: str, opening: str, closing: str) -> bool:
    depth = 0
    for char in text:
        if char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def validate_artifact(artifact_kind: str, text: str) -> ArtifactValidation:
    """Validate one generated artifact using its own surface grammar."""
    kind = str(artifact_kind).lower()
    source = str(text)
    checks = []
    problems = []
    if kind in {"qt-ui", "ui", "qrc", "qt-resource"}:
        try:
            root = ElementTree.fromstring(source)
            checks.append("well_formed_xml")
            expected = "ui" if kind in {"qt-ui", "ui"} else "rcc"
            if root.tag.lower() != expected:
                problems.append("expected <%s> root" % expected)
            else:
                checks.append("expected_root")
        except ElementTree.ParseError:
            problems.append("malformed_xml")
    elif kind in {"cmake", "build-system"}:
        if _balanced(source, "(", ")"):
            checks.append("balanced_parentheses")
        else:
            problems.append("unbalanced_parentheses")
        if re.search(r"\b(add_executable|add_library|target_sources)\s*\(", source,
                     re.IGNORECASE):
            checks.append("target_topology")
        else:
            problems.append("no_target_topology")
    elif kind in {"rust", "rust-source"}:
        if _balanced(source, "{", "}"):
            checks.append("balanced_braces")
        else:
            problems.append("unbalanced_braces")
        if re.search(r"\b(fn|mod|impl|struct|enum)\s+[A-Za-z_]", source):
            checks.append("rust_declaration")
        else:
            problems.append("no_rust_declaration")
    elif kind in {"cpp", "c++", "c", "header", "native-source"}:
        if _balanced(source, "{", "}") and _balanced(source, "(", ")"):
            checks.append("balanced_native_delimiters")
        else:
            problems.append("unbalanced_native_delimiters")
        if re.search(r"(?:\bclass\s+\w+|\b[A-Za-z_]\w*\s*\([^;{}]*\)\s*\{)", source):
            checks.append("native_declaration_or_body")
        else:
            problems.append("no_native_declaration_or_body")
    else:
        problems.append("unsupported_artifact_kind")
    return ArtifactValidation(kind, not problems, tuple(checks), tuple(problems))


__all__ = ["ArtifactValidation", "validate_artifact"]
