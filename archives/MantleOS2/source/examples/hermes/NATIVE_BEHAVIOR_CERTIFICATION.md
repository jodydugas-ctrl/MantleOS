# Native Hermes Behavior Certification

The focused native-behavior gate compares the exact same upstream Hermes tests
at commit `63279301bcbdc185c1b07b98a9312eb0c862f26d` in two checkouts:

1. pristine upstream Hermes, without Mantle tissue; and
2. the constructed MantleOS 2 candidate, with eight direct source Nerves and
   public Mantle tissue present but no organism birth.

The suite covers the mapped conversation, user-turn, MIND-finalization,
tool-authority, tool-completion, terminal session, and gateway session seams.
It uses no provider credential, makes no live MIND call, installs no resident
Heart, and performs no birth.

## Recorded local result

On 2026-09-03, using Python 3.12.14 on Windows:

- pristine checkout: **85 passed**;
- constructed checkout: **85 passed**.

Both checkouts resolved to the certified commit. The constructed checkout
remained `constructed-not-born`. This establishes behavioral equivalence for
the focused mapped seams; it is not a claim that every optional Hermes feature
or provider has been exercised.

GitHub's `Hermes assimilation` workflow can reproduce this comparison by
manual dispatch; it does not execute the example on normal PRs or releases.
The test selection and minimal upstream-pinned test
dependencies are versioned beside the Hermes seed.
