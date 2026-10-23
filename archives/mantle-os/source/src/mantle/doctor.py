#!/usr/bin/env python3
"""
mantle.doctor  --  a deployment checkup (Mantle OS · §3)

Most real-world breakage in a living organism is not a logic bug -- it is a STALE VIEW: a
truncated write, a split copy on two drives, docs that drifted from the code. The doctor is
a deterministic health check that catches those before they bite:

  cube-verify           the Prime cube hashes/coheres (no silent corruption)
  ancestor-seals        every sealed ancestor still matches its fingerprint
  genesis-key           the SELF key still matches its recorded fingerprint (M2)
  ledger-nonnegative    the symbiosis ledger never went negative (the starvation law)
  docs-vs-code          no doc hardcodes an invariant count (the count is derived from the
                        code -- `mantle prove` prints it -- so prose can never drift stale);
                        docs-vs-code-organs ties the README's organ count to ORGAN_ORDER
  legacy-egg-imports    no Python source imports the removed mantle.egg module; germ
                        loading and validation live in mantle.hatchery
  threat-model-codes    the delimited security guarantee table has unique stable IDs;
                        every cited proof is live; enforced/detected rows cite proof

`checkup(org, repo_root=...)` returns {ok, checks:[...]}; `ok` is False if any check fails.
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional


_NUMBER_WORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
                 "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12}


def _docs_vs_code(repo_root: str) -> Dict[str, Any]:
    """The coherence gate, inverted: NO doc may hardcode an invariant count. The live
    count comes from the code (`python -m mantle prove` prints it); a number written
    into prose goes stale the moment an invariant is added, so its presence IS the
    failure. Scans README.md and every markdown file under documents/."""
    pattern = re.compile(r"\b\d+(?:/\d+)?\s+(?:security\s+|executable\s+)?invariants\b",
                         re.IGNORECASE)
    offenders: List[str] = []
    targets = [os.path.join(repo_root, "README.md")]
    docs_dir = os.path.join(repo_root, "documents")
    if os.path.isdir(docs_dir):
        for base, _dirs, files in os.walk(docs_dir):
            targets.extend(os.path.join(base, f) for f in files if f.endswith(".md"))
    if not os.path.isfile(targets[0]):
        return {"check": "docs-vs-code", "ok": False, "detail": "README.md not found"}
    for path in targets:
        try:
            with open(path, encoding="utf-8") as f:
                if pattern.search(f.read()):
                    offenders.append(os.path.relpath(path, repo_root))
        except OSError:
            continue
    return {"check": "docs-vs-code", "ok": not offenders,
            "detail": ("no hardcoded invariant counts (the count is derived: mantle prove)"
                       if not offenders else
                       "hardcoded invariant count in: %s" % ", ".join(offenders[:5]))}


def _docs_vs_code_organs(repo_root: str) -> Dict[str, Any]:
    """The same coherence gate for the organ count: the README's "<N> deterministic
    organs" claim must equal len(ORGAN_ORDER). Added after the ninth-organ molt left
    stale "eight organs" prose behind -- this class of drift is now caught mechanically."""
    from .core.organism import ORGAN_ORDER
    actual = len(ORGAN_ORDER)
    try:
        with open(os.path.join(repo_root, "README.md"), encoding="utf-8") as f:
            m = re.search(r"(\w+)\s+deterministic organs", f.read(), re.IGNORECASE)
    except OSError:
        return {"check": "docs-vs-code-organs", "ok": False, "detail": "README.md not found"}
    word = m.group(1).lower() if m else None
    claimed = _NUMBER_WORDS.get(word, int(word) if word and word.isdigit() else None)
    return {"check": "docs-vs-code-organs", "ok": claimed == actual,
            "detail": "README claims %s organs; ORGAN_ORDER has %d" % (claimed, actual)}


def _legacy_egg_imports(repo_root: str) -> Dict[str, Any]:
    """Reject imports of the removed ``mantle.egg`` module.

    The egg implementation was consolidated into ``mantle.hatchery``. Parse Python
    sources rather than searching text so historical prose and schema names do not
    trigger false positives.
    """
    import ast

    ignored_dirs = {".git", ".venv", "__pycache__", "build", "dist", "node_modules"}
    offenders: List[str] = []
    for base, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
        for filename in files:
            if not filename.endswith(".py"):
                continue
            path = os.path.join(base, filename)
            rel = os.path.relpath(path, repo_root)
            try:
                with open(path, encoding="utf-8") as f:
                    tree = ast.parse(f.read(), filename=rel)
            except (OSError, SyntaxError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    if any(alias.name == "mantle.egg"
                           or alias.name.startswith("mantle.egg.")
                           for alias in node.names):
                        offenders.append(rel)
                        break
                if not isinstance(node, ast.ImportFrom):
                    continue
                module = node.module or ""
                absolute_legacy = (
                    module == "mantle.egg"
                    or module.startswith("mantle.egg.")
                    or (module == "mantle" and any(alias.name == "egg"
                                                   for alias in node.names))
                )
                relative_legacy = (
                    node.level > 0
                    and rel.replace(os.sep, "/").startswith("src/mantle/")
                    and (module == "egg"
                         or module.startswith("egg.")
                         or (not module and any(alias.name == "egg"
                                                for alias in node.names)))
                )
                if absolute_legacy or relative_legacy:
                    offenders.append(rel)
                    break
    offenders = sorted(set(offenders))
    return {
        "check": "legacy-egg-imports",
        "ok": not offenders,
        "detail": (
            "no Python source imports removed mantle.egg"
            if not offenders
            else "removed mantle.egg imported by: %s" % ", ".join(offenders[:5])
        ),
    }


_GUARANTEE_START = "<!-- MANTLE-GUARANTEES:START -->"
_GUARANTEE_END = "<!-- MANTLE-GUARANTEES:END -->"
_PROVED_VERDICTS = {"enforced", "detected"}
_ALL_VERDICTS = _PROVED_VERDICTS | {"conventional", "out of scope"}


def _live_invariant_codes() -> set:
    """Return the proof codes published by the live invariant registry."""
    from .audits.invariants import REGISTRY
    return {spec.code for spec in REGISTRY}


def _threat_model_guarantees(repo_root: str) -> Dict[str, Any]:
    """Validate only the explicitly delimited guarantee table.

    This is a drift check, not a semantic theorem: it proves stable IDs, verdict syntax,
    and live proof references. Human review still decides whether a proof supports the
    claim beside it.
    """
    path = os.path.join(repo_root, "THREAT_MODEL.md")
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError as exc:
        return {"check": "threat-model-codes", "ok": False,
                "detail": "THREAT_MODEL.md unavailable: %s" % exc}
    if text.count(_GUARANTEE_START) != 1 or text.count(_GUARANTEE_END) != 1:
        return {"check": "threat-model-codes", "ok": False,
                "detail": "guarantee table delimiters missing or duplicated"}
    body = text.split(_GUARANTEE_START, 1)[1].split(_GUARANTEE_END, 1)[0]
    live = _live_invariant_codes()
    code_re = re.compile(r"`([A-Z][A-Z0-9]*(?:-[A-Za-z0-9]+)+)`")
    ids: List[str] = []
    unknown: List[str] = []
    unbacked: List[str] = []
    bad_verdicts: List[str] = []
    for line in body.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 6 or not cells[0].startswith("`TM-"):
            continue
        guarantee_id = cells[0].strip("`")
        verdict = cells[3].strip("`").lower()
        cited = code_re.findall(cells[4])
        ids.append(guarantee_id)
        if verdict not in _ALL_VERDICTS:
            bad_verdicts.append("%s=%s" % (guarantee_id, verdict))
        if verdict in _PROVED_VERDICTS and not cited:
            unbacked.append(guarantee_id)
        unknown.extend(code for code in cited if code not in live)
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    problems = []
    if not ids:
        problems.append("no guarantee rows parsed")
    if duplicates:
        problems.append("duplicate guarantee ID(s): %s" % ", ".join(duplicates))
    if unknown:
        problems.append("unknown proof code(s): %s" % ", ".join(sorted(set(unknown))))
    if unbacked:
        problems.append("unbacked enforced/detected row(s): %s" % ", ".join(unbacked))
    if bad_verdicts:
        problems.append("invalid verdict(s): %s" % ", ".join(bad_verdicts))
    # A real repository check also proves that every executable invariant maps to a
    # declared guarantee row. Tiny synthetic tables used by unit probes remain isolated.
    if os.path.isfile(os.path.join(repo_root, "README.md")):
        from .audits.invariants import REGISTRY
        missing_guarantees = sorted({
            spec.guarantee_id for spec in REGISTRY if spec.guarantee_id not in ids
        })
        if missing_guarantees:
            problems.append("registry maps to unknown guarantee ID(s): %s"
                            % ", ".join(missing_guarantees))
    return {"check": "threat-model-codes", "ok": not problems,
            "detail": ("guarantee IDs unique; cited proofs live; registry mapped"
                       if not problems else " | ".join(problems))}


def checkup(org: Any, repo_root: Optional[str] = None) -> Dict[str, Any]:
    """Run the deployment checkup. Pass `repo_root` to include the docs-vs-code gate."""
    checks: List[Dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    problems = org.prime.verify()
    add("cube-verify", problems == [], "" if not problems else "; ".join(problems[:2]))
    seal_issues = [p for c in org.ancestral for p in c.verify_seal()]
    add("ancestor-seals", not seal_issues, "; ".join(seal_issues[:2]))
    if org.body.has_key:
        add("genesis-key", org.body.key_fingerprint_consistent(),
            "" if org.body.key_fingerprint_consistent() else "key fingerprint mismatch")
    from .symbiosis import BAND, balance
    if BAND in org.prime.bands:
        add("ledger-nonnegative", balance(org) >= 0, "balance=%.2f" % balance(org))
    if repo_root:
        checks.append(_docs_vs_code(repo_root))
        checks.append(_docs_vs_code_organs(repo_root))
        checks.append(_legacy_egg_imports(repo_root))
        checks.append(_threat_model_guarantees(repo_root))

    return {"ok": all(c["ok"] for c in checks), "checks": checks}
