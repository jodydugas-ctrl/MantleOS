"""Bounded AC-STRUCT-001 syntax evidence; no profile dispatch or execution."""
from ..anchor_language import verify_source_pins
from ..anchor_engine.tools import anchor_structure as shape
from .adapters import Builder, MAX_RECORDS
from .common import ScanError, digest, sha

MAX_SOURCE_BYTES = 2_000_000
MAX_LINE_CHARS = 16_384
MAX_CONTEXT_SPANS = 100


def extract_anchor(path, data):
    if len(data) > MAX_SOURCE_BYTES:
        raise ScanError("Anchor source byte budget exceeded")
    verify_source_pins()
    text = data.decode("utf-8-sig")
    lines = text.splitlines()
    if len(lines) > MAX_RECORDS * 2:
        raise ScanError("Anchor source line budget exceeded")
    wrapped = any(shape.MOLECULE_START.fullmatch(line) for line in lines)
    builder = Builder(path, sha(data))
    builder.nodes[0]["end_line"] = max(1, len(lines))
    molecule = None
    molecule_index = None
    molecule_names = set()
    context = []
    context_count = 0
    context_span_count = 0
    last_context = None
    for number, line in enumerate(lines, 1):
        if len(line) > MAX_LINE_CHARS:
            raise ScanError(f"Anchor line budget exceeded at line {number}")
        if line.startswith("BEGIN MOLECULE"):
            if not shape.MOLECULE_START.fullmatch(line):
                raise ScanError(f"Malformed Molecule header at line {number}")
            if molecule is not None:
                raise ScanError(f"Nested Molecule at line {number}")
            name = line.removeprefix("BEGIN MOLECULE ")
            if name in molecule_names:
                raise ScanError(f"Duplicate Molecule name at line {number}")
            molecule_names.add(name)
            molecule = builder.add("anchor_molecule", name, number, number,
                                   builder.module, 0, molecule_name=name)
            molecule_index = len(builder.nodes) - 1
        elif line.startswith("END MOLECULE"):
            if line != "END MOLECULE" or molecule is None:
                raise ScanError(f"Unpaired or malformed END MOLECULE at line {number}")
            builder.nodes[molecule_index]["end_line"] = number
            entries = [node["syntax_sha256"] for node in builder.nodes[molecule_index + 1:] if node["owner"] == molecule]
            builder.nodes[molecule_index].update(syntax_sha256=digest(entries), relocation_sha256=digest(entries))
            molecule = None
        elif line.strip() and (molecule is not None or not wrapped and not line.startswith("#")):
            match = shape.ENTRY.fullmatch(line)
            if match is None:
                raise ScanError(f"Invalid universal Anchor shape at line {number}")
            fields = match.groupdict()
            syntax = digest(fields)
            relocation = digest({key: value for key, value in fields.items() if key != "id"})
            builder.add("anchor", fields["id"], number, number,
                        molecule or builder.module, 0, anchor_id=fields["id"],
                        syntax_sha256=syntax, relocation_sha256=relocation,
                        polarity=fields["type"], opcode_hex=fields["opcode"],
                        mass_hex=fields["mass"], variable=fields["variable"],
                        semantics="UNKNOWN")
        elif line.strip() and not line.startswith("#"):
            context_count += 1
            if last_context is not None and last_context["end_line"] == number - 1:
                last_context["end_line"] = number
            else:
                context_span_count += 1
                last_context = {"line": number, "end_line": number}
                if len(context) < MAX_CONTEXT_SPANS:
                    context.append(last_context)
    if molecule is not None:
        raise ScanError("Unclosed Molecule")
    # The pinned profile-neutral oracle owns shape and duplicate-ID validation.
    shape.check_structures(text)
    builder.nodes[0]["attributes"] = {"unparsed_context_spans": context,
                                       "unparsed_context_lines": context_count,
                                       "context_spans_truncated": context_span_count > len(context)}
    gaps = ["Anchor shape only; opcode, mass and variable semantics are UNKNOWN. "
            "No profile qualification, runtime routing or REACH/QUALIFY/ROUTE execution is inferred."]
    if context_count:
        gaps.append(f"{context_count} contextual lines outside Molecules have no verified grammar in this adapter; "
                    "bounded source spans are recorded on the module node.")
    return builder.result("anchor", gaps)
