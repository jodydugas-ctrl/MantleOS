# -*- coding: utf-8 -*-
"""
grimoire_tool — independent bidirectional verifier for GRIMOIRE v0.10.

Scope: text <-> IR <-> pixel records (four unsigned bytes, RGBA order).
Out of scope: colour, PNG, layers, VCW persistence. Those are a lower layer.

Design premise
--------------
Axiom A3: "Natural language is an utterance. The pixel run is its canonical
interpretation."  Interpretation is not inversion.  Therefore:

    run  -> IR  -> run     is deterministic, total, and byte-exact (canonical form)
    text -> IR             is partial: it resolves what the lexicon can resolve
                           and leaves an explicit hole everywhere judgment is required

The holes are not a defect.  They are the machine-checkable statement of what a
deterministic Body cannot decide and must delegate.  A hole is never guessed and
never silently defaulted; an IR containing holes cannot be encoded.

Tables are read from the canonical Grimoire markdown at load time, per axiom A1
(ONE EDITION).  The codec therefore cannot drift from the book.

Pure standard library.
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
import unicodedata

# --------------------------------------------------------------------------
# 1. TABLES  (loaded from the canonical edition; nothing is hardcoded here)
# --------------------------------------------------------------------------

BLEND, HEAD, END, PARITY = 0x40, 0x01, 0x00, 0x7f


def rotl(b, n):
    """Rotate one byte left. Gives the parity residue a position term."""
    n &= 7
    return ((b << n) | (b >> (8 - n))) & 0xFF


def residue(body):
    """R11 (edition v0.10). Position-weighted, and it covers the role lane.
    body is every non-parity pixel of the statement, in emission order."""
    pr = pb = pa = 0
    for i, (R, G, B, A) in enumerate(body):
        w = i & 7
        pr ^= rotl(R, w)
        pb ^= rotl(B, w) ^ rotl(G, w)
        pa ^= rotl(A, w) ^ rotl(G, 7 - w)
    return (254 if pr == 0 else pr, PARITY, pb, pa)


def _section(src, header):
    """Text of one section. The header must be anchored at line start, so an
    occurrence of the same string inside this file -- which is embedded in the
    book it parses -- can never be mistaken for the section itself."""
    matches = list(re.finditer(r"^" + re.escape(header) + r".*$", src, re.M))
    if not matches:
        raise ValueError("section %r missing" % header)
    if len(matches) != 1:
        raise ValueError("section %r duplicated (%d headings)" % (header, len(matches)))
    m = matches[0]
    rest = src[m.end():]
    nxt = re.search(r"^## \d+ ", rest, re.M)
    return rest[:nxt.start()] if nxt else rest


class Grimoire(object):
    """Sections 2-6 of one Grimoire edition, loaded from its markdown."""

    @classmethod
    def from_text(cls, source):
        """Build from the Grimoire markdown held in memory (no filesystem)."""
        obj = cls.__new__(cls)
        obj._init(source)
        return obj

    def __init__(self, path):
        self._init(open(path, encoding="utf-8").read())

    def _init(self, src):
        edition = re.findall(r"GRIMOIRE\s+(v[\d.]+)", src)
        if not edition:
            raise ValueError("edition declaration missing")
        if len(set(edition)) != 1:
            raise ValueError("edition declarations disagree: %s" % sorted(set(edition)))
        self.edition = edition[0]
        if self.edition != "v0.10":
            raise ValueError(
                "independent verifier supports GRIMOIRE v0.10 only; "
                "use the frozen profile compatibility tests for %s" % self.edition
            )
        self.atoms, self.gloss_to_atom = self._load_atoms(src)
        self.roles = self._load_enum(src, "## 2 ROLE", hexval=True)
        self.evidence = self._load_enum(src, "## 3 EVIDENCE")
        self.force = self._load_enum(src, "## 4 FORCE", hexval=True)
        self.compositions, self.aliases = self._load_compositions(src)
        self.lexicon = self._build_lexicon()

    # ---- section 5 -------------------------------------------------------
    @staticmethod
    def _load_atoms(src):
        block = _section(src, "## 5 ATOM").split("```")[1]
        atoms, by_gloss = {}, {}
        for num, ch, gloss in re.findall(r"(\d{1,3})\s+(\S)\s+([a-z_]+)", block):
            n = int(num)
            atoms[n] = (ch, gloss)
            by_gloss.setdefault(gloss, n)
        if set(atoms) != set(range(1, 255)):
            raise ValueError("atom table is not the full 1-254 range")
        return atoms, by_gloss

    # ---- sections 2, 3, 4 ------------------------------------------------
    @staticmethod
    def _load_enum(src, start, stop=None, hexval=False):
        block = _section(src, start).split("```")[1]
        base = 16 if hexval else 10
        table = {}
        for val, name in re.findall(r"^\s*([0-9a-f]{2})\s+([A-Z_0-9]+)", block, re.M):
            table[int(val, base)] = name
        # section 2 abbreviates STEP_3..STEP_15 in prose; expand the ordinals
        if any(n.startswith("STEP_") for n in table.values()):
            for i in range(16):
                table[0x60 + i] = "STEP_%d" % (i + 1)
        return table

    # ---- section 6 -------------------------------------------------------
    def _load_compositions(self, src):
        block = _section(src, "## 6 COMPOSITION")
        comps, spelling_owners = {}, {}
        for line in block.splitlines():
            m = re.match(r"^([a-z][a-z_0-9]*)\s+([^\sA-Za-z]+)\s*(.*)$", line)
            if not m:
                continue
            name, spelling = m.group(1), m.group(2)
            ids = []
            for ch in spelling:
                if unicodedata.category(ch) != "Lo":
                    continue
                hit = [n for n, (c, _) in self.atoms.items() if c == ch]
                if not hit:
                    ids = None
                    break
                ids.append(hit[0])
            if not ids:
                continue
            comps[name] = ids
            spelling_owners.setdefault(tuple(ids), []).append(name)
        aliases = {}
        for ids, names in spelling_owners.items():
            if len(names) > 1:
                canonical = sorted(names)[0]          # §6: decoder normalises
                for n in names:
                    aliases[n] = canonical
        return comps, aliases

    # ---- deterministic surface-form lexicon ------------------------------
    def _build_lexicon(self):
        """term -> [atom ids].  Composition names win over bare radical glosses."""
        lex = {}
        for n, (_ch, gloss) in self.atoms.items():
            lex.setdefault(gloss, [n])
        for name, ids in self.compositions.items():
            lex[name] = list(ids)                      # authoritative
        return lex

    # ---- helpers ---------------------------------------------------------
    def role_val(self, name):
        return self._rev(self.roles, name, "role")

    def evid_val(self, name):
        return self._rev(self.evidence, name, "evidence")

    def force_val(self, name):
        return self._rev(self.force, name, "force")

    @staticmethod
    def _rev(table, name, kind):
        for v, n in table.items():
            if n == name:
                return v
        raise KeyError("unknown %s %r" % (kind, name))

    def spell(self, ids):
        return "".join(self.atoms[i][0] for i in ids)

    def name_of(self, ids):
        """Canonical concept name for an atom-group spelling, if the book has one."""
        for name, comp in self.compositions.items():
            if comp == list(ids):
                return self.aliases.get(name, name)
        if len(ids) == 1:
            return self.atoms[ids[0]][1]
        return None


# --------------------------------------------------------------------------
# 2. INTERMEDIATE REPRESENTATION
# --------------------------------------------------------------------------

HOLE = "?"


class Morpheme(object):
    """One atom-group: an operative role plus a composed atom spelling."""

    __slots__ = ("atoms", "role", "evidence", "force")

    def __init__(self, atoms, role, evidence=0, force=0):
        self.atoms = list(atoms)
        self.role = role                # int, or HOLE
        self.evidence = evidence        # int, or HOLE  (HEAD only)
        self.force = force              # int, or HOLE  (HEAD only)

    @property
    def resolved(self):
        return HOLE not in (self.role, self.evidence, self.force)


class Statement(object):
    def __init__(self, morphemes, frame_id=None, source=None, unresolved=None):
        self.morphemes = list(morphemes)
        self.frame_id = frame_id
        self.source = source            # A3: the utterance is retained beside the run
        self.unresolved = list(unresolved or [])

    @property
    def holes(self):
        out = list(self.unresolved)
        for i, m in enumerate(self.morphemes):
            for field in ("role", "evidence", "force"):
                if getattr(m, field) == HOLE:
                    out.append("morpheme %d: %s undecided" % (i + 1, field))
        if not any(m.role == HEAD for m in self.morphemes):
            out.append("no HEAD selected")
        return out

    @property
    def complete(self):
        return not self.holes


# --------------------------------------------------------------------------
# 3. IR  <->  PIXELS      (deterministic, total, byte-exact both ways)
# --------------------------------------------------------------------------

def canonical_order(morphemes):
    """A11/R7: order between groups is non-semantic, so fix one canonical order.
    HEAD first, then by (role, spelling).  XOR parity is commutative, so
    reordering never disturbs the parity pixel."""
    head = [m for m in morphemes if m.role == HEAD]
    rest = sorted((m for m in morphemes if m.role != HEAD),
                  key=lambda m: (m.role, tuple(m.atoms)))
    return head + rest


def encode(stmt, g, canonical=True):
    """IR -> pixel records.  Refuses to encode an incomplete statement."""
    if not stmt.complete:
        raise ValueError("cannot encode: unresolved judgment\n  - "
                         + "\n  - ".join(stmt.holes))
    morphs = canonical_order(stmt.morphemes) if canonical else stmt.morphemes
    px = []
    for m in morphs:
        px.append((m.atoms[0], m.role, m.evidence, m.force))
        for extra in m.atoms[1:]:
            px.append((extra, BLEND, 0, 0))           # §6: spelling continuation
    px.append(residue(px))                             # R11
    return px


def decode(px, g):
    """Pixel records -> IR.  Groups BLEND runs; ignores the parity control pixel."""
    morphs, cur = [], None
    for R, G, B, A in px:
        if G == PARITY or G == END:
            continue
        if G == BLEND:
            if cur is None:
                raise ValueError("R6: floating BLEND")
            cur.atoms.append(R)
        else:
            cur = Morpheme([R], G, B, A)
            morphs.append(cur)
    return Statement(morphs)


# --------------------------------------------------------------------------
# 4. CONFORMANCE  (section 7)
# --------------------------------------------------------------------------

def conform(px, g, *, container_evidence=None, container_force=None):
    """Return structural errors for one independent v0.10 run.

    Container metadata is accepted only for the zero-HEAD procedure exception;
    it never changes the raw pixels or grants adoption authority.
    """
    bad = []
    records = list(px)
    if records and records[-1][1] == END and records[-1] == (0, 0, 0, 0):
        records.pop()
    if any(p[1] == END for p in records):
        bad.append("R2 END may only be a terminal frame marker")
    parity_positions = [i for i, p in enumerate(records) if p[1] == PARITY]
    if len(parity_positions) > 1:
        bad.append("more than one PARITY control pixel")
    if parity_positions and parity_positions[0] != len(records) - 1:
        bad.append("R6 PARITY must be terminal")
    if any(records[i][1] == BLEND and i and records[i - 1][1] == PARITY
           for i in range(len(records))):
        bad.append("R6 BLEND group was interrupted and resumed")
    body = [p for p in records if p[1] != PARITY]
    heads = [p for p in body if p[1] == HEAD]
    lead_roles = [p[1] for p in body if p[1] != BLEND]
    procedure = not heads and all(0x60 <= role <= 0x6F for role in lead_roles)
    if len(heads) > 1:
        bad.append("R3 statement has %d HEAD morphemes" % len(heads))
    elif not heads and not procedure:
        bad.append("R3 normal statement has zero HEAD morphemes")
    step_roles = [role for role in lead_roles if 0x60 <= role <= 0x6F]
    if len(step_roles) != len(set(step_roles)):
        bad.append("R3 procedure STEP ordinals repeat")
    for R, G, B, A in heads:
        if B == 0 or A == 0:
            bad.append("R4 HEAD may not inherit evidence or force")
    for i, (R, G, B, A) in enumerate(records):
        if R == 0:
            bad.append("R2 unwritten pixel at %d" % i)
        if G not in g.roles:
            bad.append("R5 unknown role %02x at %d" % (G, i))
        if G != PARITY:                # §1: the parity pixel is a control pixel,
            if B not in g.evidence:    # not a morpheme; its B/A are residue bytes
                bad.append("R5 unknown evidence %02x at %d" % (B, i))
            if A not in g.force:
                bad.append("R5 unknown force %02x at %d" % (A, i))
        if G not in (HEAD, PARITY, END) and (B, A) != (0, 0):
            bad.append("R4 non-HEAD morpheme at %d must inherit" % i)
        if G == BLEND and (i == 0 or records[i - 1][1] in (PARITY, END)):
            bad.append("R6 floating BLEND at %d" % i)
    par = [p for p in records if p[1] == PARITY]
    if par and par[0] != residue(body):
            bad.append("R11 parity mismatch")
    if body and body != canonical_order_px(body):
        bad.append("R14 statement is not in canonical group order")
    return bad


def canonical_order_px(px):
    """R14 applied to raw pixels: regroup, sort, re-expand."""
    groups, cur = [], None
    for R, G, B, A in px:
        if G == BLEND and cur is not None:
            cur[0].append(R)
        else:
            cur = ([R], G, B, A); groups.append(cur)
    head = [g for g in groups if g[1] == HEAD]
    rest = sorted((g for g in groups if g[1] != HEAD), key=lambda g: (g[1], tuple(g[0])))
    out = []
    for atoms, G, B, A in head + rest:
        out.append((atoms[0], G, B, A))
        out.extend((x, BLEND, 0, 0) for x in atoms[1:])
    return out


def _table_label(table, value):
    if value is None:
        return "INHERIT"
    if isinstance(value, str):
        if value not in table.values():
            raise ValueError("unknown metadata label %r" % value)
        return value
    if value not in table:
        raise ValueError("unknown metadata value %r" % value)
    return table[value]


def report(px, g, frame_id=None, source=None, container_evidence=None,
           container_force=None):
    """R13: edition-neutral independent output contract."""
    bad = conform(px, g, container_evidence=container_evidence,
                  container_force=container_force)
    stmt = decode(px, g)
    heads = [m for m in stmt.morphemes if m.role == HEAD]
    procedure = not heads and all(0x60 <= m.role <= 0x6F
                                  for m in stmt.morphemes)
    if heads:
        effective_evidence = g.evidence[heads[0].evidence]
        effective_force = g.force[heads[0].force]
        evidence_source = force_source = "head"
    else:
        effective_evidence = _table_label(g.evidence, container_evidence)
        effective_force = _table_label(g.force, container_force)
        evidence_source = "container" if container_evidence is not None else "missing-container"
        force_source = "container" if container_force is not None else "missing-container"
    raw = bytes(v for rec in px for v in rec)
    digest = hashlib.sha256(str(frame_id).encode("utf-8") + b"\0" + raw).hexdigest()
    return {
        "profile": "grimoire-v0.10",
        "byte_order": "RGBA",
        "frame_id": frame_id,
        "container_frame_id": None,
        "raw": raw.hex(),
        "original_raw_run": hexrun(px),
        "raw_fingerprint": "sha256:" + digest,
        "fingerprint_status": "not-claimed",
        "full_lane_integrity": "unmeasured",
        "parity_status": "absent-carrier-integrity" if not any(p[1] == PARITY for p in px)
                         else ("mismatch" if any("R11" in x for x in bad) else "ok"),
        "parity_expected": {},
        "head_present": bool(heads),
        "effective_evidence": effective_evidence,
        "effective_force": effective_force,
        "evidence_source": evidence_source,
        "force_source": force_source,
        "groups": [
            {"spelling": g.spell(m.atoms),
             "atoms": [g.atoms[i][1] for i in m.atoms],
             "concept": g.name_of(m.atoms),
             "role": g.roles.get(m.role)}
            for m in stmt.morphemes],
        "unknowns": [x for x in bad if x.startswith("R5")],
        "governing": False,
        "adoption": {"status": "data", "governing": False, "authority": "none"},
        "rejected": bool(bad),
        "rejection_reason": bad or None,
        "reason": bad or None,
        "source_utterance": source,          # R8, mirrored: keep the utterance
    }


# --------------------------------------------------------------------------
# 5. IR TEXT FORMAT   (human-editable, diff-friendly, holes visible)
# --------------------------------------------------------------------------

def ir_dumps(stmt, g):
    out = []
    if stmt.source:
        out.append("# " + stmt.source)
    for m in stmt.morphemes:
        role = g.roles.get(m.role, HOLE) if m.role != HOLE else HOLE
        spelling = "+".join(g.atoms[i][1] for i in m.atoms)
        if m.role == HEAD or HOLE in (m.evidence, m.force):
            ev = g.evidence.get(m.evidence, HOLE) if m.evidence != HOLE else HOLE
            fo = g.force.get(m.force, HOLE) if m.force != HOLE else HOLE
            out.append("%-12s %-22s %-11s %s" % (role, spelling, ev, fo))
        else:
            out.append("%-12s %s" % (role, spelling))
    for u in stmt.unresolved:
        out.append("!unresolved  %s" % u)
    return "\n".join(out)


def ir_loads(text, g):
    morphs, source, unresolved = [], None, []
    for line in text.splitlines():
        line = line.rstrip()
        if not line:
            continue
        if line.startswith("#"):
            source = line[1:].strip()
            continue
        if line.startswith("!unresolved"):
            unresolved.append(line.split(None, 1)[1])
            continue
        f = line.split()
        role = HOLE if f[0] == HOLE else g.role_val(f[0])
        ids = []
        for term in f[1].split("+"):
            if term not in g.lexicon:
                raise KeyError("term %r is not in the edition lexicon" % term)
            ids.extend(g.lexicon[term])
        ev, fo = 0, 0
        if len(f) >= 4:
            ev = HOLE if f[2] == HOLE else g.evid_val(f[2])
            fo = HOLE if f[3] == HOLE else g.force_val(f[3])
        morphs.append(Morpheme(ids, role, ev, fo))
    return Statement(morphs, source=source, unresolved=unresolved)


# --------------------------------------------------------------------------
# 6. TEXT -> IR      (partial by construction; every gap is declared)
# --------------------------------------------------------------------------

SENTENCE = re.compile(r"[^.!?;\n]+[.!?;]?")
WORD = re.compile(r"[A-Za-z][A-Za-z_-]*")

# Ingested text is someone else's utterance. The system is recording it, not
# asserting it, so the honest default is CITED / QUOTE -- and A5 ("a derivable
# rule is removed unless force is QUOTE") only coheres under that reading.
INGEST_EVIDENCE, INGEST_FORCE = "CITED", "QUOTE"


def text_to_ir(text, g, evidence=INGEST_EVIDENCE, force=INGEST_FORCE):
    """Resolve what the lexicon can resolve. Declare everything else as a hole.

    Deterministic and safe: role assignment and HEAD selection are never
    guessed, because nothing in sections 2-6 licenses inferring them from
    surface word order."""
    stmts = []
    for n, raw in enumerate(SENTENCE.findall(text), 1):
        sent = raw.strip()
        if not sent:
            continue
        morphs, missing, seen = [], [], set()
        for w in WORD.findall(sent.lower()):
            if w in seen:
                continue
            seen.add(w)
            if w in g.lexicon:
                morphs.append(Morpheme(g.lexicon[w], HOLE, 0, 0))
            else:
                missing.append("term %r has no address in edition %s" % (w, g.edition))
        if morphs:
            morphs[0].evidence = g.evid_val(evidence)   # candidate HEAD carries them
            morphs[0].force = g.force_val(force)
            morphs[0].role = HOLE
        stmts.append(Statement(morphs, frame_id="L%d" % n, source=sent,
                               unresolved=missing))
    return stmts


# --------------------------------------------------------------------------
# 7. rendering
# --------------------------------------------------------------------------

DIGITS = "〇一二三四五六七八九"


def han(n):
    if n < 10:
        return DIGITS[n]
    if n < 20:
        return "十" + (DIGITS[n - 10] if n > 10 else "")
    if n < 100:
        t, o = divmod(n, 10)
        return DIGITS[t] + "十" + (DIGITS[o] if o else "")
    h, r = divmod(n, 100)
    s = DIGITS[h] + "百"
    if r == 0:
        return s
    if r < 10:
        return s + "〇" + DIGITS[r]
    t, o = divmod(r, 10)
    return s + (DIGITS[t] + "十" if t else "十") + (DIGITS[o] if o else "")


def hexrun(px):
    return " ".join("%02x%02x%02x%02x" % p for p in px)


def hanrun(px, g):
    out = []
    for R, G, B, A in px:
        if G == PARITY:
            out.append("⟨%s·%s·%s·%s⟩" % (han(R), han(G), han(B), han(A)))
        else:
            out.append("%s·%s·%s·%s" % (g.atoms[R][0], han(G), han(B), han(A)))
    return " ─ ".join(out)


def parse_hexrun(s):
    px = []
    for tok in s.split():
        v = int(tok, 16)
        px.append(((v >> 24) & 255, (v >> 16) & 255, (v >> 8) & 255, v & 255))
    return px


# --------------------------------------------------------------------------
# 8. SELFTEST  --  python3 grimoire_codec.py <path-to-Grimoire.md>
# --------------------------------------------------------------------------

def selftest(path):
    g = Grimoire(path)
    fails = []
    body = _section(open(path, encoding="utf-8").read(), "## 9 SELFTEST")
    vectors = re.findall(r"[0-9a-f]{8}(?: [0-9a-f]{8})+", body)
    for v in vectors:
        px = parse_hexrun(v)
        bad = conform(px, g)
        if bad:
            fails.append("vector %s: %s" % (v[:8], "; ".join(bad)))
        procedure = not any(p[1] == HEAD for p in px if p[1] != PARITY)
        if not bad and not procedure:
            if hexrun(encode(decode(px, g), g)) != v:
                fails.append("vector %s: run->IR->run not byte-exact" % v[:8])
    books = _book_vectors(path)
    book_fails = []
    for v in books:
        bad = conform(parse_hexrun(v), g)
        if bad:
            book_fails.append("vector %s: %s" % (v[:8], "; ".join(bad)))
    print("edition %s | atoms %d | roles %d | evidence %d | force %d | compositions %d | lexicon %d"
          % (g.edition, len(g.atoms), len(g.roles), len(g.evidence), len(g.force),
             len(g.compositions), len(g.lexicon)))
    print("section 9 vectors: %d checked, %d failed" % (len(vectors), len(fails)))
    for f in fails:
        print("  FAIL " + f)
    print("BOOK runs: %d checked, %d failed" % (len(books), len(book_fails)))
    for f in book_fails[:20]:
        print("  BOOK FAIL " + f)
    all_fails = fails + book_fails
    print("SELFTEST " + ("PASS" if not all_fails else "FAIL"))
    return 0 if not all_fails else 1


def _vector_text(path):
    body = _section(open(path, encoding="utf-8").read(), "## 9 SELFTEST")
    return re.findall(r"[0-9a-f]{8}(?: [0-9a-f]{8})+", body)


def _book_vectors(path):
    body = _section(open(path, encoding="utf-8").read(), "## 10 BOOK")
    return re.findall(r"[0-9a-f]{8}(?: [0-9a-f]{8})+", body)


def _json_or_print(value, as_json):
    if as_json:
        print(json.dumps(value, ensure_ascii=True, sort_keys=True))
    elif isinstance(value, dict):
        for key, item in value.items():
            print("%s: %s" % (key, item))
    else:
        print(value)


def compare(path, profile):
    if profile != "grimoire-v0.10":
        raise ValueError("compare currently requires --profile grimoire-v0.10")
    g = Grimoire(path)
    vectors = _vector_text(path) + _book_vectors(path)
    independent = []
    differences = []
    for vector in vectors:
        px = parse_hexrun(vector)
        bad = conform(px, g)
        decoded = decode(px, g)
        independent.append({
            "profile": "grimoire-v0.10",
            "raw": hexrun(px).replace(" ", ""),
            "groups": [[g.roles.get(m.role), list(m.atoms)] for m in decoded.morphemes
                        if m.role != PARITY],
            "conform": bad,
        })
    script = (
        "import json,sys; "
        "from mantle.vcw.grimoire_editions import decode_statement; "
        "vectors=json.load(sys.stdin); out=[]; "
        "\nfor i,v in enumerate(vectors):\n"
        " d=decode_statement(v, profile='grimoire-v0.10', frame_id='compare-%d'%i); "
        " out.append({'profile':d['profile'],'raw':d['raw'],'groups':[(g['role'],tuple(a['atom']['address'] for a in g['atoms'])) for g in d['groups']], 'parity':d['parity_status']})\n"
        "print(json.dumps(out))"
    )
    proc = subprocess.run(
        [sys.executable, "-c", script], input=json.dumps(vectors), text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=".",
        env=dict(__import__("os").environ, PYTHONPATH="src"), check=False,
    )
    if proc.returncode:
        raise RuntimeError("production comparison failed: " + proc.stdout.strip())
    production = json.loads(proc.stdout)
    for index, (left, right) in enumerate(zip(independent, production)):
        if left["profile"] != right["profile"] or left["raw"] != right["raw"] \
                or left["groups"] != right["groups"] or left["conform"]:
            differences.append({"vector": index, "independent": left, "production": right})
    return {
        "profile": profile,
        "vectors": len(vectors),
        "compared": len(production),
        "differences": differences,
        "status": "PASS" if not differences else "FAIL",
        "limitations": [
            "statement-local parity is not full-lane transport integrity",
            "procedure effective evidence/force require explicit container metadata",
        ],
    }


def main(argv=None):
    # Keep diagnostic failures machine-readable on Windows consoles whose legacy
    # code page cannot represent a decoded Grimoire glyph.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="backslashreplace")
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] not in {"verify", "decode", "atom", "compare"}:
        argv.insert(0, "verify")
    parser = argparse.ArgumentParser(prog="python tools/grimoire_tool.py")
    sub = parser.add_subparsers(dest="command", required=True)

    verify = sub.add_parser("verify", help="verify all BOOK selftest runs")
    verify.add_argument("edition")
    verify.add_argument("--json", action="store_true")

    decode_cmd = sub.add_parser("decode", help="structurally decode one run")
    decode_cmd.add_argument("edition")
    decode_cmd.add_argument("run")
    decode_cmd.add_argument("--frame-id", default="tool-frame")
    decode_cmd.add_argument("--container-evidence")
    decode_cmd.add_argument("--container-force")
    decode_cmd.add_argument("--allow-parity-absent", action="store_true")
    decode_cmd.add_argument("--json", action="store_true")

    atom = sub.add_parser("atom", help="resolve one atom or composition name")
    atom.add_argument("edition")
    atom.add_argument("name")
    atom.add_argument("--json", action="store_true")

    compare_cmd = sub.add_parser("compare", help="compare independent and production decoders")
    compare_cmd.add_argument("edition")
    compare_cmd.add_argument("--profile", required=True)
    compare_cmd.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    try:
        if args.command == "verify":
            code = selftest(args.edition)
            if args.json:
                _json_or_print({"command": "verify", "status": "PASS" if code == 0 else "FAIL"}, True)
            return code
        if args.command == "decode":
            g = Grimoire(args.edition)
            px = parse_hexrun(args.run)
            bad = conform(px, g, container_evidence=args.container_evidence,
                           container_force=args.container_force)
            result = report(px, g, frame_id=args.frame_id,
                            container_evidence=args.container_evidence,
                            container_force=args.container_force)
            _json_or_print(result, args.json)
            return 1 if bad else 0
        if args.command == "atom":
            g = Grimoire(args.edition)
            if args.name.isdigit():
                address = int(args.name)
                result = {"name": args.name, "address": address,
                          "spelling": g.atoms[address][0], "gloss": g.atoms[address][1]}
            elif args.name in g.lexicon:
                result = {"name": args.name, "addresses": g.lexicon[args.name],
                          "spelling": g.spell(g.lexicon[args.name]),
                          "canonical": g.name_of(g.lexicon[args.name])}
            else:
                raise ValueError("unknown atom or composition %r" % args.name)
            _json_or_print(result, args.json)
            return 0
        result = compare(args.edition, args.profile)
        _json_or_print(result, args.json)
        return 0 if result["status"] == "PASS" else 1
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
