#!/usr/bin/env python3
"""
demo.py  --  semantic memory on the VCW (one-step thought-and-storage encoding)

A live walkthrough of the `grimoire-v0.10-entry` driver on a semantic-genome cube:
a MIND reflection is appended as ONE entry and the append itself encodes a Grimoire
v0.10 statement (record kind, author, time, evidence, force, parity) plus a content
QUOTE frame. The same entry guarantees as `log-json` hold on the semantic band:
ids, veil, immune marks, graded memory, multi-layer reads, and metabolism.

Run:  PYTHONPATH=src python examples/semantic_memory/demo.py
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from mantle.vcw.bands import semantic_genome
from mantle.vcw.cube import Cube
from mantle.vcw.entry import make_entry
from mantle.vcw.grimoire_editions import v010


def main() -> int:
    cube = Cube.genesis(semantic_genome(), generation=0)

    # --- the one step: think -> entry -> append -> v0.10 statement -> PNG layer ---
    entry = make_entry({"reflection": "The body grows memory; the mind extends it."},
                       opcode="THINK", author="MIND", verified=False,
                       confidence="inferred")
    cube.append("thoughts", entry)
    record = cube.read("thoughts", reveal_private=True)[0]

    print("one-step write: entry -> semantic record (id=%s %s)" % (record["id"],
                                                                  record["opcode"]))
    print("  semantic.raw       = %s" % record["semantic"]["raw"])
    print("  content QUOTE frame= %s" % record["semantic"]["content_raw"])
    print("  evidence=%s force=%s composition=%s parity=%s" % (
        record["semantic"]["evidence"], record["semantic"]["force"],
        record["semantic"]["composition"], record["semantic"]["parity_status"]))

    # the raw run is a real v0.10 statement -- decode it back with the edition decoder
    stmt = v010.decode_statement(record["semantic"]["raw"], profile="grimoire-v0.10",
                                 frame_id="demo")
    groups = ["%s:%s" % (g["role"], ",".join("%02x" % a["r"] for a in g["atoms"]))
              for g in stmt["groups"]]
    print("  decoded groups     = %s" % ", ".join(groups))

    # --- the veil: thoughts is private ---
    print("  veil: read without reveal = %r" % (cube.read("thoughts"),))

    # --- content rides QUOTE frames, byte-exact ---
    bytes_back = v010.decode_quoted_bytes(record["semantic"]["content_raw"],
                                          frame_id="demo-content")
    print("  content round-trip = %r" % json.loads(bytes_back.decode("utf-8")))

    # --- immune marks + graded memory ---
    cube.append("thoughts", make_entry({"reflection": "second reflection"},
                                       opcode="THINK", author="MIND",
                                       verified=False, confidence="inferred"))
    cube.deweight("thoughts", 0, weight=0.0)
    print("  after deweight(0): visible ids = %s, ghosts = %s" % (
        [e["id"] for e in cube.read("thoughts", reveal_private=True)],
        [e["id"] for e in cube.read("thoughts", reveal_private=True, ghosts=True)]))

    # --- durability: save/load round trip, hashes intact ---
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "gen0.vcw")
        cube.save(path)
        loaded = Cube.load(path)
        problems = loaded.verify()
        print("  save/load verify   = %s (%d records reloaded)" % (
            "CLEAN" if not problems else problems,
            len(loaded.read("thoughts", reveal_private=True))))
    print("\nALL DEMO CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
