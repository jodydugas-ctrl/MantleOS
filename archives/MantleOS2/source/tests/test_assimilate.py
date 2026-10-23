from __future__ import annotations

import gzip
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from mantleos.assimilate import (
    AssimilationError,
    assimilate_source,
    census_repository,
    construct_nest,
    normalize_github_source,
)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _host(tmp_path: Path) -> Path:
    root = tmp_path / "host"
    root.mkdir()
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.name", "Mantle Test")
    _git(root, "config", "user.email", "mantle@example.invalid")
    (root / "LICENSE").write_text("MIT test fixture\n", encoding="utf-8")
    (root / "app.py").write_text("print('native body')\n", encoding="utf-8")
    _git(root, "add", "LICENSE", "app.py")
    _git(root, "commit", "-m", "host fixture")
    return root


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("github.com/example/widget-app", "https://github.com/example/widget-app"),
        ("https://github.com/Example/Widget-App.git", "https://github.com/example/widget-app"),
        ("git@github.com:example/widget-app.git", "https://github.com/example/widget-app"),
    ],
)
def test_normalize_github_source(source: str, expected: str):
    assert normalize_github_source(source) == (expected, "widget-app")


def test_non_github_source_is_refused():
    with pytest.raises(AssimilationError):
        normalize_github_source("https://example.com/owner/repo")


@pytest.mark.parametrize(
    "source",
    [
        "https://example.com/github.com/owner/repo",
        "https://github.com.evil.example/owner/repo",
        "https://github.com/owner/repo?ref=unsafe",
        "https://user@github.com/owner/repo",
    ],
)
def test_github_lookalikes_and_ambiguous_urls_are_refused(source: str):
    with pytest.raises(AssimilationError):
        normalize_github_source(source)


def test_read_only_census_is_stable(tmp_path: Path):
    root = _host(tmp_path)
    before = census_repository(root)
    after = census_repository(root)
    assert before == after
    assert before.file_count == 2
    assert before.source_fingerprint.startswith("sha256:")


def test_census_is_independent_of_checkout_line_endings(tmp_path: Path):
    lf = tmp_path / "lf"
    crlf = tmp_path / "crlf"
    lf.mkdir()
    crlf.mkdir()
    (lf / "body.py").write_bytes(b"print('body')\n")
    (crlf / "body.py").write_bytes(b"print('body')\r\n")
    assert census_repository(lf) == census_repository(crlf)


def test_constructs_unborn_delta_without_executing_host(tmp_path: Path):
    root = _host(tmp_path)
    sentinel = root / "would-run.txt"
    (root / "setup.py").write_text(
        "from pathlib import Path\nPath('would-run.txt').write_text('bad')\n",
        encoding="utf-8",
    )
    _git(root, "add", "setup.py")
    _git(root, "commit", "-m", "untrusted candidate")

    manifest = construct_nest(
        root,
        source_url="https://github.com/example/host",
        command="mantle assimilate github.com/example/host",
    )

    assert manifest["status"] == "constructed-not-born"
    assert manifest["default_body"]["logical_layer"] == 0
    assert manifest["activation"]["automatic"] is False
    assert manifest["activation"]["traditional_plugin"] is False
    assert manifest["body_map"]["default_body"] == "NEST"
    assert manifest["gates"]["primer"] == "awaiting-developmental-mind"
    assert not sentinel.exists()
    assert not (root / "COMMUNICATION.TXT").exists()
    assert not (root / ".mantle" / "keys").exists()
    assert (root / "mantle" / "ASSIMILATION.json").is_file()
    assert (root / "mantle" / "maps" / "BODY_MAP.json").is_file()
    assert (root / "mantle" / "maps" / "ARTERY_MAP.json.gz").is_file()
    assert (root / "mantle" / "maps" / "FILE_COVERAGE.json.gz").is_file()
    assert (root / "mantle" / "maps" / "COVERAGE.json").is_file()
    assert (root / "mantle" / "maps" / "NERVE_MAP.json").is_file()
    assert (root / "mantle" / "runtime" / "mantleos" / "runtime.py").is_file()
    assert not any("plugin" in path.as_posix().lower() for path in (root / "mantle").rglob("*"))
    assert (root / ".mantle" / "prebirth.json").is_file()
    assert "/.mantle/" in (root / ".gitignore").read_text(encoding="utf-8")

    public = json.loads((root / "mantle" / "ASSIMILATION.json").read_text(encoding="utf-8"))
    prebirth = json.loads((root / ".mantle" / "prebirth.json").read_text(encoding="utf-8"))
    assert public["source"]["commit"] == _git(root, "rev-parse", "HEAD")
    assert public["gates"]["birth"] == "not-authorized"
    assert public["gates"]["public_delta"] == "verified-at-construction"
    assert prebirth["public_manifest_sha256"] == hashlib.sha256(
        (root / "mantle" / "ASSIMILATION.json").read_bytes()
    ).hexdigest()
    artery_archive = (root / "mantle" / "maps" / "ARTERY_MAP.json.gz").read_bytes()
    assert artery_archive[9] == 255
    assert isinstance(json.loads(gzip.decompress(artery_archive)), list)

    isolated = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            (
                "import sys; "
                f"sys.path.insert(0, {str(root)!r}); "
                "import mantle; "
                "assert mantle.MantleBody.__module__ == 'mantle.runtime.mantleos.runtime'"
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert isolated.returncode == 0, isolated.stderr


def test_host_markers_do_not_trigger_builtin_innervation(tmp_path: Path):
    root = _host(tmp_path)
    agent = root / "agent"
    agent.mkdir()
    markers = {
        root / "run_agent.py": "def run_agent(): pass\n",
        agent / "conversation_loop.py": "def run_conversation(): pass\n",
        agent / "turn_context.py": "def prepare_turn_context(): pass\n",
        agent / "tool_executor.py": "def execute(): pass\n",
    }
    for path, source in markers.items():
        path.write_text(source, encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "host markers")
    before = {path: path.read_bytes() for path in markers}

    manifest = construct_nest(root, source_url="https://github.com/example/host", command="test")

    assert manifest["target"]["kind"] == "generic"
    assert manifest["nerve_map"] == []
    assert manifest["activation"]["direct_nerves"] is False
    assert {path: path.read_bytes() for path in markers} == before
    assert json.loads((root / "mantle" / "maps" / "NERVE_MAP.json").read_text(encoding="utf-8")) == []


def test_existing_mantle_tissue_is_not_overwritten(tmp_path: Path):
    root = _host(tmp_path)
    (root / "mantle").mkdir()
    with pytest.raises(AssimilationError, match="already contains"):
        construct_nest(root, source_url="https://github.com/example/host", command="test")


def test_local_git_source_is_cloned_without_execution(tmp_path: Path):
    source = _host(tmp_path)
    destination = tmp_path / "candidate"
    manifest = assimilate_source(
        str(source),
        destination=destination,
        canonical_source="https://github.com/example/native-body",
    )
    assert manifest["source"]["canonical_url"] == "https://github.com/example/native-body"
    assert manifest["target"]["kind"] == "generic"
    assert manifest["target"]["mapping"] == "mapping-complete"
    assert manifest["gates"]["innervation"] == "awaiting-nerve-synthesis"
    assert manifest["execution_plan"]["approval"] == "required-before-any-command"
    assert not (destination / "would-run.txt").exists()


def test_local_source_canonicalizes_public_github_identity(tmp_path: Path):
    source = _host(tmp_path)
    manifest = assimilate_source(
        str(source),
        destination=tmp_path / "candidate",
        canonical_source="https://github.com/Example/Native-Body.git",
    )
    assert manifest["source"]["canonical_url"] == "https://github.com/example/native-body"
