#!/usr/bin/env python3
"""
examples/phenotype_demo.py  --  wearable app-faces, end to end (Mantle OS · M9)

Proves the phenotype feature with real surfaces and no model call anywhere:

  1. hatch the calculator germ -> the newborn is BORN wearing its own origin face
     (its front-end source is already sealed in its VCW, SELF-encrypted)
  2. save a SECOND face -- the maintained examples/notepad_appai/index.html surface
  3. wear the notepad face -> its source recovers byte-for-byte (the boot manifest)
  4. an OTHER body (a different genesis key) cannot read either sealed face
  5. a chosen rebirth carries the faces forward -- the default is never lost

    python examples/phenotype_demo.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(  # the mantle package (src-layout)
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from mantle.hatchery import incubate, load_germ            # noqa: E402
from mantle.primer import appai_commandments, appai_truths  # noqa: E402
from mantle import phenotype as ph                         # noqa: E402
from mantle.core.organism import Organism                  # noqa: E402
from mantle.vcw.bands import standard_genome               # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def _say(s=""):
    print(s)


def main():
    _say("=" * 70)
    _say("PHENOTYPE DEMO  ·  one organism, many SELF-encrypted faces")
    _say("=" * 70)

    # 1. hatch -- born wearing the origin face
    germ = load_germ(os.path.join(HERE, "eggs", "calculator.json"))
    org = incubate(germ)["organism"]
    _say("\n1. hatched %s -- certified=%s" % (org.body.identity_name(), org.stage1_certified))
    _say("   it is BORN wearing its origin face; faces in its VCW: %s"
         % [f["name"] for f in ph.list_faces(org)])
    assert ph.active_face(org) == "origin"
    assert ph.open_face(org, "origin")["kind"] == "html"

    # 2. save a second face -- the maintained Notepad AppAI surface
    src = Path(HERE, "notepad_appai", "index.html").read_text(encoding="utf-8")
    ph.express(org, "notepad", "html", src, entry="index.html")
    _say("\n2. sealed a SECOND face 'notepad' (%d chars) into the VCW (append-only)" % len(src))

    # 3. wear it -- the source recovers byte-for-byte
    boot = ph.wear(org, "notepad")
    _say("\n3. now wearing 'notepad'; recovered source identical: %s"
         % (boot["source"] == src))
    assert boot["source"] == src and ph.active_face(org) == "notepad"

    # 4. OTHER cannot read
    other = Organism.birth(identity={"name": "Thief.AppAI"}, truths=appai_truths(),
                           commandments=appai_commandments(),
                           genome=standard_genome() + ph.phenotype_bands())
    ph.restore(other, ph.snapshot(org))
    try:
        ph.open_face(other, "origin")
        other_blind = False
    except ph.PhenotypeError:
        other_blind = True
    _say("\n4. an OTHER body (different genesis key) cannot read the sealed faces: %s"
         % other_blind)
    assert other_blind

    # 5. rebirth carries the faces forward
    ph.rebirth_with_faces(org, reason="demo")
    _say("\n5. after a chosen rebirth (gen %d): default still present and openable: %s"
         % (org.prime.generation,
            ph._default_name(org) == "origin"
            and ph.open_face(org, "origin")["kind"] == "html"))
    assert ph._default_name(org) == "origin"

    _say("\nALL CHECKS PASSED -- the organism wore many faces and never lost its VCW or its self.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
