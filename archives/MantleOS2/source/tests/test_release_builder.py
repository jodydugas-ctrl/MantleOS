from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import build_release


def test_release_evidence_contains_only_package_artifacts(tmp_path: Path, monkeypatch):
    dist = tmp_path / "dist"
    dist.mkdir()
    wheel = dist / "mantleos2-2.0.0a3-py3-none-any.whl"
    source = dist / "mantleos2-2.0.0a3.tar.gz"
    wheel.write_bytes(b"wheel fixture")
    source.write_bytes(b"source fixture")
    private = tmp_path / "private.key"
    private.write_bytes(b"not for release")
    report = tmp_path / "test-results.xml"
    report.write_text("<testsuite/>\n", encoding="utf-8")
    output = tmp_path / "out"
    monkeypatch.setattr(
        "sys.argv", ["build_release.py", str(dist), str(output), "--test-report", str(report)]
    )
    assert build_release.main() == 0
    assert (output / "test-results.xml").read_text(encoding="utf-8") == report.read_text(encoding="utf-8")
    assert json.loads((output / "sbom.spdx.json").read_text(encoding="utf-8"))["packages"]
    sums = (output / "SHA256SUMS").read_text(encoding="utf-8")
    assert f"{hashlib.sha256(wheel.read_bytes()).hexdigest()}  {wheel.name}" in sums
    assert f"{hashlib.sha256(source.read_bytes()).hexdigest()}  {source.name}" in sums
    assert "private.key" not in sums
    assert {path.name for path in output.iterdir()} == {
        "test-results.xml", "sbom.spdx.json", "SHA256SUMS"
    }
