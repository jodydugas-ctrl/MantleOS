# Pantry

`kpp.ingredient/1` describes a reusable capability's purpose, interface, suitability, dependencies, provenance, and limits. Ingredients are selected by the human maintainer and AI Oven from metadata. Existing IDs remain stable; departments use the existing `tags` field, alongside technical tags:

- `department:memory` — continuity and retained records.
- `department:carriers` — portable representations and packaging.
- `department:languages` — implementation-language contracts.
- `department:body` — Body structure, tissue, and host-facing behavior.
- `department:cognition` — bounded reasoning, observation, and decision contracts.
- `department:construction` — application, scanning, and build capabilities.

## Status and evidence

- `ready` means current source and named evidence support the narrow contract written in the manifest. It does not claim compatibility with a particular recipe.
- `experimental` means an implementation exists, but evidence for the declared capability is incomplete.
- `reference` means the implementation is unavailable as a current reusable capability, or the entry is a limited example/design reference.

Pantry evidence is a manifest statement. The label says so explicitly; it is not independent proof. Recipe-specific fitness and Baker acceptance are separate and must be established for each recipe. A source pointer or content hash does not establish behavior, trust, rights, or compatibility.

## Source pointers and disclosure

Eligible manifests may declare `source: {"kind":"repository-files","repository":"owner/name","paths":[...]}` with canonical KPP repository-relative paths. These paths are advisory locations. Pantry query, label, contract, and source views only report the declaration; they never fetch, import, hash, open, or execute repository source. A source view marks the location `DECLARED_LOCATION_ONLY` and `EXPLICIT_ONLY`. Source review is a separate, deliberate action.

The original supplied Anchor specimens retain exact supported literal semantics. Browser ingredients support their declared browser contracts; they do not automatically produce native Qt or Python GUI runtimes. Read labels before source and expand only when resolving a concrete compatibility question.

## Historical research

VCW Cube is archive-only research and is excluded from the current-source inventory. VCW Stack remains unresolved. Neither is a Pantry ingredient or selectable manifest. Historical archive files are not current-source evidence.
