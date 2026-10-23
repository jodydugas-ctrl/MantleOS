"""Profile-neutral Anchor *shape* checker; never executes Anchor behavior.

An Anchor's serialized slots and candidate stage skeleton are shared for all
three polarities. Opcode meanings and stage mechanics belong to a specific
self-contained Blueprint primer, not this validator.
"""
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

from mantleos.anchors import TYPES, definition
FIELDS = ("id", "type", "opcode", "mass", "variable")
# Experimental 3-stage execution *candidate*, deliberately not a runtime.
CANDIDATE_STAGES = ("REACH", "QUALIFY", "ROUTE")
ENTRY = re.compile(
    r"(?P<id>[A-Za-z][A-Za-z0-9_-]*): "
    r"(?P<type>BlackHole|WhiteHole|Neutral) "
    r"-(?P<opcode>[0-9A-F]{2}) -(?P<mass>[0-9A-F]{2}) "
    r"-(?P<variable>[A-Za-z_][A-Za-z0-9_]*(?:=.+)?)\Z"
)
MOLECULE_START = re.compile(r"BEGIN MOLECULE [A-Za-z][A-Za-z0-9_]*\Z")


class StructureError(ValueError):
    """A malformed Anchor or nonuniform structural record."""


@dataclass(frozen=True)
class AnchorShape:
    id: str
    type: str
    opcode: str
    mass: str
    variable: str

    @property
    def singularity(self):
        return definition(self.type).singularity

    @property
    def attributes(self):
        return {'opcode': self.opcode, 'mass': self.mass, 'variable': self.variable}

    @property
    def stages(self) -> tuple[str, ...]:
        """Same provisional stage skeleton regardless of polarity."""
        return CANDIDATE_STAGES


def parse_entry(line: str) -> AnchorShape:
    match = ENTRY.fullmatch(line)
    if match is None:
        raise StructureError(f"Invalid universal Anchor shape: {line!r}")
    return AnchorShape(**match.groupdict())


def extract_entries(source: str) -> list[str]:
    """Extract only Molecule entries from a Blueprint, or raw fixture lines.

    Full Blueprint parsing and execution are intentionally handled by each
    profile runtime. This tool validates only serialized Anchor shapes.
    """
    lines = source.splitlines()
    if any(MOLECULE_START.fullmatch(line) for line in lines):
        entries: list[str] = []
        in_molecule = False
        seen_molecule = False
        for line in lines:
            if MOLECULE_START.fullmatch(line):
                if in_molecule:
                    raise StructureError("Nested Molecule")
                in_molecule = True
                seen_molecule = True
            elif line == "END MOLECULE":
                if not in_molecule:
                    raise StructureError("Unpaired END MOLECULE")
                in_molecule = False
            elif in_molecule and line.strip():
                entries.append(line)
        if in_molecule or not seen_molecule:
            raise StructureError("Unclosed Molecule")
        return entries
    # Simple fixture input without a Blueprint wrapper.
    return [line for line in lines if line.strip() and not line.startswith("#")]


def check_structures(source: str, *, all_types: bool = False) -> list[AnchorShape]:
    lines = extract_entries(source)
    if not lines:
        raise StructureError("No Anchor entries")
    anchors = [parse_entry(line) for line in lines]
    ids = [a.id for a in anchors]
    if len(set(ids)) != len(ids):
        raise StructureError("Duplicate Anchor ID")
    if all_types and set(a.type for a in anchors) != set(TYPES):
        raise StructureError("Family example must contain all three Anchor types")
    # Since only *one* AnchorShape and stage tuple exist, polarity-specific
    # structure changes cannot pass through this parser unchecked.
    if any(tuple(vars(a)) != FIELDS or a.stages != CANDIDATE_STAGES for a in anchors):
        raise StructureError("Anchor shape or candidate stage skeleton not uniform")
    return anchors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate universal Anchor shape (not execution)")
    parser.add_argument("file", type=Path)
    parser.add_argument("--all-types", action="store_true", help="Require all three polarities in fixture")
    args = parser.parse_args(argv)
    try:
        anchors = check_structures(args.file.read_text(encoding="utf-8"), all_types=args.all_types)
    except (OSError, StructureError) as exc:
        parser.exit(1, f"FAIL: {exc}\n")
    print(f"PASS: {len(anchors)} Anchor(s), shared slots {','.join(FIELDS)}; "
          "shape only, no execution verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
