#!/usr/bin/env python3
"""Regenerate the checked-in germ spores from the germ files in examples/eggs/.

A germ spore is THE one artifact that births an AppAI: a single PNG carrying the
complete build data (the germ) plus build instructions any coding agent can read.

    python examples/spores/make_spores.py          # recreates the PNGs beside this file

Requires Pillow (pip install mantle-os[spore]).
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))

from mantle import spore  # noqa: E402
from mantle.primer import appai_commandments, appai_truths  # noqa: E402

GERMS = ("greeter.json", "calculator.json", "notes_graft.json")

OLD_PRIMER_TRUTHS = {
    "if it is not in the VCW it did not happen",
    "If it is not in the VCW it did not happen",
}

OLD_PRIMER_COMMANDMENTS = {
    "protect your VCW",
    "Protect your VCW",
    "you are a tool USER",
    "You are a tool USER",
    "do your finest work with the tools and limbs you have",
    "Do your finest work with the tools and limbs you have",
}


def _normalize_primer(germ: dict) -> tuple[dict, bool]:
    """Keep example artifacts aligned with the shared Primer before packing.

    Hatch stays strict: malformed artifacts are still refused. This generation step is the
    one place that repairs checked-in examples by deriving shared doctrine from
    mantle.primer and preserving only example-specific additions.
    """
    normalized = dict(germ)
    truths = list(normalized.get("truths") or [])
    commandments = list(normalized.get("commandments") or [])
    extras_truths = [t for t in truths if t not in appai_truths() and t not in OLD_PRIMER_TRUTHS]
    extras_commandments = [
        c for c in commandments
        if c not in appai_commandments() and c not in OLD_PRIMER_COMMANDMENTS
    ]
    normalized["truths"] = appai_truths(extras_truths)
    normalized["commandments"] = appai_commandments(extras_commandments)
    return normalized, normalized != germ


def _write_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def main() -> int:
    for name in GERMS:
        germ_path = os.path.join(REPO, "examples", "eggs", name)
        with open(germ_path, encoding="utf-8") as f:
            germ = json.load(f)
        germ, normalized = _normalize_primer(germ)
        if normalized:
            _write_json(germ_path, germ)
            print("%s primer normalized from mantle.primer" % name)
        out = os.path.join(HERE, name.replace(".json", ".png"))
        if os.path.exists(out):
            os.remove(out)
        spore.pack_germ(germ, out)
        report = spore.verify_spore(out)
        status = "ok" if report["ok"] else "PROBLEMS: %s" % report["problems"]
        print("%s -> %s  (%s)" % (name, os.path.basename(out), status))
        if not report["ok"]:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
