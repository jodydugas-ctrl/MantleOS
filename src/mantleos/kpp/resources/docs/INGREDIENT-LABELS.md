# Ingredient disclosure

Pantry manifests own metadata. `pantry --query` finds small labels; `--id` reads one. Expand `--level contract` for suitability, department and technical tags, and declared sources. Expand `--level source` to see source pointers and inspection guidance. `--check-source` rechecks a bounded local-directory inventory or bundled file pins. Source-level disclosure also verifies the existing `bundled-files` pins. Repository-file declarations are reported without reading their targets.

For `repository-files`, contract and source views return the declared repository and safe relative paths with `integrity: DECLARED_LOCATION_ONLY` and `source_access: EXPLICIT_ONLY`. Discovery and views do not fetch, import, hash, open, or execute those files. The path is a pointer for a later, deliberate source review.

Labels describe purpose, interfaces, limits, tissue, provenance, and the manifest's evidence statement. They neither prove behavior nor authorize integration. `ready` describes support for the narrow current-source contract, not recipe compatibility. Recipe-specific fitness and Baker acceptance remain separate. Workspaces retain pinned selection-time labels. External sources require actual revision, license, and interface review for the selected recipe; nothing is fetched automatically.

## Browse by organ

The [organ shelves](../pantry/organs/README.md) are generated from the same
manifests in the standalone project. The optional `organs` array lists one or
more shelf IDs. Use `pantry --organ memory` with any existing search filters.
Ingredients can appear on several shelves, and the main catalog includes
ingredients without an organ tag. Shelves describe responsibilities for browsing.
The recipe still determines the actual organ composition.

## Check ingredient fit

`provides` and `requires` describe interface IDs such as `notes-rows/1`.
An ingredient that declares these fields includes both arrays, using an empty
array when appropriate. A missing declaration appears as unknown. Existing
`dependencies` name specific ingredients. A named dependency must appear in the
proposed selection, while a capability can come from the host or a selected
ingredient with satisfied requirements.

`pantry-fit` accepts a recipe, explicit ingredients, or both. Repeated
`--host-capability` options describe interfaces the caller says the host
provides. The report prefers host declarations and lists unmet inputs, available
catalog suggestions, and selected ingredients that wait on one another. The
version is part of the match. An unspecified or mixed recipe tissue is marked
for review. The report binds its recipe and ingredient metadata with digests
and leaves verification and authorization to the normal KPP workflow.

From the standalone root with `src` on the Python path:

```console
python -m kpp pantry --organ memory
python -m kpp pantry-fit --recipe recipes/appai-heart-spore.json --ingredient appai-heart
python -m kpp pantry-fit --recipe recipes/appai-heart-notes-trial.json --host-capability notes-rows/1
python -m kpp pantry-fit --recipe recipes/sleep-memory-composition.json
python -m kpp pantry-fit --ingredient appai-heart --ingredient sleep-memory-consolidation
```

The Sleep Memory recipe declares the whole chain. Heart exposes a beat sequence
and Engram ledger source. Engram Continuity reads the source and supplies a
verified prefix. Sleep Memory uses the beat and prefix to produce a derived
view. The last command omits Engram Continuity so the report can show the
missing prefix and a suggested provider. The recipe specifies behavioral checks
on a supplied beat and byte preservation of the source ledger.

In MantleOS, use `python -m mantleos kpp` with the same options and resolve
recipe files under the bundled `src/mantleos/kpp/resources/recipes/` directory.
