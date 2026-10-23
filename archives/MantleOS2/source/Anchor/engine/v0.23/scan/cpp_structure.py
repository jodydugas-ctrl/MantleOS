from __future__ import annotations

from dataclasses import dataclass
import bisect
import re

# Conservative recognizer used only after masking comments/string bodies.
# It is a fallback structural layer, not a replacement for a compiler AST.
FUNC_HEADER_RE = re.compile(
    r"^[\t ]*(?:(?:template\s*<[^\n;{}]+>\s*)?"
    r"(?:[\w:<>,~*&\[\] \t]+?[ \t]+))"
    r"(?P<name>[A-Za-z_~]\w*(?:::[A-Za-z_~]\w*)*)\s*"
    r"\([^;{}]*\)\s*(?:const\s*)?(?:noexcept(?:\s*\([^)]*\))?\s*)?(?:override\s*)?\{",
    re.MULTILINE,
)

CTOR_HEADER_RE = re.compile(
    r"^[\t ]*(?P<name>(?:[A-Za-z_]\w*::)+(?:~?[A-Za-z_]\w*))\s*"
    r"\([^;{}]*\)\s*(?::[^\n{]*)?\{",
    re.MULTILINE,
)

CONTROL_NAMES = {
    "if", "for", "while", "switch", "catch", "sizeof", "alignof", "decltype",
    "return", "new", "delete", "throw", "static_cast", "dynamic_cast",
    "reinterpret_cast", "const_cast", "typeid", "requires", "co_await",
}

CALL_RE = re.compile(
    r"(?<![\w])(?:(?P<scope>[A-Za-z_]\w*(?:::[A-Za-z_]\w*)*)::|"
    r"(?P<receiver>(?:this|[A-Za-z_]\w*)\s*(?:->|\.))\s*)?"
    r"(?P<name>[A-Za-z_]\w*)\s*\("
)


CLASS_HEADER_RE = re.compile(
    r"\b(?P<kind>class|struct)\s+(?:(?:[A-Za-z_]\w*)_API\s+)?(?P<name>[A-Za-z_]\w*)"
    r"(?:\s*:[^{;]+)?\s*\{",
    re.MULTILINE,
)

MEMBER_DECL_RE = re.compile(
    r"^[\t ]*(?P<type>(?:const\s+)?[A-Za-z_]\w*(?:::[A-Za-z_]\w*)*"
    r"(?:\s*<[^;(){}\n]+>)?(?:\s+const)?)\s*(?P<pointer>[*&]+)?\s*"
    r"(?P<name>[A-Za-z_]\w*)\s*(?:=[^;\n]*|\{[^;\n]*\})?\s*;",
    re.MULTILINE,
)

LOCAL_DECL_RE = re.compile(
    r"\b(?P<type>(?:const\s+)?[A-Za-z_]\w*(?:::[A-Za-z_]\w*)*"
    r"(?:\s*<[^;(){}\n]+>)?(?:\s+const)?)\s*(?P<pointer>[*&]+)?\s*"
    r"(?P<name>[A-Za-z_]\w*)\s*(?=[,)=;{])"
)

THIS_ASSIGN_RE = re.compile(
    r"\bthis\s*->\s*(?P<member>[A-Za-z_]\w*)\s*(?P<op>\+=|-=|\*=|/=|%=|=)\s*(?!=)"
)


@dataclass(frozen=True)
class FunctionRegion:
    name: str
    start: int
    body_start: int
    end: int
    start_line: int
    end_line: int

    @property
    def class_scope(self) -> str | None:
        if "::" not in self.name:
            return None
        return self.name.rsplit("::", 1)[0]


@dataclass(frozen=True)
class ClassRegion:
    name: str
    start: int
    body_start: int
    end: int
    start_line: int
    end_line: int
    kind: str


def mask_cpp(text: str) -> str:
    """Mask comments and literal contents while preserving byte offsets and newlines.

    The result is deliberately same-length as the input so match offsets map back to source.
    Handles //, /* */, quoted strings/chars, and common C++ raw string literals.
    """
    out = list(text)
    n = len(text)
    i = 0

    def blank(a: int, b: int):
        for j in range(a, min(b, n)):
            if out[j] != "\n":
                out[j] = " "

    while i < n:
        if text.startswith("//", i):
            j = text.find("\n", i + 2)
            if j < 0:
                j = n
            blank(i, j)
            i = j
            continue
        if text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            blank(i, j)
            i = j
            continue

        # C++ raw string: optional prefix then R"delim(... )delim"
        raw_prefix_len = 0
        for prefix in ("u8R\"", "uR\"", "UR\"", "LR\"", "R\""):
            if text.startswith(prefix, i):
                raw_prefix_len = len(prefix)
                break
        if raw_prefix_len:
            delim_start = i + raw_prefix_len
            paren = text.find("(", delim_start)
            if paren >= 0 and paren - delim_start <= 16:
                delim = text[delim_start:paren]
                terminator = ")" + delim + '"'
                j = text.find(terminator, paren + 1)
                j = n if j < 0 else j + len(terminator)
                blank(i, j)
                i = j
                continue

        # prefixed and ordinary string/char literals
        prefix = None
        quote_pos = None
        for p in ("u8\"", "u\"", "U\"", "L\"", '"', "u'", "U'", "L'", "'"):
            if text.startswith(p, i):
                prefix = p
                quote_pos = i + len(p) - 1
                break
        if prefix is not None and quote_pos is not None:
            quote = text[quote_pos]
            j = quote_pos + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == quote:
                    j += 1
                    break
                j += 1
            blank(i, j)
            i = j
            continue

        i += 1
    return "".join(out)


def _line_starts(text: str) -> list[int]:
    starts = [0]
    for m in re.finditer("\n", text):
        starts.append(m.end())
    return starts


def line_for_offset(starts: list[int], pos: int) -> int:
    return bisect.bisect_right(starts, pos)


def _match_brace(masked: str, open_pos: int) -> int | None:
    depth = 0
    for i in range(open_pos, len(masked)):
        c = masked[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
    return None


def find_function_regions(text: str, *, masked_text: str | None = None,
                          line_starts: list[int] | None = None) -> list[FunctionRegion]:
    masked = masked_text if masked_text is not None else mask_cpp(text)
    starts = line_starts if line_starts is not None else _line_starts(text)
    candidates = list(FUNC_HEADER_RE.finditer(masked)) + list(CTOR_HEADER_RE.finditer(masked))
    candidates.sort(key=lambda m: (m.start(), -(m.end() - m.start())))
    regions: list[FunctionRegion] = []
    occupied_until = -1
    for m in candidates:
        if m.start() < occupied_until:
            continue
        open_pos = masked.find("{", m.start(), m.end())
        if open_pos < 0:
            continue
        end = _match_brace(masked, open_pos)
        if end is None:
            continue
        name = m.group("name")
        # Defensive exclusion for accidental control constructs.
        if name.rsplit("::", 1)[-1] in CONTROL_NAMES:
            continue
        regions.append(FunctionRegion(
            name=name,
            start=m.start(),
            body_start=open_pos + 1,
            end=end,
            start_line=line_for_offset(starts, m.start()),
            end_line=line_for_offset(starts, end - 1),
        ))
        occupied_until = end
    return regions


def find_class_regions(text: str, *, masked_text: str | None = None,
                       line_starts: list[int] | None = None) -> list[ClassRegion]:
    masked = masked_text if masked_text is not None else mask_cpp(text)
    starts = line_starts if line_starts is not None else _line_starts(text)
    regions: list[ClassRegion] = []
    for m in CLASS_HEADER_RE.finditer(masked):
        open_pos = masked.find("{", m.start(), m.end())
        if open_pos < 0:
            continue
        end = _match_brace(masked, open_pos)
        if end is None:
            continue
        regions.append(ClassRegion(
            name=m.group("name"),
            start=m.start(),
            body_start=open_pos + 1,
            end=end,
            start_line=line_for_offset(starts, m.start()),
            end_line=line_for_offset(starts, end - 1),
            kind=m.group("kind"),
        ))
    return regions


def iter_member_declarations(text: str, region: ClassRegion, *, masked_text: str | None = None,
                             line_starts: list[int] | None = None):
    masked = masked_text if masked_text is not None else mask_cpp(text)
    starts = line_starts if line_starts is not None else _line_starts(text)
    body = masked[region.body_start:region.end - 1]
    for m in MEMBER_DECL_RE.finditer(body):
        raw_type = m.group("type").strip()
        name = m.group("name")
        # Exclude common access/using/static-assert style false positives and anything that looks callable.
        if raw_type in {"public", "private", "protected", "using", "typedef", "return"}:
            continue
        abs_start = region.body_start + m.start()
        pointer = (m.group("pointer") or "").strip()
        yield {
            "start": abs_start,
            "end": region.body_start + m.end(),
            "line": line_for_offset(starts, abs_start),
            "owner_class": region.name,
            "member": name,
            "declared_type": raw_type,
            "pointer": pointer or None,
            "static_type": raw_type + (" " + pointer if pointer else ""),
        }


def containing_region(regions: list[FunctionRegion], pos: int) -> FunctionRegion | None:
    # Region list is source ordered and non-overlapping.
    for region in regions:
        if region.body_start <= pos < region.end:
            return region
        if region.start > pos:
            break
    return None


def iter_calls(text: str, region: FunctionRegion, *, masked_text: str | None = None):
    masked = masked_text if masked_text is not None else mask_cpp(text)
    body = masked[region.body_start:region.end - 1]
    for m in CALL_RE.finditer(body):
        name = m.group("name")
        if name in CONTROL_NAMES:
            continue
        abs_start = region.body_start + m.start()
        abs_end = region.body_start + m.end()
        yield {
            "start": abs_start,
            "end": abs_end,
            "name": name,
            "scope": m.group("scope"),
            "receiver": (m.group("receiver") or "").strip() or None,
        }


def iter_local_declarations(text: str, region: FunctionRegion, *, masked_text: str | None = None,
                            line_starts: list[int] | None = None):
    """Yield direct parameter/local type bindings inside one function region.

    This intentionally recognizes only simple named declarations. It does not infer ``auto``,
    aliases, casts, assignments, or template deduction; ambiguous bindings remain unresolved.
    """
    masked = masked_text if masked_text is not None else mask_cpp(text)
    starts = line_starts if line_starts is not None else _line_starts(text)
    segment = masked[region.start:region.end]
    excluded_types = {
        "auto", "bool", "char", "double", "float", "int", "long", "short", "signed",
        "unsigned", "void", "return", "class", "struct", "typename",
    }
    for match in LOCAL_DECL_RE.finditer(segment):
        raw_type = match.group("type").strip()
        if raw_type in excluded_types:
            continue
        absolute = region.start + match.start()
        pointer = (match.group("pointer") or "").strip()
        yield {
            "start": absolute,
            "end": region.start + match.end(),
            "line": line_for_offset(starts, absolute),
            "name": match.group("name"),
            "declared_type": raw_type,
            "pointer": pointer or None,
            "static_type": raw_type + (" " + pointer if pointer else ""),
        }


def iter_this_assignments(text: str, region: FunctionRegion, *, masked_text: str | None = None):
    masked = masked_text if masked_text is not None else mask_cpp(text)
    body = masked[region.body_start:region.end - 1]
    for m in THIS_ASSIGN_RE.finditer(body):
        yield {
            "start": region.body_start + m.start(),
            "end": region.body_start + m.end(),
            "member": m.group("member"),
            "operator": m.group("op"),
        }
