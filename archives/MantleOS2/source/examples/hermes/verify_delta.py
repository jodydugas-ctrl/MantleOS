from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout.rstrip()


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def git_bytes(root: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True
    ).stdout


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a constructed Hermes delta")
    parser.add_argument("nest", type=Path)
    parser.add_argument("--expected-commit")
    args = parser.parse_args()
    nest = args.nest.resolve()
    manifest_path = nest / "mantle" / "ASSIMILATION.json"
    if not manifest_path.is_file():
        raise SystemExit("missing mantle/ASSIMILATION.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    actual = git(nest, "rev-parse", "HEAD")
    if manifest["source"]["commit"] != actual:
        raise SystemExit("manifest commit does not match the NEST")
    if args.expected_commit and actual != args.expected_commit:
        raise SystemExit("NEST does not match the certified upstream commit")
    if manifest["status"] != "constructed-not-born":
        raise SystemExit("reference delta must remain un-born")
    if (nest / "COMMUNICATION.TXT").exists() or (nest / ".mantle" / "keys").exists():
        raise SystemExit("construction created live organism material")

    if manifest.get("target", {}).get("traditional_plugin") is not False:
        raise SystemExit("Hermes must be innervated directly, not registered as a plugin")
    if manifest.get("activation", {}).get("direct_nerves") is not True:
        raise SystemExit("direct Hermes nerves are not declared")

    nerves = manifest.get("nerve_map", [])
    if not nerves:
        raise SystemExit("the Nerve Map is empty")
    nerve_paths = {nerve["anchor"]["path"] for nerve in nerves}
    allowed_paths = {".gitignore", "mantle/", *nerve_paths}

    changed = []
    for line in git(nest, "status", "--short").splitlines():
        path = line[3:].replace("\\", "/")
        changed.append(path)
        if path not in allowed_paths and not path.startswith("mantle/"):
            raise SystemExit(f"unexpected host change: {path}")
    if ".gitignore" not in changed or not any(path.startswith("mantle/") for path in changed):
        raise SystemExit("expected delta surfaces are missing")
    if not nerve_paths.issubset(changed):
        missing = sorted(nerve_paths.difference(changed))
        raise SystemExit(f"mapped nerve changes are missing: {missing}")

    # A file may contain more than one nerve. The first record binds the clean
    # upstream bytes and the last record binds the final innervated bytes.
    by_path: dict[str, list[dict]] = {}
    for nerve in nerves:
        by_path.setdefault(nerve["anchor"]["path"], []).append(nerve)
    for path, records in by_path.items():
        upstream = git_bytes(nest, "show", f"HEAD:{path}")
        current = (nest / path).read_bytes()
        if sha256(upstream) != records[0]["before_sha256"]:
            raise SystemExit(f"upstream seam hash mismatch: {path}")
        if sha256(current) != records[-1]["after_sha256"]:
            raise SystemExit(f"innervated seam hash mismatch: {path}")

    forbidden = [
        path
        for path in (nest / "mantle").rglob("*")
        if path.is_file() and ("plugin" in path.name.lower() or path.name == "plugin.yaml")
    ]
    if forbidden:
        raise SystemExit(f"traditional plugin material found: {forbidden}")
    print(json.dumps({"ok": True, "commit": actual, "changed_paths": changed}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
