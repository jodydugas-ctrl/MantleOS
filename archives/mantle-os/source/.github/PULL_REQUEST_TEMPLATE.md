## What changed

<!-- One or two sentences. If this PR moves or renames files, include the old → new mapping. -->

## Verification

- [ ] `python -m mantle prove` — all invariants green
- [ ] `python tools/release_scan.py` — no secret-shaped strings
- [ ] `python tools/grimoire_tool.py verify documents/grimoire/editions/grimoire-v0.10.md` — if a Grimoire/edition file is touched

## Notes

- Documentation lives in `documents/` — the single doc root; `documents/mantle2/` holds the
  machine-referenced `MANTLE2_*` release records. Never create a new doc root.
- Small conventional commits only; no history rewrites, no force-pushes.
