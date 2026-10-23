# Files.AppAI Stage-1 Certification

## Declaration

- AppAI: `Files.AppAI`
- Source evidence: `files-community/Files`
- Evidence commit: `7aa516aca1a97e08ffd74a5cc79a91d00e828a2c`
- Carrier: `spore-png-v2`, Grimoire v0.9 QUOTE statements
- Runtime: static HTML/CSS/JavaScript plus a hatched Mantle Body
- MIND: dormant
- Model calls: zero
- Network required: no
- Files source write limb: none

## Gate Receipt

| Gate | Evidence | Verdict |
| --- | --- | --- |
| Spore generation | `examples/files_appai/build.py` deletes and recreates the PNG from germ + face | PASS |
| Carrier structure | 28/28 `verify_spore` checks | PASS |
| Statement integrity | 70/70 generated statements report PARITY `ok` | PASS |
| Container integrity | Full-lane SHA-256 status `ok` | PASS |
| Germ proving cases | `files_area` 4/4; `files_verify_command` 3/3 | PASS |
| Stage-1 Body | 21/21 rows; zero failures | PASS |
| Persisted birth evidence | body, organism, seal, portrait, and hatch report all present | PASS |
| Source lifecycle receipt | One receipt survives sealed reload | PASS |
| Phenotype identity | Sealed origin source SHA-256 equals local `index.html` | PASS |
| Browser behavior | Evidence, instincts, commit discipline, and containment assertions pass | PASS |
| Browser network boundary | Zero external requests observed | PASS |
| Responsive layout | Desktop and 390x844 mobile have no horizontal overflow | PASS |

"100% certified" here means every declared carrier, Body, persistence, and phenotype gate
above passed. It does not claim that changing external repository facts remain current
after the recorded commit.

## Grimoire Receipt

- Physical lane order is raw `R/G/B/A`.
- HEAD carries `B=DIRECT`, `A=QUOTE`.
- Non-HEAD/non-PARITY morphemes use `B=0`, `A=0` inheritance.
- Each statement ends in `G=0x7f` PARITY over R/B/A.
- Zero R XOR is encoded as `R=0xFE`; zero B/A XOR remains zero.
- The manifest fingerprints all raw payload lanes and explicit frame boundaries.
- Unsupported assistant questions are returned as `UNKNOWN`, never upgraded.

## Reproduce

```powershell
$env:PYTHONPATH = "src"
python -B examples/files_appai/build.py
python -B examples/files_appai/certify.py
python -B -m pytest -q examples/tests/test_grimoire_spore_v2.py examples/tests/test_spore_hatchability.py
python -B -m http.server 8765 --directory examples
```

Then, from `examples/tests`, run `node files_appai_smoke.mjs` with Playwright available.
The complete repository gate remains `python -B -m mantle check`.
