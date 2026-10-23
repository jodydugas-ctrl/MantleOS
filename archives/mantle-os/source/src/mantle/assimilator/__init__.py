"""mantle.assimilator -- Path B: grow organs around existing code, non-destructively.

The prime directive: DO NO HARM. Dissect read-only (scanner), map host tissue to organs
(organ_map), produce the signed Phase-0 artifacts (report), and only then thread host
behavior through the organism with fail-open, reversible wrappers (wrappers). The host
runs exactly as before -- plus now it has a nervous system and a memory.
"""
from .scanner import scan_project, scan_file, classify_symbol, ROLES
from .organ_map import build_map, propose_genome, ROLE_TO_ORGAN, ORGANS
from .evidence import build_host_evidence_index, answer_from_host_evidence
from .surface_coverage import build_surface_coverage, render_surface_coverage_markdown
from .wrappers import Assimilation
from .report import dry_run, render_inventory, write_artifacts, emit_spore

__all__ = ["scan_project", "scan_file", "classify_symbol", "ROLES",
           "build_map", "propose_genome", "ROLE_TO_ORGAN", "ORGANS",
           "build_host_evidence_index", "answer_from_host_evidence",
           "build_surface_coverage", "render_surface_coverage_markdown",
           "Assimilation", "dry_run", "render_inventory", "write_artifacts",
           "emit_spore"]

# scanner_ts is intentionally not imported here: it depends on the optional
# tree-sitter stack and is reached via mantle.assimilator.scanner_ts directly.
