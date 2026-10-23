#!/usr/bin/env python3
"""
mantle.vcw.grimoire_editions.semantic  --  one-step semantic memory encoding (Mantle OS)

The "one step" contract: a MIND reflection (or any Body record) is APPENDED as one
entry-shaped record, and the append itself encodes the record into a Grimoire v0.10
pixel run. Thought and storage are one operation; the driver does the encoding, the
organism's API never changes.

Two-layer encoding per statement (the "semantic memory" profile, NOT an edition):

  STRUCTURAL SEMANTICS -- the record kind, author, timestamp, evidence, and force are
  spelled as atom-groups with roles from the existing v0.10 registries (channel R/G/B/A).
  Evidence and force come from the DEFAULT TABLES below; they are never invented.
  Record-kind atoms are canonical rows from the edition's section-6 composition table
  (verified against the source document on a repository checkout); an opcode with no
  canonical row is carried as an undifferentiated record (HEAD atom 一) with the opcode
  token preserved in the record fields -- no atom address is ever invented.

  CONTENT -- arbitrary content rides as a v0.10 QUOTE frame (`encode_quoted_bytes`:
  HEAD=DIRECT/QUOTE + BLEND nibble continuation + PARITY), preserving verbatim fidelity.

The v0.10 decoder enforces exactly one HEAD per statement, so the semantic structure and
the content QUOTE frame are two framed runs inside ONE record. Both runs are retained as
hex text (never bytes), both are covered by the record's entry hash, and both must
survive save/reload. This is a design decision, recorded in the semantic-memory
companion document (DD-Q).

Evidence/force/record-kind mapping tables are the DEFAULT tables documented in
`documents/grimoire/semantic-memory/semantic-memory-v1.md`; every row is executable here
and covered by the GRIMOIRE-ENC-* invariant family.
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, List, Optional, Tuple

from .common import GrimoireEditionError
from . import v010
from ..entry import entry_hash, content_hash
from ... import paths  # mantle.paths -- stdlib-only, no import cycle

PROFILE = "grimoire-v0.10-entry"
BASE_PROFILE = v010.PROFILE
DOCUMENT_PATH = v010.DOCUMENT_PATH  # the frozen edition this profile rides on

# ---------------------------------------------------------------------------
# 1. Author atoms -- the only authors the MIND surface can write
# ---------------------------------------------------------------------------
# 心 k61 (mind) for the MIND, 身 k158 (body) for the BODY. Single canonical atoms
# from the edition's section-5 table; no composition row needed. Any other author
# carries no AGENT atom group (the author string stays in the record fields).
AUTHOR_ATOMS: Dict[str, int] = {"MIND": 0x61, "BODY": 0x9E}

# ---------------------------------------------------------------------------
# 2. Record-kind compositions -- canonical section-6 rows, mirrored here
# ---------------------------------------------------------------------------
# name -> (spelling atom addresses, gloss). Each row names the exact composition
# row in the frozen edition. At import time the mirror is verified against the
# edition document (section 6) whenever the document is present (repository
# checkout); on an installed package the mirror is the fallback and the
# GRIMOIRE-ENC-* family reports the source check as skipped.
COMPOSITION_ROWS: Dict[str, Tuple[Tuple[int, ...], str]] = {
    "reasoning":       ((0x3D, 0x90), "mind + walk"),        # 心行
    "sense":           ((0x80,),     "ear"),                 # 耳
    "guarded_action":  ((0xA9, 0x90), "gate + walk"),        # 門行
    "proof":           ((0x70,),     "stone"),               # 石
    "immune":          ((0xA9, 0x8F), "gate + blood"),       # 門血
    "signal":          ((0xB4,),     "sound"),               # 音
    "redescription":   ((0x95, 0xF4), "speech + further"),   # 言更
    "entry":           ((0xA9, 0x0B), "gate + enter"),       # 門入
    "weaken":          ((0x13, 0x4C), "power + lack"),       # 力欠
    "receipt":         ((0x43,),     "script"),              # 文
    "discovery":       ((0x93, 0x64), "see + life"),         # 見生
    "proposal":        ((0x95, 0xF3), "speech + soon"),      # 言將
    "intent":          ((0x3D, 0xDF), "mind + toward"),      # 心向
    "handoff":         ((0x40, 0xDF), "hand + toward"),      # 手向
    "law":             ((0x71,),     "altar"),               # 示
    "history":         ((0xF9, 0x43), "before + script"),    # 前文
}

# opcode (exact or prefix) -> canonical composition name
RECORD_KIND_BY_OPCODE: Dict[str, str] = {
    "THINK": "reasoning",
    "CONSOLIDATE": "redescription",
    "PROPOSE": "proposal",
    "SPECIAL": "proposal",
    "DISPATCH": "guarded_action",
    "INTENTION": "intent",
    "DELEGATED": "handoff",
    "PROOF": "proof",
    "IMMUNE": "immune",
    "WARN": "signal",
    "SENSE": "sense",
    "RULE": "law",
    "POLICY": "law",
    "DEWEIGHT": "weaken",
    "WRITE": "entry",
    "DISCOVERY": "discovery",
    "RECALL": "history",
}
MODEL_PREFIX_COMPOSITION = "receipt"          # MODEL.* body traces -> 文 script
UNDIFFERENTIATED_ATOM = 0x01                  # 一 one -- an undifferentiated record

# ---------------------------------------------------------------------------
# 3. Evidence (channel B) -- DEFAULT TABLE (section 4.2 of the plan)
# ---------------------------------------------------------------------------
# Resolution order is a documented decision procedure; the table is the canonical
# statement of it. DIRECT is never invented: it is reserved for sensor-verified
# direct observation with a source.
_SOURCE_KIND_MEASURED = ("measured", "sensor", "direct")
_SOURCE_KIND_CITED = ("cited", "external", "reference", "quoted")
_SOURCE_KIND_CONVERSATION = ("conversation", "chat", "dialogue", "reported", "report")
_SOURCE_KIND_POLICY = ("policy", "genome", "stipulated", "rule", "operator")


def _source_kind(entry: Dict[str, Any]) -> str:
    """The recognizable kind of an entry's `source` string ("" when unrecognized)."""
    src = str(entry.get("source") or "").lower()
    for kind, keywords in (
        ("measured", _SOURCE_KIND_MEASURED),
        ("cited", _SOURCE_KIND_CITED),
        ("conversation", _SOURCE_KIND_CONVERSATION),
        ("policy", _SOURCE_KIND_POLICY),
    ):
        if any(keyword in src for keyword in keywords):
            return kind
    return ""


def _to_name(value: Any, table: Dict[int, str], label: str) -> str:
    """Accept a channel value as its name string or its numeric address."""
    if isinstance(value, str):
        reverse = {name: number for number, name in table.items()}
        if value in reverse:
            return value
        return "UNKNOWN"
    if isinstance(value, int) and value in table:
        return table[value]
    raise GrimoireEditionError("unknown %s marker %r" % (label, value))


def resolve_evidence(entry: Dict[str, Any]) -> str:
    """The DEFAULT evidence mapping for one entry (never DIRECT by invention).

    Decision procedure (the canonical statement is the table in the semantic-memory
    companion, section 4.2):
      1. explicit `evidence` marker  -> validated; DIRECT only when verified +
         measured source, else UNKNOWN;
      2. verified True               -> MEASURED / CITED by source kind, else UNKNOWN;
      3. unverified CONSOLIDATE/RECALL -> REMEMBERED (retrospective interpretation);
      4. unverified MIND reflection/discovery (THINK / DISCOVERY) -> INFERRED;
      5. ingested conversation without verification -> REPORTED;
      6. explicitly marked assumption -> ASSUMED;
      7. policy/genome stipulation -> STIPULATED;
      8. nothing identifiable -> UNKNOWN; otherwise the honest default INFERRED.
    """
    marker = entry.get("evidence")
    if marker is not None:
        name = _to_name(marker, v010.EVIDENCE, "evidence")
        if name == "DIRECT":
            if entry.get("verified") is True and _source_kind(entry) == "measured":
                return "DIRECT"
            return "UNKNOWN"                       # DIRECT is never invented
        return name
    if entry.get("verified") is True:
        kind = _source_kind(entry)
        if kind == "measured":
            return "MEASURED"
        if kind == "cited":
            return "CITED"
        return "UNKNOWN"                           # verified-but-unattributable
    op = str(entry.get("opcode") or "")
    if op in ("RECALL", "CONSOLIDATE") or op.startswith("CONSOLIDATION"):
        return "REMEMBERED"
    if op in ("THINK", "DISCOVERY") or entry.get("author") == "MIND":
        return "INFERRED"                          # reflections and discoveries
    if _source_kind(entry) == "conversation":
        return "REPORTED"                          # ingested, unverified
    if entry.get("assumption") is True or entry.get("confidence") == "assumed":
        return "ASSUMED"
    if _source_kind(entry) == "policy":
        return "STIPULATED"
    if not entry.get("opcode") and not entry.get("author") and not entry.get("source"):
        return "UNKNOWN"                           # nothing identifiable
    return "INFERRED"                              # the honest default


# ---------------------------------------------------------------------------
# 4. Force (channel A) -- DEFAULT TABLE (section 4.3 of the plan)
# ---------------------------------------------------------------------------
FORCE_BY_OPCODE: Dict[str, str] = {
    "THINK": "MAY",            # reflection, no obligation
    "PROPOSE": "MAY",          # propose only
    "SPECIAL": "MAY",
    "CONSOLIDATE": "LET",      # propose only
    "DISPATCH": "GATE",        # body-authorized action
    "INTENTION": "GATE",
    "DELEGATED": "GATE",
    "PROOF": "BOUND",          # recorded obligation of an action
    "IMMUNE": "MUST",          # integrity response
    "WARN": "MUST",
    "SENSE": "WAY",            # observed, informative
    "RULE": "RULE",            # LAW only with operator stipulation
    "POLICY": "RULE",
    "DEWEIGHT": "BOUND",       # graded-memory bookkeeping
    "WRITE": "BOUND",          # a Body-authored record
    "DISCOVERY": "BOUND",      # a Body-authored claim record
    "RECALL": "WAY",
}
MODEL_PREFIX_FORCE = "BOUND"   # MODEL.* body traces are recorded actions

# name -> channel address (the registries are keyed by address; encoding needs names)
_EVIDENCE_BY_NAME: Dict[str, int] = {name: number for number, name in v010.EVIDENCE.items()}
_FORCE_BY_NAME: Dict[str, int] = {name: number for number, name in v010.FORCE.items()}


def resolve_force(entry: Dict[str, Any]) -> str:
    """The DEFAULT force mapping for one entry (QUOTE when unmapped -- never invented)."""
    marker = entry.get("force")
    if marker is not None:
        name = _to_name(marker, v010.FORCE, "force")
        if name == "LAW":
            # LAW is reserved for operator stipulation
            if entry.get("stipulated") is True or _source_kind(entry) == "policy":
                return "LAW"
            return "QUOTE"
        return name
    op = str(entry.get("opcode") or "")
    if op in FORCE_BY_OPCODE:
        return FORCE_BY_OPCODE[op]
    if op.startswith("MODEL."):
        return MODEL_PREFIX_FORCE
    return "QUOTE"             # unmapped -> inert, never invented


def resolve_record_kind(opcode: str) -> Optional[Tuple[Tuple[int, ...], str]]:
    """Canonical composition for an opcode, or None (undifferentiated record)."""
    op = str(opcode or "")
    name = RECORD_KIND_BY_OPCODE.get(op)
    if name is None and op.startswith("MODEL."):
        name = MODEL_PREFIX_COMPOSITION
    if name is None:
        return None
    spelling, gloss = COMPOSITION_ROWS[name]
    return spelling, "%s (%s)" % (name, gloss)


# ---------------------------------------------------------------------------
# 5. The edition cross-check (refuse to invent addresses)
# ---------------------------------------------------------------------------
def _edition_composition_rows() -> Dict[str, Tuple[int, ...]]:
    """Parse section 6 of the frozen edition document into name -> atom spelling.

    Mirrors `tools/grimoire_tool.py`'s parser (name -> composed Chinese spelling ->
    atom addresses via the section-5 gloss table). Returns {} when the document is
    absent (installed package); raises when the document is present but inconsistent.
    """
    source_path = os.path.join(paths.REPO_ROOT, "documents", "grimoire", "editions",
                               "grimoire-v0.10.md")
    if not os.path.isfile(source_path):
        return {}
    with open(source_path, encoding="utf-8") as fh:
        source = fh.read()
    block = source.split("## 6 COMPOSITION", 1)[1].split("## 7 CONFORMANCE", 1)[0]
    atoms_block = source.split("## 5 ATOM", 1)[1].split("## 6 COMPOSITION", 1)[0]
    by_char: Dict[str, int] = {}
    for num, ch, _gloss in re_find_atoms(atoms_block):
        by_char.setdefault(ch, num)
    rows: Dict[str, Tuple[int, ...]] = {}
    for line in block.splitlines():
        m = re_match_composition(line)
        if not m:
            continue
        name, spelling = m
        ids = tuple(by_char[ch] for ch in spelling)
        rows[name] = ids
    return rows


def re_find_atoms(block: str) -> List[Tuple[int, str, str]]:
    """Section-5 atom rows: (address, character, gloss)."""
    import re
    return [(int(num), ch, gloss)
            for num, ch, gloss in re.findall(r"(\d{1,3})\s+(\S)\s+([a-z_]+)", block)]


def re_match_composition(line: str) -> Optional[Tuple[str, str]]:
    """Section-6 composition row: (name, composed spelling) or None."""
    import re
    m = re.match(r"^([a-z][a-z_0-9]*)\s+([^\sA-Za-z]+)\s*(.*)$", line)
    if not m:
        return None
    return m.group(1), m.group(2)


_EDITION_ROWS = _edition_composition_rows()
_SOURCE_VERIFIED = False
if _EDITION_ROWS:
    # The mirror must equal the edition for every row this profile uses.
    for _name, (_spelling, _gloss) in COMPOSITION_ROWS.items():
        _edition_spelling = _EDITION_ROWS.get(_name)
        if _edition_spelling is None:
            raise GrimoireEditionError(
                "semantic profile composition %r is not a canonical section-6 row"
                % _name)
        if _edition_spelling != _spelling:
            raise GrimoireEditionError(
                "semantic profile composition %r spells %r in the mirror but %r "
                "in the edition" % (_name, _spelling, _edition_spelling))
    _SOURCE_VERIFIED = True


def composition_source_verified() -> bool:
    """True when the mirror was verified against the edition document (checkout)."""
    return _SOURCE_VERIFIED


# ---------------------------------------------------------------------------
# 6. The encoder: one entry -> one semantic record with two framed runs
# ---------------------------------------------------------------------------
def _ts_nibble_atoms(ts: float) -> Tuple[int, ...]:
    """Canonical time spelling: nibble atoms of hex(int(ts)), atom = nibble + 1."""
    value = int(ts)
    if value < 0:
        value = 0
    hex_text = "%x" % value
    return tuple(int(ch, 16) + 1 for ch in hex_text)


def encode_entry(entry: Dict[str, Any], *, frame_id: str = "semantic-frame",
                 adoption: str = "data") -> Dict[str, Any]:
    """Encode one entry-shaped record into a semantic record (the one step).

    Returns an entry-shaped dict with a `semantic` metadata dict:
      raw          hex of the structural v0.10 statement (record kind/author/time/
                   evidence/force + PARITY)
      content_raw  hex of the content QUOTE frame (verbatim content bytes)
      statement    the decoded structural statement (from v010.decode_statement)
      parity_status / fingerprint / evidence / force / composition / adoption
    The returned record's `hash` is the standard total entry hash over every
    non-volatile field, including `semantic` (raw runs are hex text, so the
    serialization is deterministic).
    """
    if not isinstance(entry, dict) or not entry.get("opcode"):
        raise GrimoireEditionError("semantic encode requires an entry-shaped dict "
                                   "with an opcode")
    evidence = resolve_evidence(entry)
    force = resolve_force(entry)
    kind = resolve_record_kind(str(entry.get("opcode") or ""))
    opcode_text = str(entry.get("opcode") or "")

    records: List[Tuple[int, int, int, int]] = []
    if kind is not None:
        spelling, _gloss = kind
        records.append((spelling[0], v010.HEAD, _EVIDENCE_BY_NAME[evidence],
                        _FORCE_BY_NAME[force]))
        records.extend((atom, v010.BLEND, 0, 0) for atom in spelling[1:])
    else:
        # undifferentiated record: HEAD 一 (one), opcode token stays in the fields
        records.append((UNDIFFERENTIATED_ATOM, v010.HEAD, _EVIDENCE_BY_NAME[evidence],
                        _FORCE_BY_NAME[force]))
    author = str(entry.get("author") or "BODY")
    if author in AUTHOR_ATOMS:
        records.append((AUTHOR_ATOMS[author], 0x02, 0, 0))       # AGENT
    ts = entry.get("ts")
    if ts is not None:
        nibbles = _ts_nibble_atoms(ts)
        records.append((nibbles[0], 0x21, 0, 0))                 # TIME
        records.extend((atom, v010.BLEND, 0, 0) for atom in nibbles[1:])
    records.append(v010.parity_pixel(records))

    raw = b"".join(bytes(record) for record in records)
    content_bytes = json.dumps(entry.get("content"), sort_keys=True,
                               separators=(",", ":"), ensure_ascii=False,
                               default=str).encode("utf-8")
    content_raw = v010.encode_quoted_bytes(content_bytes, evidence=0x01, force=0x0F)

    statement = v010.decode_statement(raw, frame_id=frame_id, profile=BASE_PROFILE,
                                      adoption_policy="data")
    composition_name = None
    if kind is not None:
        _spelling, gloss = kind
        composition_name = gloss.split(" (")[0]
    semantic = {
        "profile": PROFILE,
        "raw": raw.hex(),
        "content_raw": content_raw.hex(),
        "statement": statement,
        "parity_status": statement["parity_status"],
        "fingerprint": v010.raw_run_fingerprint(raw, frame_id),
        "evidence": evidence,
        "force": force,
        "composition": composition_name,
        "adoption": adoption,
        "content_sha256": hashlib.sha256(content_bytes).hexdigest()[:16],
    }
    record = dict(entry)
    record["semantic"] = semantic
    record["hash"] = entry_hash(record)
    return record


def decode_entry(record: Dict[str, Any], *, frame_id: str = "semantic-frame",
                 verify_content: bool = True) -> Dict[str, Any]:
    """Verify and decode a semantic record back to its entry-shaped form.

    Raises GrimoireDecodeError on: missing semantic metadata, entry-hash mismatch
    (tampered raw/fields), statement parity failure, or content mismatch against
    the QUOTE frame. Returns the entry-shaped record unchanged on success.
    """
    from .v010 import GrimoireDecodeError
    if not isinstance(record, dict) or "semantic" not in record:
        raise GrimoireDecodeError("semantic record has no semantic metadata")
    semantic = record["semantic"]
    if entry_hash(record) != record.get("hash"):
        raise GrimoireDecodeError("semantic record hash mismatch "
                                  "(raw run or fields were tampered)")
    raw = semantic.get("raw")
    if not raw:
        raise GrimoireDecodeError("semantic record has no raw run")
    statement = v010.decode_statement(raw, frame_id=frame_id, profile=BASE_PROFILE,
                                      adoption_policy="data")
    if statement["parity_status"] != "ok":
        raise GrimoireDecodeError("semantic record parity failure")
    if verify_content:
        content_raw = semantic.get("content_raw")
        if not content_raw:
            raise GrimoireDecodeError("semantic record has no content frame")
        content_bytes = v010.decode_quoted_bytes(content_raw, frame_id=frame_id + "-content")
        decoded = json.loads(content_bytes.decode("utf-8"))
        if decoded != record.get("content"):
            raise GrimoireDecodeError("semantic record content mismatch "
                                      "(QUOTE frame drifts from the stored content)")
    return record


def content_digest(entry: Dict[str, Any]) -> str:
    """The metabolism dedupe key for a semantic record (opcode + content hash)."""
    return content_hash(entry.get("content"))


# ---------------------------------------------------------------------------
# 7. Selftest vectors (mirrors the edition's vector style)
# ---------------------------------------------------------------------------
def _vector_entry(opcode: str, **overrides: Any) -> Dict[str, Any]:
    e = {"id": None, "ts": 123456789.0, "opcode": opcode, "author": "MIND",
         "source": "", "content": {"reflection": "example"},
         "tombstone": False, "quarantined": False, "verified": False,
         "confidence": "inferred"}
    e.update(overrides)
    return e


def selftest_vectors() -> Tuple[Tuple[str, Dict[str, Any], str, str], ...]:
    """(label, entry, expected evidence, expected force) -- at least THINK/SENSE/IMMUNE."""
    return (
        ("THINK", _vector_entry("THINK"), "INFERRED", "MAY"),
        ("SENSE", _vector_entry("SENSE", author="BODY", source="sensor-1",
                                verified=True), "MEASURED", "WAY"),
        ("IMMUNE", _vector_entry("IMMUNE", author="BODY", source="immune",
                                 content={"event": "overflow"}), "INFERRED", "MUST"),
    )


def selftest() -> List[Tuple[str, bool, str]]:
    """Run the selftest vectors through encode -> decode; return (label, ok, note)."""
    results = []
    for label, entry, expected_evidence, expected_force in selftest_vectors():
        try:
            record = encode_entry(entry)
            evidence = record["semantic"]["evidence"]
            force = record["semantic"]["force"]
            parity = record["semantic"]["parity_status"]
            decode_entry(record)
            ok = (evidence == expected_evidence and force == expected_force
                  and parity == "ok")
            results.append((label, ok,
                            "evidence=%s force=%s parity=%s" % (evidence, force, parity)))
        except Exception as exc:  # noqa: BLE001 -- selftest reports, never crashes
            results.append((label, False, "%s: %s" % (type(exc).__name__, exc)))
    return results
