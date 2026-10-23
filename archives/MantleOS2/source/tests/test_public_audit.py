import gzip
from pathlib import Path

from mantleos.public_audit import audit_public_tree


def test_clean_tree_passes(tmp_path: Path):
    (tmp_path / "README.md").write_text("public text", encoding="utf-8")
    assert audit_public_tree(tmp_path) == []


def test_private_paths_and_secret_shapes_are_refused(tmp_path: Path):
    private = tmp_path / ".mantle"
    private.mkdir()
    (private / "state.json").write_text("private", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("sk-or-v1-" + "x" * 30, encoding="utf-8")
    findings = audit_public_tree(tmp_path)
    assert {finding.reason for finding in findings} == {"private organism path", "OpenRouter API key"}


def test_compressed_evidence_is_scanned_for_secret_shapes(tmp_path: Path):
    value = b'{"value":"sk-or-v1-' + b"x" * 30 + b'"}'
    (tmp_path / "evidence.json.gz").write_bytes(gzip.compress(value, mtime=0))
    findings = audit_public_tree(tmp_path)
    assert {finding.reason for finding in findings} == {"OpenRouter API key"}
