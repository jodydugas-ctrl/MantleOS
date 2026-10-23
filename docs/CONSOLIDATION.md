# GitHub consolidation

The intended maintained repositories are `jodydugas-ctrl/MantleOS` and `jodydugas-ctrl/Kitchen-Party-Protocol`. This candidate is prepared locally; publication and deletion require approval of the completed review package.

MantleOS starts from `MantleOS-GitHub-Project-2026-10-23-r3.zip`, SHA-256 `af1349b8f6b58e7b2f71208d01867fa17c5242bb5971227856760a1be5eac527`. No old repository history becomes a parent of the new main branch. The four historical projects are preserved as inert archive data with independently restorable original backups. Unmerged SCAN work is preserved, not integrated.

## Shared KPP source

KPP remains primary for shared development. Prepare/review shared changes there, verify the complete standalone export, and promote matching bytes to MantleOS using the existing reviewed updater. The alignment lock identifies a clean KPP Git commit and its shared file hashes. `python tools/verify_kpp_pin.py --source KPP_CHECKOUT` checks that commit and the exact shared bytes. CI checks out that specific public commit read-only; it does not follow `main`, create updates or merge automatically. KPP may advance independently; MantleOS identifies its selected reviewed revision.

## Archives and distributions

`archives/ARCHIVE-FILES.json` inventories every historical file, including bundles and release assets. Archive checking refuses added, missing, modified and unsafe files. It does not execute old code. Private live-source exclusions remain unchanged outside this dedicated tree. `python tools/archive_inventory.py --reviewed` additionally requires completed public review.

Full repository handoffs include the inventoried archives. Wheels and source distributions exclude historical implementations, bundles, assets and GitHub record payloads; they carry only the archive index and current runtime. Use the GitHub repository or complete project handoff for historical restoration.

Exact original backups, including private state removed from public copies, remain outside GitHub. Public redactions and rewritten commit identities are documented per project. Retained private-distribution notices are provenance; consolidation grants no blanket open-source license and preserves component terms.

## Cutover gates

Verify original and public bundles, source snapshots, paginated GitHub exports, attachment/asset checksums, redactions, current test results and KPP parity. Recheck source repositories for changes after capture. Present the concrete review package. After approval, publish the new MantleOS repository and the ordinary KPP update, verify fresh clones and hosted CI, then delete only the four named old repositories. Any incomplete preservation or failed check prevents deletion.
