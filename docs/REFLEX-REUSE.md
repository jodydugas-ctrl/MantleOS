# REFLEX reuse review — before implementation

Pinned KPP base: `96fb48a830e879a073738cf3a028af9824e2b249`; MantleOS base: `0139197e2e8a8e41072e10b60fe5def9d0e3de4d`. Full MantleOS inventory: 7,144 entries plus its index, including all four archive snapshots and preserved refs. Relevant active and historical implementations were inspected; this does not certify every archived test or historical receipt.

Prototype bundle SHA256: `6bec263858c8e1780f2b7bb9b4e734d42ce293c1eb79161e03fbcf34c64f62ff`; 103 manifest entries verified. Original per-file hashes and selected source hashes are in REFLEX-PROVENANCE.json.

| Classification | Source | Planned reuse | SHA256 |
| --- | --- | --- | --- |
| direct | `src/mantleos/lifecycle.py` | Current Body transport | `7ad19f1a3c26f5526b0b32b10a6df72c51d91be810d22550de4c11204750bba2` |
| direct | `src/mantleos/cartridge.py` | Current Body transport | `56e22f0fc5e3339b8a87b9d29605846db8a68f4df4d3894b3604a21f2546a896` |
| direct | `src/mantleos/chromamem.py` | Current Body transport | `9a12cae4b17feb5f3e1f0c3ccab0dd4b0acf5a90f459035d8685f8c39d3add3f` |
| direct | `src/mantleos/transactions.py` | Current Body transport | `f4aeac0393c17f01d6faec9a8d7810a4e2eda1ba36b438239b2ce21ca2e72e9b` |
| direct | `src/mantleos/engram.py` | Current Body transport | `6f44b80a01c28982bf70f477984b5478c20f21b8a544439becdd70aec164a2e7` |
| direct | `src/mantleos/kpp/pantry.py` | KPP discovery/evidence/export | `b878dd1981b1ab6b867c9c8271e67157ee5c8b43eaf7bfee43df98b509b7b86b` |
| direct | `src/mantleos/kpp/testing.py` | KPP discovery/evidence/export | `6dcfce1056eb1a81e657598125862099104d14e4db327b6038c7eedd89f4b96b` |
| direct | `src/mantleos/kpp/core.py` | KPP discovery/evidence/export | `c9e52bcce849c7f34cc8f47356d93059c72ebd3f4e49ac6364bf06210ab6d3bc` |
| direct | `tools/export_kpp.py` | KPP discovery/evidence/export | `80e965f6012f208043c97d93d254f60a27125d1260abeeb9bbce88f01836e134` |
| adaptation | `archives/mantle-os/source/src/mantle/vcw/drivers.py` | Gates and independent execution tests | `f7b36887b1739dc6f90d5b7f0f9ffcc212cd2bf286b186449e894bd805b2eedd` |
| reference | `archives/mantle-os/source/src/mantle/vcw/languages/registry.py` | Exact editions; review selftest result handling before reuse | `c4443ef854ec6895707dc6b44c9d9b7e6397bbf79d0ee72c63f0dd696a3839fb` |
| reference | `archives/MantleOS2/source/src/mantleos/runtime.py` | Later layered frontier/acknowledgment | `8761377165cceff0cbe7ad2d58f46c8e0646d880305fdcc6d5d4beff24504802` |
| reference | `archives/mantle-daemon-laboratory/source/daemon/development.py` | Offline candidate pin verification | `78ed317147cbdf89333105e6321d3672558df59c7265d9f2d7ad309747e2cdfe` |
| reference | `archives/organize-appai/source/organize/mantle_appai/assist.py` | Proposal-only application integration | `afa74bf52589d31410560f9e63cb6f0cc905cd72ac71632bf126da62fcf333f2` |

The original `mantle-os` Python exec runner is unsuitable as the REFLEX evaluator: it accepts broader Python code. Its refusal/budget tests are adaptation references only. Do not revive RGBA, encrypted historical VCW, whole archived runtimes or the unmerged SCAN branches. The historical Book registry checks that selftest returns a dictionary without checking a success flag; do not inherit that behavior.

Corrections to the supplied handoff: the REFLEX bundle, SPEC and original M0–M7 roadmap are available; the 64-test prototype suite was independently reproduced on Windows/Python 3.14 during planning. Its simulated registry and experimental raw/ZIP transports are not production authority. The dummy reviewer collision in admission is a reproduced defect to fix. The roadmap proposes types/operators absent from the prototype; they remain unsupported.

Current AppAI STASIS pauses recording and motor activity. Independent MIND sleep, complete layered wake deltas, scheduling, aging, rebirth, automatic calcification and immune-policy changes are deferred. MantleOS2 has useful frontier/acknowledgment code for that later work. Original Commandments variants must not replace the current founding Primer.

Licensing/provenance: Prototype bundle contains no LICENSE; maintainer-supplied experimental source, no MIT or open-source relicensing asserted. Shared MantleOS terms and source notices remain applicable. Historical sources remain inert, unchanged and under their own notices. No missing licensing information is interpreted as permission to relicense. No imported conversations or private identity are included.
