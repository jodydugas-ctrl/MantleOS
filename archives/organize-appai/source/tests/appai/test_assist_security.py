from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from organize import Config
from organize.logger import workspace_log_dir
from organize.mantle_appai.assist import answer_existing, create_proposal
from organize.mantle_appai.containment import ContainmentError, require_contained
from organize.mantle_appai.provider import FakeProvider, parse_proposal_response
from pydantic import ValidationError


def test_containment_rejects_parent_and_absolute_escape(tmp_path: Path):
    assert (
        require_contained(tmp_path, "inside/file.txt")
        == tmp_path / "inside" / "file.txt"
    )
    with pytest.raises(ContainmentError):
        require_contained(tmp_path, "../escape.txt")
    outside = tmp_path.parent / "outside.txt"
    with pytest.raises(ContainmentError):
        require_contained(tmp_path, outside)


def test_logging_stays_inside_marked_workspace(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("ORGANIZE_APPAI_WORKSPACE", raising=False)
    (tmp_path / "WORKSPACE.txt").write_text(str(tmp_path.resolve()), encoding="utf-8")
    nested = tmp_path / "product" / "app"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)
    assert workspace_log_dir() == tmp_path / "logs" / "organize"


def test_containment_rejects_symlink_escape(tmp_path: Path):
    outside = tmp_path.parent / (tmp_path.name + "-outside")
    outside.mkdir(exist_ok=True)
    link = tmp_path / "escape-link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as error:
        if os.name != "nt":
            pytest.skip(f"symlink creation unavailable: {error}")
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(outside)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            pytest.fail(f"could not create Windows junction: {result.stderr}")
    try:
        with pytest.raises(ContainmentError):
            require_contained(tmp_path, link / "child.txt")
    finally:
        # Remove the link itself, never its target. `os.rmdir` on a POSIX symlink
        # raises NotADirectoryError (ENOTDIR); a symlink must be `unlink`ed. On
        # Windows a junction is removed like a directory, so branch on platform.
        if os.name == "nt":
            link.rmdir()
        else:
            link.unlink()


def test_assist_saves_validated_proposal_but_never_executes(tmp_path: Path):
    inbox = tmp_path / "fixtures" / "inbox"
    inbox.mkdir(parents=True)
    original = inbox / "invoice.pdf"
    original.write_text("synthetic", encoding="utf-8")
    report = create_proposal(
        "Move PDF invoices into folders by year",
        safe_root=tmp_path,
        location=inbox,
    )
    assert report["validation"] == "passed"
    assert report["execution"] == "not_performed"
    assert Path(report["proposal_path"]).is_file()
    assert original.exists()
    assert not (tmp_path / "artifacts" / "proposed-archive").exists()


def test_assist_never_overwrites_active_configuration(tmp_path: Path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    active = tmp_path / "active.yaml"
    active.write_text("rules:\n  - actions: [echo]\n", encoding="utf-8")
    before = active.read_bytes()
    report = create_proposal(
        "Find duplicate files but do not delete anything",
        safe_root=tmp_path,
        location=inbox,
        existing_config=active,
    )
    assert active.read_bytes() == before
    assert report["diff"]
    assert Path(report["proposal_path"]) != active


def test_malformed_and_unsafe_model_output_falls_back(tmp_path: Path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    malformed = create_proposal(
        "report files",
        safe_root=tmp_path,
        location=inbox,
        provider=FakeProvider("not json"),
    )
    assert malformed["source"] == "deterministic"
    assert "provider output rejected" in malformed["provider_error"]

    unsafe = FakeProvider(
        {
            "config_yaml": f"rules:\n  - locations: [{inbox.as_posix()}]\n    actions: [delete]\n",
            "explanation": "unsafe",
            "assumptions": [],
        }
    )
    refused = create_proposal(
        "delete everything",
        safe_root=tmp_path,
        location=inbox,
        provider=unsafe,
    )
    assert refused["source"] == "deterministic"
    assert "refuses generated action" in refused["provider_error"]
    assert "delete" not in refused["config_yaml"]


@pytest.mark.parametrize(
    "unsafe_yaml, expected",
    [
        (
            "rules:\n  - locations: [$HOME]\n    actions: [echo]\n",
            "environment or home expansion",
        ),
        (
            "rules:\n  - locations: [.]\n    subfolders: true\n    actions: [echo]\n",
            "recursive traversal",
        ),
        (
            "rules:\n  - locations: [.]\n    filters: [python]\n    actions: [echo]\n",
            'filter "python"',
        ),
        (
            "rules:\n  - locations: [.]\n    actions: [symlink]\n",
            'action "symlink"',
        ),
    ],
)
def test_assist_rejects_expansion_recursion_and_unsafe_components(
    tmp_path: Path, unsafe_yaml: str, expected: str
):
    report = create_proposal(
        "unsafe provider proposal",
        safe_root=tmp_path,
        provider=FakeProvider(
            {
                "config_yaml": unsafe_yaml,
                "explanation": "unsafe",
                "assumptions": [],
            }
        ),
    )
    assert report["source"] == "deterministic"
    assert expected in report["provider_error"]


def test_assist_answer_requires_citations_from_bounded_evidence(tmp_path: Path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "invoice.txt").write_text("synthetic", encoding="utf-8")
    config = Config.from_string(
        f"rules:\n  - name: invoices\n    locations: [{inbox.as_posix()}]\n    filters:\n      - extension: txt\n    actions: [echo]\n"
    )
    provider = FakeProvider(
        {
            "answer": "The rule accepts txt files.",
            "citations": [
                {"ref": "config:rule:1", "claim": "Rule 1 filters txt files."}
            ],
            "uncertainty": "The bounded scan does not prove future filesystem state.",
        }
    )
    report = answer_existing(
        config, "Why is this file selected?", safe_root=tmp_path, provider=provider
    )
    assert report["source"] == "fake"
    assert report["citations"][0]["ref"] == "config:rule:1"
    assert report["trace_run_ids"]

    rejected = answer_existing(
        config,
        "Why?",
        safe_root=tmp_path,
        provider=FakeProvider(
            {
                "answer": "Invented.",
                "citations": [{"ref": "trace:not-supplied:99", "claim": "invented"}],
                "uncertainty": "none",
            }
        ),
    )
    assert rejected["source"] == "deterministic"
    assert "not supplied" in rejected["provider_error"]


def test_typed_provider_schema_rejects_extra_fields():
    with pytest.raises(ValidationError):
        parse_proposal_response(
            '{"config_yaml":"rules: []","explanation":"x","assumptions":[],"extra":1}'
        )


def test_pristine_source_clones_are_clean_when_workspace_is_present():
    workspace = Path(__file__).resolve().parents[4]
    sources = workspace / "sources"
    if not (workspace / "WORKSPACE.txt").is_file() or not sources.is_dir():
        pytest.skip("not running in the isolated integration workspace")
    for repository in (sources / "mantle-os", sources / "organize-upstream"):
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        )
        assert result.stdout == ""
