from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Build host-independent MantleOS2 release evidence")
    parser.add_argument("dist", type=Path, help="MantleOS2 wheel and source distribution directory")
    parser.add_argument("output", type=Path)
    parser.add_argument("--test-report", type=Path)
    args = parser.parse_args()
    dist = args.dist.resolve()
    output = args.output.resolve()
    packages_built = sorted((*dist.glob("mantleos2-*.whl"), *dist.glob("mantleos2-*.tar.gz")))
    if not any(path.suffix == ".whl" for path in packages_built) or not any(
        path.name.endswith(".tar.gz") for path in packages_built
    ):
        raise SystemExit("MantleOS2 wheel and source distribution are both required")
    output.mkdir(parents=True, exist_ok=True)
    if args.test_report and args.test_report.is_file():
        shutil.copy2(args.test_report, output / "test-results.xml")
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")

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

    evidence = (path for path in output.iterdir() if path.is_file() and path.name != "SHA256SUMS")
    artifacts = sorted((*packages_built, *evidence), key=lambda path: path.name)
    sums = "".join(f"{sha256(path)}  {path.name}\n" for path in artifacts)
    (output / "SHA256SUMS").write_text(sums, encoding="utf-8", newline="\n")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
