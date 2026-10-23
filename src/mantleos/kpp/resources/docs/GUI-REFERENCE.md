# GUI discovery and independent coverage

gui-scan reads local Qt .ui declarations without Qt, imports, scripts or network access. Bounds: 1..256 files, 2 MB/file, 16 MB total, XML depth 64 and 10,000 entries. Symlinks, malformed XML and DTD/entities are refused. UTF-8 and BOM-marked UTF-16 are supported.

Current format: kpp.gui-inventory/2. source.identity is an unauthenticated label; source.files pins relative paths by raw-byte SHA-256; source.revision is the canonical digest of that map, not a Git commit. Upstream commit, source permission and licensing need separate review.

Entries locate widgets, actions, groups, placements, connections and tab order, carrying file/XML path, class, label, shortcuts, properties and declaration-only confidence. Initial disposition is required, with no anchor_ids. Required/deferred/unknown/unsupported entries need mandatory mappings. Excluded entries remain visible and require scope_approval={baker,evidence}. A mapping establishes accounting only.

Recipe reference_gui selects source_root, inventory={path,sha256}, and coverage_anchor. Path is under references/; the pin uses kpp.core.digest over JSON. Target source/version must match inventory identity/content revision. Before publication KPP rescans and compares all structural declarations; dropping or relabeling entries fails even after repinning. New scope needs a reviewed new recipe and workspace.

## Independent matrix

`gui-matrix --workspace WS` is also projected by status, coverage and the Functional Graph.

| Observation | Supported meaning |
| --- | --- |
| Discovered | Declaration found in the pinned reference |
| Accounted for | Mandatory Anchor mapping or approved exclusion |
| Represented | Explicit evidence of presence in the emerging GUI |
| Functional | Explicit evidence of implemented behavior |
| Tested | Behavior was exercised; its result may have failed |
| Accepted | Mapped obligation has current Baker approval |

Percentages use all discovered entries as denominator. Shared Anchor approval can accept several obligations without asserting presence, behavior or testing. No stage promotes another. Exclusions retain their Baker and reason and are counted separately; exclusion alone grants no acceptance.

Candidate entry_observations are arrays of {entry_id, locator:{region:[x,y,width,height]}, represented:boolean, functional:boolean, tested:boolean}. Regions must fit actual PNG dimensions. Flags are independent. Screenshots support representation; functional/tested claims require action, expected and observed results in a runtime record. A failed interaction is still tested and cannot be GUI-accepted. These are labeled manual observations, not certified facts.

Evidence is bound to workspace, pinned sources, capture bytes and context. Stale claims do not count. Conflicting claims in the same mode/state are disclosed and cannot give a positive count; distinct conditional contexts remain visible.

## Captures and comparison

gui-record requires --workspace, --capture, --surface reference|candidate, --method screenshot|runtime, --actor, --mode and --ui-state. --entries links declarations; --entry-observations reads a JSON array. Runtime records also require --action, --expected and --observed. gui-evidence --workspace WS --id ID rechecks evidence. gui-compare --workspace WS --reference ID --candidate ID --actor LABEL requires matching target, viewport, mode and state, producing pixel metrics and a difference image. gui-accept --workspace WS --anchor ID --id EVIDENCE --baker LABEL --evidence TEXT is separate explicit review.

The stdlib PNG codec supports bounded static noninterlaced 8-bit RGB/RGBA, checks CRC/chunk ordering and all five row filters, and refuses unsupported encodings. Metrics compare raw RGBA without color management or semantic equivalence. Relevant [W3C PNG chunk/filter definitions](https://www.w3.org/TR/png-3/) guide this limited profile; full PNG conformance is not claimed. Pixel comparison establishes no behavior or approval.

The synthetic fixture has two files and 20 declarations (9 widgets, 3 actions, 5 placements, 2 connections, 1 tab order), mapped to one declaration-audit Anchor. The browser oracle measures 20 accounted, 3 represented, 2 functional, 2 tested and 0 accepted, with an explicitly synthetic pixel twin reference. Notepad Next remains a possible Chase example; no source acquisition, native Qt runtime, clone or parity is included. Declarations are not exhaustive dynamic/platform/accessibility coverage.
