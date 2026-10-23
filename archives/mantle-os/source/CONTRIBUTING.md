# Contributing to Mantle OS

Thanks for your interest in Mantle OS. This project is published as an open demonstration of an
alternative coding structure, and contributions — from typo fixes to deep critiques of the
architecture — are welcome.

## Ways to contribute

- **Ask questions or discuss the ideas.** Open an issue. "Why is it built this way?" is a valid
  issue. The philosophy is meant to be examined.
- **Report problems.** If something in the `examples/vcw/` substrate doesn't run, or a document
  contradicts the code, open an issue describing what you expected and what happened.
- **Improve the docs.** Clarity fixes, examples, and diagrams are valuable.
- **Extend the substrate.** New organs, drivers, or examples that respect the framework's rules.

## Ground rules for code changes

Mantle has a small number of load-bearing principles. Changes should respect them:

1. **Body before brain.** Anything that *can* be a deterministic reflex *must* be a reflex, living
   in the Body. The MIND (LLM) is for judgment and voice — never for plumbing.
2. **The cube is the single source of truth.** Durable state lives in the VCW cube, addressed
   through bands. No hidden parallel stores or shared globals.
3. **Memory is append-only.** Never rewrite the past — append, tombstone (retire), or quarantine
   (isolate).
4. **Everything is provable.** Every organ carries audit obligations. If you add an organ or
   reflex, state how the Stage 1 / Stage 2 audit checks it.
5. **Fail open, never fail silent.** Instrumentation must not crash the host, but it must not hide
   a problem either.

## Before you open a pull request

- Install the package editable (it lives under `src/`, src-layout) so `mantle` is importable,
  then run the gates:

  ```bash
  pip install -e ".[spore,multilang]"
  python -m mantle check --strict  # closed-world certification; skips fail
  ```

  (`check` runs the Stage-1 gate, the three tamper proofs, the current invariant suite, the Stage-2
  gate, both demos, the assimilation dry-run, the standalone cube codec conformance, the
  SPORE purity gates, and the parity test — the same sequence CI runs.)

  A plain `check` may produce a partial diagnostic when prerequisites are missing.
  `check --fast` deliberately omits narrated rows and is never a certification. CI and
  certification claims always use the full `--strict` profile: top-level skips, internal
  unittest skips, and required `N/A` rows fail closed.

- If a doctrine-critical guard changes, run `python tools/mutate.py`. The targeted
  catalogue weakens security checks in isolated source copies and requires the named
  live invariant to kill every mutant. A survivor blocks CI.

- For performance work, use the bounded harness described in
  [`documents/guides/Certification_Performance.md`](documents/guides/Certification_Performance.md).
  Benchmark records are measurements only; they never replace strict certification.

- For clean-room reproduction and the evidence bundle CI retains, follow
  [`REPRODUCE.md`](REPRODUCE.md).

- Make sure `python -m mantle audit` still reports the **Stage 1 gate passed** (no open hard-fails).
- Keep Phase 1 brain-free: Phase-1 organs must not depend on an LLM to function.

## Style

- Match the existing code style in `examples/vcw/`.
- Keep documents in the established voice and reading order. If you add a document, link it from
  the README and the Primer's document set.
- **Where documents live:** `documents/` is the single documentation root — the corpus, plus
  the `documents/mantle2/` release-closure records (`MANTLE2_*`, written by
  `tools/build_mantle2_matrix.py` and read by the invariant suite — do not move or rename them).
  Never create a new documentation root (`doc/`, `docs/`, `document/`, `documentation/`, ...);
  add to `documents/` instead.

## License

By contributing, you agree that your contributions will be licensed under the project's
[MIT License](LICENSE).
