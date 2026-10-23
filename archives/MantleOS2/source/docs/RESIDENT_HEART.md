# Resident Heart lifecycle evidence

Scope: issue #16, incremental progress after PRs #30–#32. This document
records actual boundaries, not complete native service certification.

## Runtime and scheduling

The generated runner imports the NEST-local `mantle/runtime/mantleos` organs
using isolated Python. A global constructor installation is not its organ source.
Python and cryptography remain runtime prerequisites.

`MantleBody.watch` runs a full startup Heartbeat, observes committed communication
at the configured file cadence and runs scheduled full Heartbeats at the separate
maintenance cadence. Both intervals must be positive and finite. Idle waits are
at most 100 ms, with stop checked again after waiting and before a new Heartbeat.
Short stop-check slices do not increase the configured file-observation rate.

When maintenance and a file change coincide, a single `resident-scheduled`
Heartbeat runs all ordinary phases, including communication. A stat failure
during save/replace or temporary absence does not skip the maintenance decision.
An actual failed Heartbeat still fails visibly; this is not permission to ignore
storage failures. Post-Heartbeat observation includes the response written by
that beat so the response alone does not produce another wake.

This polling change does not claim durable concurrent-editor delivery, stable
message IDs, lossless saves or atomic transcript/VCW publication. Those remain
separate communication/storage gates.

## Cooperative command-line shutdown

`resident.watch_with_signals` owns handlers only while the CLI `watch` command
runs on the main thread. Embedded hosts may continue using their own handlers
and the existing `stop_requested` callback instead.

- SIGINT and SIGTERM, plus SIGBREAK where available, set a single stop flag.
  The handler does not acquire locks, write state, raise into a transaction,
  contact a provider or start another Heartbeat.
- A started Heartbeat is allowed to finish; no new Heartbeat starts after the
  watcher observes stop. A failure during that beat propagates as failure.
- Prior handlers are restored on normal return, runtime failure and partial
  installation failure. A worker-thread call is refused before handler changes.
- A normal CLI return prints `status=stopped`, the first received signal name
  and `shutdown=cooperative-between-heartbeats`. That output is process evidence,
  not a new VCW lifecycle record, organism death or an atomic shutdown checkpoint.

The implementation follows Python's [main-thread signal model](https://docs.python.org/3.13/library/signal.html).
Signal delivery depends on the operating system and launch surface. In
particular, Windows process termination is a forced kill rather than a Python
SIGTERM callback. Do not infer graceful Windows Task Scheduler shutdown from
the cooperative handler tests.

Idle stop checks have a 100 ms maximum requested wait slice, not a real-time
scheduling guarantee. Synchronous disk/lock/provider work can delay return.
A hard shutdown deadline needs the planned bounded asynchronous work lifecycle
and durable disposition of unfinished attempts. This implementation neither
claims that guarantee nor installs anything to resist OS termination.

## Verification map

| Evidence | Proven scope | Not proven |
| --- | --- | --- |
| `test_watch_shutdown.py` with controlled clock/state | Pre-start/idle/in-flight stop ordering; failed beat remains failed; finite intervals; cadence; unavailable file; collision and response-echo behavior | Real OS scheduling, storage durability or provider cancellation |
| `test_resident.py` | Explicit installation gates, NEST-local runner, mocked Windows/Linux registration; signal-handler restoration and main-thread boundary | Actual Task Scheduler/systemd installation or console signal delivery |
| `test_resident_registration.py` | Collision refusal, strict NEST-bound receipts, task owner/action checks, loaded-unit/override checks before Linux start, pending evidence, stop-before-delete and drift refusal using OS fixtures | Native task XML variants, service-manager timing, interrupted removal recovery or adversarial concurrent OS changes |
| `test_resident_process.py` existing cross-platform process test | Real encrypted disposable VCW; startup, communication, forced stop/restart, pending host receipt recovery, unchanged Primer and native Body | Crash during admission, OS-managed automatic restart or fenced canonical writer |
| `test_real_sigterm_stops_idle_resident_without_extra_heartbeat` (Linux) | Real SIGTERM delivery, exit code zero with stop result, no extra VCW event/Heartbeat, preserved Primer/native bytes and usable native Body | Windows graceful stop; termination during provider I/O; native systemd service lifecycle |
| `test_resident_native.py` on disposable hosted runners | Real installation, startup, communication, restart, already-stopped removal, preserved Primer/native bytes and VCW validity; Linux automatic restart after SIGKILL and zero-status stop | Windows automatic restart/graceful stop; login/reboot transitions; non-admin Windows 11; mid-transaction failure |

These tests run in the existing Windows/Linux Python 3.11–3.13 matrix. The real
SIGTERM case is explicitly skipped on Windows instead of fabricating evidence.
Fixtures birth only disposable test organisms; no real Compiler SELF or creator
machine service registration is changed.

## Registration ownership and failure boundaries

Installation requires explicit approval and birth, and creates only the known
NEST-local runner/receipt plus the user-level OS registration. Existing local
artifacts or unit files are refused, not overwritten. Windows task creation no
longer uses the force-replacement flag; command input is closed so a collision
cannot be accepted interactively. See Microsoft's [task creation reference](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/schtasks-create).

A `registration-pending` receipt is persisted before OS changes. Only successful
registration and configuration verification allow `registered`. Failures retain
intent and artifacts for inspection, with no automatic rollback that might
delete somebody else's registration. Repeating installation refuses the pending
construction. This is evidence retention, not yet an automatic recovery protocol.

Removal rederives the identifier, runner, organ location and (on Linux) unit path
from this NEST and current user configuration. It rejects redirected paths,
oversized/ambiguous receipts and changed runner bytes. Missing runners do not
hide a remaining registration. Legacy v2 receipts without a state field remain
readable, without automatic rewriting. Status is explicitly `receipt-only` and
reports `running=unknown`; it is not live process or OS-registration proof.

- Windows: inspect task XML for exactly one expected executable action, isolated
  runner arguments, the current user's SID and least privilege. Only then request
  task stop followed by deletion; a stop error prevents deletion. Deletion alone
  does not stop the program, as Microsoft's [task deletion reference](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/schtasks-delete)
  explains. Task stop is not claimed to be a graceful Heartbeat checkpoint.
- Linux: require exact unit bytes, the expected loaded fragment and no drop-ins.
  Installation checks these after reload and before `enable --now`; removal checks
  before `disable --now`. Relative configuration roots and unsupported expansion
  characters in interpreter/runner paths are refused pending a certified escaping
  profile. Existing simple-path unit formatting is retained for compatibility.
- OS commands use no shell, accept no interactive input, have a 30-second timeout,
  and return error classes rather than echoing command output into diagnostics.

If an operation fails, retain the receipt and inspect both it and the actual task
or user unit before taking any further approved recovery action. Do not delete
the receipt to bypass ownership checks or repeatedly retry an uncertain install.
An interrupted removal (for example, OS deletion succeeded but local cleanup did
not) still needs a verified recovery procedure. These preflight checks are not a
transaction with the OS and do not claim protection against a concurrent actor
replacing files or registrations between validation and mutation. Native service
tests must also establish already-stopped task behavior and actual task XML.

## Remaining acceptance gates

### Disposable native workflow

`native-resident.yml` runs `test_resident_native.py` on GitHub-hosted Windows
and Linux with Python 3.12. Ordinary unit runs skip this test. An explicit flag,
hosted-runner environment check and RUNNER_TEMP containment check prevent
accidental local registration; environment variables are not a security boundary
against a malicious caller. No provider secrets or foreign repository code are
used. Linux starts the disposable runner's user service manager; this is test
environment preparation, not a constructor privilege escalation.

The test uses the production installer and remover with actual OS replies. It
requires an OS-managed full startup Heartbeat, a committed communication reply,
another startup after restart, and removal of an already-stopped registration.
Primer, native Body bytes, encrypted VCW verification and native output remain
checked. Only the JUnit result is uploaded, never the disposable NEST.

Linux injects SIGKILL into the service's main process to test the declared
`Restart=on-failure` policy, then verifies exit status zero after `systemctl stop`.
Windows uses explicit [task run/end operations](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/schtasks-end),
not automatic failure recovery or graceful shutdown. Linux restart semantics
follow the [systemd service reference](https://github.com/systemd/systemd/blob/main/man/systemd.service.xml).
No reboot, user-login session transition, in-flight provider cancellation or
mid-transaction kill is covered. A failed test attempts ownership-checked removal;
it never bypasses those checks. Hosted VMs are discarded even if cleanup fails.

Native evidence is established only by successful workflow runs, not by the
presence of this harness. [Run 34157324647](https://github.com/jodydugas-ctrl/MantleOS2/actions/runs/34157324647)
passed both jobs on Ubuntu 24.04.4 and Windows Server 2025 with Python 3.12,
using source commit `30647be`. The broader certification requirements below remain.
That run issued an explicit initial Windows task start from the test. The final
gate is stricter: production installation now starts the task after ownership
verification, and the test must observe startup without issuing that command.
Failed initial starts retain pending installation evidence. The logon trigger is
retained for later sessions; it is not claimed tested by the on-demand start.

The first native run passed Linux and exposed an overly strict Windows XML
check: the optional RunLevel element can be absent for the default least-privilege
setting. The verifier now accepts absence, but rejects explicit empty, unknown or
elevated values. This follows Microsoft's [optional principal schema](https://learn.microsoft.com/en-us/windows/win32/taskschd/taskschedulerschema-principaltype-complextype)
and [default low-privilege task context](https://learn.microsoft.com/en-us/windows/win32/taskschd/security-contexts-for-running-tasks).
The setting does not prove effective token isolation when UAC is disabled or an
account ignores that setting; ordinary non-admin client certification remains open.

1. Extend observed native startup/removal to user-login/reboot transitions,
   non-admin Windows 11, Windows automatic restart/graceful stop, registration
   interruption and partial-removal recovery. Repeat the exact ownership/path
   checks in those environments; current hosted service tests do not close them.
2. A single serialized Body mutation port and storage-enforced writer epochs;
   current process/file locks must not be described as stale-writer fencing.
3. Crash-atomic admission/root/receipt publication and durable unfinished-work
   dispositions before claiming complete Heartbeat transaction recovery.
4. Bounded asynchronous provider/effect cancellation, an overall shutdown deadline
   and explicit uncertainty for work that may have happened remotely.

Do not close issue #16 or promote full resident certification until its actual
platform and storage evidence exists. Real resident installation on the creator's
PC remains separately approved.
