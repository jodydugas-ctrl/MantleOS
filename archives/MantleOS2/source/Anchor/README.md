# SCAN Anchor

This directory is the GitHub home for the independent SCAN evidence-first software reverse-engineering project. It is stored within MantleOS2 for a possible future integration, but is not part of the MantleOS2 package, release, default tests, or product CodeQL analysis. Integration must be explicit; repository placement alone does not admit scanner code into MantleOS2.

The public, versioned project documents live in [`docs/`](docs/). They are part of this repository and are the only documentation paths referenced by this README.

## Current checkpoint

- SCAN Engine: v0.27 tested calibration candidate; v0.26 remains the latest frozen release and v0.20 remains the immutable pre-oracle cold baseline
- Project documentation: v0.32 checkpoint (A1-A8 governing contract unchanged)
- Status: frozen pre-v1 candidate; calibration loop active, production certification pending
- PR5 NotepadNext calibration: v0.20 cold and v0.21-v0.26 sealed reruns mechanically PASS; calibration PARTIAL
- PR7 reconstruction proof: partial; M5 and M6A mechanisms pass, external-agent M6B remains open
- H-001 blind holdout: frozen and source-uninspected

## Documents

- [`docs/ANCHOR_CODING_PROMPT.md`](docs/ANCHOR_CODING_PROMPT.md) — governing A1-A8 architecture and evidence contract.
- [`docs/SCAN_PROTOCOL.md`](docs/SCAN_PROTOCOL.md) — operational scanning, certification, promotion, and reconstruction protocol.
- [`docs/SCAN_REPORT.md`](docs/SCAN_REPORT.md) — executed evidence, specimen findings, calibration history, and honest coverage state.
- [`docs/SCAN_CREATION_PLAN.md`](docs/SCAN_CREATION_PLAN.md) — engineering roadmap and PR1-PR8 certification ledger.
- [`evidence/pr5/PR5_ACQUISITION_RECEIPT.md`](evidence/pr5/PR5_ACQUISITION_RECEIPT.md) — exact pinned-source acquisition and archive digest evidence.
- [`evidence/pr5/PR5_EXECUTION_ARTIFACT_REQUIREMENTS.json`](evidence/pr5/PR5_EXECUTION_ARTIFACT_REQUIREMENTS.json) — authoritative v0.20 release hashes and cold-run admission policy.
- [`evidence/pr5/PR5_COLD_SCAN_RECEIPT.json`](evidence/pr5/PR5_COLD_SCAN_RECEIPT.json) — sealed cold-run identity, coverage, and bundle digests.
- [`evidence/pr5/PR5_CALIBRATION_REPORT.md`](evidence/pr5/PR5_CALIBRATION_REPORT.md) — post-seal machine-versus-oracle comparison and generic corrective backlog.
- [`engine/v0.26/`](engine/v0.26/) — exact frozen surface-denominator-corrected scanner source; this is not the NotepadNext specimen.
- [`engine/v0.27/`](engine/v0.27/) — tested generic Qt `QEvent::FileOpen` routing correction; it is a candidate awaiting final release certification.
- [`releases/v0.26/`](releases/v0.26/) — frozen v0.26 artifacts, deterministic/cache receipts, and completed PR5 certification/calibration evidence. The 277 MB sealed specimen bundle is kept out of Git and identified by SHA-256.

## Synchronization rules

1. Update the tracked documents in `docs/` as part of the corresponding implementation or release change.
2. Keep documentation links repository-relative and usable by every reader.
3. Keep aspirations in the creation plan and executed evidence in the report.
4. Do not promote `UNKNOWN`, `PARTIAL`, or `BLOCKED` findings into completed claims.
5. Do not alter A1-A8 merely to describe an implementation change.
6. Record only tests, scans, calibrations, and certifications that were actually executed.
