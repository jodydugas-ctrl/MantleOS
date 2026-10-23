from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import subprocess
import zipfile
from datetime import UTC, datetime
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Build reproducible public release evidence")
    parser.add_argument("nest", type=Path, help="Constructed Hermes NEST")
    parser.add_argument("output", type=Path)
    parser.add_argument("--test-report", type=Path)
    args = parser.parse_args()
    nest = args.nest.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    bundle = output / "mantleos2-hermes-delta.zip"
    patch = subprocess.run(
        ["git", "diff", "--binary", "--full-index", "--", ":(exclude)mantle/**"],
        cwd=nest,
        check=True,
        capture_output=True,
    ).stdout
    if not patch:
        raise SystemExit("host-edge patch is empty")
    manifest = (nest / "mantle" / "ASSIMILATION.json").read_bytes()
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted((nest / "mantle").rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}:
                archive.write(path, path.relative_to(nest).as_posix())
        archive.writestr("host-edge.patch", patch)
        archive.writestr(
            "APPLY.md",
            "# Apply the Hermes reference seed\n\n"
            "Start from the exact commit recorded in `mantle/ASSIMILATION.json`. "
            "Copy `mantle/` into the NEST, then run `git apply --check host-edge.patch` "
            "and `git apply host-edge.patch`. Verify with MantleOS before any birth.\n\n"
            "To reverse the public delta before birth, run `git apply -R host-edge.patch` "
            "and remove only the copied `mantle/` directory. Private organism state is "
            "not part of this bundle.\n",
        )
        archive.writestr("manifest/ASSIMILATION.json", manifest)
        if args.test_report and args.test_report.is_file():
            archive.write(args.test_report, "evidence/test-results.xml")

    packages = []
    for name in ("mantleos2", "cryptography"):
        try:
            version = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            continue
        packages.append(
            {
                "SPDXID": f"SPDXRef-Package-{name}",
                "name": name,
                "versionInfo": version,
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": False,
            }
        )
    sbom = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": "MantleOS2-alpha-release",
        "documentNamespace": f"https://github.com/jodydugas-ctrl/MantleOS2/releases/{timestamp}",
        "creationInfo": {"created": timestamp, "creators": ["Tool: MantleOS2 release builder"]},
        "packages": packages,
    }
    (output / "sbom.spdx.json").write_text(json.dumps(sbom, indent=2) + "\n", encoding="utf-8")

    artifacts = sorted(path for path in output.iterdir() if path.is_file() and path.name != "SHA256SUMS")
    sums = "".join(f"{sha256(path)}  {path.name}\n" for path in artifacts)
    (output / "SHA256SUMS").write_text(sums, encoding="utf-8", newline="\n")
    print(bundle)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
