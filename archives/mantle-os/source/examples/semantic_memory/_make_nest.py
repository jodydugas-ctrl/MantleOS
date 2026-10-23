#!/usr/bin/env python3
"""Throwaway: write a semantic-genome organism nest for doctor/certify (deleted after)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from mantle import Organism
from mantle.primer import appai_truths, appai_commandments
from mantle.vcw.bands import semantic_genome

nest = sys.argv[1]
org = Organism.birth(identity={"name": "SemanticDemo"},
                     truths=appai_truths(), commandments=appai_commandments(),
                     genome=semantic_genome())
org.prime.append("thoughts", {"opcode": "THINK", "author": "MIND",
                              "content": {"reflection": "hello"},
                              "verified": False, "confidence": "inferred"})
org.save(nest)
print("nest written to", nest)
