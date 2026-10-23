# Progressive BioSoftware

For chat construction, follow [the shared Canvas build sequence](CANVAS-BUILDS.md):
mount the first useful slice before generating later stages, keep its state alive,
then use `build-step --workspace DIR` after each Chase cycle. The shared
`mantleos.kpp.build.run` host driver opens the preview before invoking refinement
and keeps unmet requirements active until current scoped acceptance. It reports
review/blocking/budget stops with a resume point and never supplies Baker approval.

Product, construction and delivery are independent. BioSoftware implies no MIND or agent. BioAgent and AppAI require explicit capabilities and separate operator authority.

Browser recipes pin index.html/base.js/style.css, declare state_profile=json-body/1, and share assets/progressive.js. The loopback server serves a fixed shell and source manifest. Reviewed installation is explicit; serving/activity do not generate or install code. Integrity and dependencies gate modules.

The base owns an independently useful application and frozen window.KPPBody snapshot()/restore() adapter. Snapshots are plain JSON objects: finite values, no cycles or silent field loss, depth <=128 and serialized UTF-8 <=8 MiB. Notepad supports typing/local drafts before extensions; calculator supports arithmetic.

Modules register synchronously with window.KPP.define(id, activate). activate(context) uses managed listen, property, append and cleanup. Activation may add resources but must preserve existing Body data. Failures remove tracked resources and restore pre-activation/pre-action data. Withdrawal cascades dependents and preserves the current snapshot, including drafts written after activation. Reactivation avoids duplicate handlers; pinned source remains for recovery.

This is a reviewed-code contract. Async effects belong to product code and must manage cancellation. The file module refuses invalid UTF-8, oversized files, stale reads after withdrawal and reads that would overwrite newer typing. Runtime cannot undo arbitrary unregistered effects or sandbox malicious JavaScript. Shell replacement and arbitrary cross-schema migration are unsupported.

Actual browser probes cover first typing, Unicode, reload, mounted selection, additive controls, failed activation/action, cleanup, withdrawal/reactivation, canceled/invalid/delayed reads, explicit state transport and receiving-origin recovery. Optional Playwright/Chromium are developer instrumentation, not runtime dependencies. Staged, visible, interactive, tested and accepted remain distinct.
