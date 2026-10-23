"""Write a proposal for operator review; do not admit it automatically."""
import argparse
import json
from pathlib import Path

from mantleos import evolution, organism

parser = argparse.ArgumentParser()
parser.add_argument("body")
parser.add_argument("output")
args = parser.parse_args()
proposal = evolution.propose(args.body, organism.notebook_tissue("Ready to remember and reconsider."))
with Path(args.output).open("x", encoding="utf-8") as output:
    json.dump(proposal, output, indent=2)
    output.write("\n")
print("Review the proposal. Admission requires its exact digest:", proposal["sha256"])
