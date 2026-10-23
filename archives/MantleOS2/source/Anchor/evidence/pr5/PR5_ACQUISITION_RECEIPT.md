# PR5 NotepadNext acquisition receipt

- Acquired (UTC): `2026-09-13T18:21:51.2836955Z`
- Repository: `https://github.com/dail8859/NotepadNext.git`
- Required/observed commit: `f57db52d6760a2ce4149a37190c3adaa586845f5`
- Required/observed tree: `f0995b128bf6dbc73e5d0f3ef4e4f302f8a3081b`
- Tree status: **MATCH**
- Tracked files: `1,928`
- Working tree: clean
- Git object verification: `git fsck --full` passed
- Submodules: none (`.gitmodules` absent; no mode-160000 tree entries)

## Accepted exact acquisition package

- File: `NotepadNext_exact_acquisition.zip`
- Method: provider-tree denominator plus byte-for-byte `git cat-file` export from the verified local Git object database
- Provider blobs: `1,928 / 1,928`
- Verified source bytes: `20,875,384`
- Package bytes: `7,336,255`
- Verification: declared size + canonical Git blob SHA-1 + available provider SHA-256
- SHA-256: `4a1343f4f56500ba850162039e7483e2f17f894be6493f5afbaacdf25c2c44a3`

An earlier Windows checkout/archive (`d808933bb774f7258750100ea5902ba0b06d1dc30ca8075b7d5c829f4290988e`) was rejected for the cold lineage because checkout filters transformed line endings in 1,823 blobs. No transformed bytes entered the accepted scan.

This receipt proves exact acquisition. Cold execution and certification are recorded separately in `PR5_COLD_SCAN_RECEIPT.json`. The third-party source package is intentionally not committed to this repository.
