# Verification

Run focused tests, then from the extracted root:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -q
python -m kpp doctor
python examples/adaptive-reflex/smoke.py
python tools/verify_release.py
```

Restricted hosts need writable TEMP/TMP and permitted loopback for HTTP tests. Symlink creation checks explicitly skip if privilege is unavailable; report skips. Do not turn blocked checks into passes.

validate_release.py --json-out OUTSIDE_SOURCE.json records actual outcomes/counts/environment. Optional --browser runs all four real probes: notes, calculator, managed recovery/transport and GUI observations/matrix. It needs already available Playwright/Chromium; --chromium selects a local executable. Optional Node checks syntax. These tools are developer instrumentation; nothing is installed automatically.

The shared runtime supports Python 3.11–3.14; versions not actually exercised remain untested. Local Python versions are recorded separately; definitions for hosted CI do not establish an observed run. Pixel-twin synthetic comparison does not establish native Qt or Notepad Next parity. Probe/test approval labels are synthetic and confer no actual product acceptance.

Regenerate SHA256SUMS.json over exact release source (excluding itself/development outputs), package, clean-extract, verify inventory and rerun checks. Current evidence is unsigned observation, never Baker acceptance.


## Save organ integration and scanner reconciliation — 23 October 2026

Executed locally on Windows x64, CPython 3.14.2 and Chromium 145.0.7632.6:

| Check | Result | Scope |
| --- | --- | --- |
| Combined MantleOS suite | 321 run, 316 passed, 5 skipped; 369.315s | Full suite including shared KPP checks |
| Primary KPP suite | 228 run, 223 passed, 5 skipped; 65.310s | Complete standalone workflow suite |
| Save organ browser demonstration | PASS | Two broken candidates rejected; reviewed replacement; injected activation failure; state-preserving restoration; recovered browser checkpoint |
| Candidate behavior profile | PASS | Nine checks covering exact Unicode/empty bytes, filename, single user gesture, failure isolation, cleanup, storage failure and Open |
| Existing browser probes | 4 PASS | Notepad, calculator, managed recovery/transport and GUI observations |
| JavaScript syntax | 11 PASS | Current and retained runtime plus all preview modules |
| KPP doctor and adaptive smoke | PASS | Local deterministic tooling; no model/provider required |
| Documented MantleOS walkthroughs | 5 PASS | Foundation, working examples, thoughts, KPP and discovery |
| Offline distributions | Both projects built | Wheels and source distributions using already provisioned pinned build tools |
| Fresh KPP wheel | PASS outside checkouts | Identical facade modules, packaged contracts/runtime assets and doctor |

The five skips require unavailable Windows symlink privileges. Discovery's junction
refusal test passed. Other Python versions, operating systems, external model
providers, SCAN v0.28 and native-reference parity were not qualified here.

The first KPP full run exposed missing retained Qt entry points and lost projected
HTML control IDs in the pre-existing scanner work. Those were repaired and tested,
along with a trace CLI forwarding regression and equivalent filter normalization.
All final shared source originates in KPP. The former MantleOS discovery suite is
now in shared KPP tests, updated to prove overlap of captured-file extraction.

The two negative candidate reports intentionally record FAIL; admission rejects
them and preserves the active baseline. The final demonstration passes with three
retained Save revisions, BUILDING phase and no Baker acceptance. Managed JavaScript
is not a sandbox, and hashes/report declarations are not authentication.

Repeat the new probe using `tools/check_organ_save.py --output NEW_DIRECTORY
--execute --reviewed`. Existing release validation and full verification commands
remain applicable. Local receipts, candidate sources, screenshots, checkpoints,
history and initial failing logs remain outside Git under MantleOS's ignored
`.work/organ-bridge/`. No remote publication or configuration was performed.
