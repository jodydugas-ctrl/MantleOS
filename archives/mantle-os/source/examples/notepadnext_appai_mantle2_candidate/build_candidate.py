"""Build a disposable, independently keyed NotepadNext Mantle 2 candidate."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from mantle.certify import certify_nest, write_certificate
from mantle.hatchery import hatch
from mantle.lifecycle import LifecycleAction, LifecycleAuthorization
from mantle.primer import appai_commandments, appai_truths
from mantle.spore import inspect_spore_typed, pack_germ, verify_spore


HERE = Path(__file__).resolve().parent
HOST_COMMIT = "0e9694d98aa8a9962bbe2bfa9dd502931be33670"


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build(out: Path) -> dict:
    out = out.resolve()
    if out.exists():
        raise FileExistsError("candidate output already exists; historical outputs are preserved")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.mkdir()
    terminal = (HERE / "terminal.py").read_text(encoding="utf-8")
    germ = {
        "schema": "mantle-germ-v2",
        "identity": {
            "name": "NotepadNext.AppAI.Mantle2Candidate",
            "purpose": "evidence-grounded resident for the pinned NotepadNext host",
        },
        "truths": appai_truths([
            "NotepadNext remains ordinary host software and is never modified by this candidate.",
            "Observed Qt mappings are not applied or runtime-verified hooks.",
        ]),
        "commandments": appai_commandments([
            "Preserve unsaved user text and require Body-owned post-state proof for visible operations.",
        ]),
        "controls": [
            {"id": "editor", "type": "text-surface", "commit_policy": "submit_or_blur"},
            {"id": "terminal", "type": "conversation"},
        ],
        "host_evidence": {
            "repository": "https://github.com/dail8859/NotepadNext",
            "commit": HOST_COMMIT,
            "substrate": ["c++20", "qt6", "cmake"],
            "insertion_state": "observed_causal_graph",
            "runtime_hook_verified": False,
        },
        "embedded_material": [{
            "path": "terminal.py", "content": terminal,
            "sha256": _digest(terminal.encode("utf-8")),
        }],
    }
    spore = out / "notepadnext-mantle2-candidate.png"
    pack_germ(germ, str(spore), source={
        "kind": "git", "url": "https://github.com/dail8859/NotepadNext",
        "ref": HOST_COMMIT,
        "notes": "pinned source evidence; candidate does not apply host hooks",
    })
    if not verify_spore(str(spore))["ok"]:
        raise RuntimeError("candidate spore verification failed")

    keys = []
    residents = []
    for suffix in ("a", "b"):
        target = out / ("resident-" + suffix)
        auth = LifecycleAuthorization.issue(LifecycleAction.HATCH, str(spore), str(target))
        result = hatch(str(spore), out_dir=str(target), warmup_beats=0,
                       authorization=auth)
        keys.append(result["organism"].body.key_fingerprint)
        residents.append(str(target))
    if keys[0] == keys[1]:
        raise RuntimeError("genesis keys were not independently minted")

    certificate = certify_nest(residents[0])
    write_certificate(certificate, str(Path(residents[0]) / "certification.json"))
    inspection = inspect_spore_typed(str(spore)).to_dict()
    audit = {
        "schema": "notepadnext-lifecycle-completion-audit-v2",
        "result": "PASS",
        "historical_artifacts_modified": False,
        "host_commit": HOST_COMMIT,
        "resident_protocol": "mantle-resident-v2",
        "germ_schema": "mantle-germ-v2",
        "spore_sha256": _digest(spore.read_bytes()),
        "embedded_terminal_sha256": germ["embedded_material"][0]["sha256"],
        "activation_authorization": "fresh artifact-and-target-bound operator receipt per hatch",
        "genesis_keys_independent": True,
        "resident_key_fingerprints": keys,
        "insertion_state": "observed_causal_graph",
        "runtime_hook_verified": False,
        "visible_operation_certified": False,
        "inspection": inspection,
        "residents": residents,
    }
    (out / "LIFECYCLE_COMPLETION_AUDIT_V2.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return audit


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(build(args.out), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
