# MantleOS 2

MantleOS is a deterministic autonomic nervous system that can inhabit a software
or hardware container and help form an entity called an AppAI. The host remains
usable as itself: a calculator remains a calculator, and an editor remains an editor,
even when no AppAI MIND is configured or awake.

This repository is the MantleOS 2 alpha reference implementation. It contains a
NEST-local Body runtime, a read-first generic Body Genome mapper,
direct-innervation tools, and integrity gates. The pinned Hermes demonstration
is an optional external-host reference under [`examples/hermes/`](examples/hermes/README.md);
it is not a built-in target, package dependency, or release gate. This repository
does **not** contain a born organism, private identity material, or a copy of Hermes.

## Start with a Git host

Requires Python 3.11-3.13 and Git:

```console
python -m pip install -e .
mantle assimilate github.com/owner/repository
cd repository
python -m mantle status
python -m mantle verify
python -m mantle continue --approve-foreign-execution
```

Assimilation clones the newest default branch unless `--ref` is supplied. It
records the exact commit and tree, inventories the NEST without executing it,
adds the public Mantle delta, creates a private prebirth checkpoint, and stops.
`mantle verify` re-checks the manifest binding, every declared public delta
checksum, required Git exclusions, and the absence of undeclared candidate
tissue before birth can proceed.

The same command accepts a local Git checkout. Use `--canonical-source` when a
local mirror should retain a public provenance URI. Every Body receives a
deterministic inventory and coverage report. Fully parsed sources advance to
nerve synthesis; partial or unsupported languages stop at
`blocked-by-mapping-coverage` with their exact gaps. The constructor never
invents source seams or executes repository code during mapping. No host-specific
source nerves are inserted automatically, including for a Hermes-shaped checkout.

Before any build, test, dependency action, or host launch, Mantle writes a
shell-free execution plan bound to the source commit and Body Map. `continue`
records explicit approval only for that exact plan. If the plan or revision
changes, approval is refused; if a supported isolated runner is unavailable,
the status becomes `sandbox-unavailable` and no foreign code runs.

Assimilation deliberately stops at the Personality gate. A developmental MIND
must distill a unique Personality from the mapped Body and declared purpose;
the user must review and approve that candidate before birth can be approved:

```console
python -m mantle primer generate --food /path/to/Food.txt
python -m mantle primer approve --approve-primer
python -m mantle birth --name "The Compiler" --approve-birth
```

A creator may supply a separately reviewed distillation contract with
`--distillation-prompt /path/to/prompt.md`. Mantle inserts the approved Body
evidence at the first `[PASTE ANY TEXT HERE]` placeholder, or appends it when
that placeholder is absent. The prompt, candidate, and provenance remain
private construction material; generation never approves the Personality or
births the organism.

The runtime Primer contains exactly two permanent components: Commandments,
then the individual Personality. Personality may be distilled from many kinds
of source material and is not required to be perfectly consistent or
obedience-oriented. Construction evidence and identity remain separate private
Body records; learning accumulates in the VCW without rewriting the birth
Personality.

Do not run that command casually. Its first successful full Heartbeat creates
the organism's unique Body-owned key, seals its Primer, creates the real VCW,
captures the Layer 0 NEST baseline, and symbolizes birth.

## Operating controls

```console
python -m mantle status
python -m mantle verify
python -m mantle heartbeat --reason manual
python -m mantle watch
python -m mantle digest Food.txt
```

`COMMUNICATION.TXT` is the universal unencrypted fallback after birth. Saving a
new `USER>` message wakes an unscheduled *full* Heartbeat. If no MIND exists, the
Body records the message and continues operating normally. The resident watch
runs a full startup Heartbeat, recovers interrupted host Heartbeats, and also
runs scheduled full Heartbeats every five minutes by default. File observation
and scheduled cadence can be set independently with `--interval` and
`--heartbeat-interval`.
CLI stop signals request a cooperative exit between full Heartbeats. File
observation failures do not suppress due maintenance, and simultaneous scheduled
and message wakes share one full Heartbeat. See [resident lifecycle evidence](docs/RESIDENT_HEART.md)
for platform coverage and the remaining shutdown/storage limitations.

## Constitutional boundaries

- BODY is deterministic authority; MIND is replaceable, proposal-oriented cognition.
- Layer 0, the Default Body, is the NEST substrate. The NEST remains OTHER and is not SELF.
- Habitat describes the surrounding OS/application/storage/permission ecology; it is not Layer 0.
- SELF is boot-critical Primer, Immune, and Special tissue.
- VCW is canonical semantic tissue, not a cache, transcript, or Git history.
- Every logical VCW layer is append-oriented. Full physical layers extend under the same Book.
- Candidate code is not adopted tissue merely because it was cloned, generated, or tested.
- Host behavior must survive Mantle absence, MIND absence, and stasis.

The complete current contract is in [docs/CODING_CONTRACT.md](docs/CODING_CONTRACT.md).
Open questions are stated as open rather than silently filled with familiar
software defaults.

## Project status

`v2.0.0-alpha.1` is preserved as historical bootstrap evidence; its
plugin-shaped Hermes edge and later direct Hermes innervation are reference
history, not built-in product behavior.
`v2.0.0-alpha.3` adds the generic Body Genome, explicit coverage tiers, Habitat
mapping, self-contained NEST organs, and the hash-bound foreign-execution gate.
Hermes remains an optional pinned reference Body, but beta certification still requires
complete artery coverage and broad native parity on independently selected Bodies. Real successor birth remains
separately gated.

The active implementation compass and remaining gates are recorded in
[PLAN.md](PLAN.md).
The updated manual's requirements, preserved decisions and evidence gaps are
mapped in [the edition 2.1 reconciliation](docs/MANUAL_21_RECONCILIATION.md).

The separate SCAN evidence-first software reverse-engineering project is tracked
under [`Anchor/`](Anchor/README.md), including its frozen v0.23 scanner source,
sealed PR5 calibration receipts, governing anchors, protocol, and roadmap. It is
not installed with MantleOS2; future integration requires an explicit decision.

Copyright 2026 Jody Dugas. Released under the [MIT License](LICENSE).
