# Ingredient disclosure

Pantry manifests own metadata. `pantry --query` finds small labels; `--id` reads one. Expand `--level contract` for suitability, department and technical tags, and declared sources. Expand `--level source` to see source pointers and inspection guidance. `--check-source` rechecks a bounded local-directory inventory or bundled file pins. Source-level disclosure also verifies the existing `bundled-files` pins. Repository-file declarations are reported without reading their targets.

For `repository-files`, contract and source views return the declared repository and safe relative paths with `integrity: DECLARED_LOCATION_ONLY` and `source_access: EXPLICIT_ONLY`. Discovery and views do not fetch, import, hash, open, or execute those files. The path is a pointer for a later, deliberate source review.

Labels describe purpose, interfaces, limits, tissue, provenance, and the manifest's evidence statement. They neither prove behavior nor authorize integration. `ready` describes support for the narrow current-source contract, not recipe compatibility. Recipe-specific fitness and Baker acceptance remain separate. Workspaces retain pinned selection-time labels. External sources require actual revision, license, and interface review for the selected recipe; nothing is fetched automatically.
