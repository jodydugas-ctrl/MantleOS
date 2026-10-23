from __future__ import annotations

import subprocess
import zipfile
from pathlib import Path

from examples.hermes import build_release


def test_release_bundle_excludes_compiled_and_private_tissue(tmp_path: Path, monkeypatch):
    nest = tmp_path / "nest"
    mantle = nest / "mantle"
    cache = mantle / "__pycache__"
    private = nest / ".mantle"
    cache.mkdir(parents=True)
    private.mkdir()
    (mantle / "ASSIMILATION.json").write_text("{}", encoding="utf-8")
    (mantle / "runtime.py").write_text("pass\n", encoding="utf-8")
    (cache / "runtime.pyc").write_bytes(b"compiled")
    (private / "identity.key").write_bytes(b"private")
    output = tmp_path / "out"

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, stdout=b"patch"),
    )
    monkeypatch.setattr(
        "sys.argv",
        ["build_release.py", str(nest), str(output)],
    )
    assert build_release.main() == 0

    with zipfile.ZipFile(output / "mantleos2-hermes-delta.zip") as archive:
        names = set(archive.namelist())
        patch = archive.read("host-edge.patch")
    assert "mantle/runtime.py" in names
    assert "APPLY.md" in names
    assert patch == b"patch"
    assert not any("__pycache__" in name or name.endswith(".pyc") for name in names)
    assert not any(".mantle" in name or name.endswith(".key") for name in names)
