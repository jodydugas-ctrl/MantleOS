from __future__ import annotations

from scan.assimilation_context import files_for_assimilation_detection, is_runtime_candidate_path


def test_documentation_and_test_helpers_are_not_runtime_substrates():
    rows = [
        {"path": "docs/capture-window.ps1", "language": "PowerShell", "is_binary": 0},
        {"path": "tests/setup.py", "language": "Python", "is_binary": 0},
        {"path": "src/app.ts", "language": "TypeScript", "is_binary": 0},
        {"path": "main.ps1", "language": "PowerShell", "is_binary": 0},
    ]
    out = files_for_assimilation_detection(rows)

    assert out[0]["language"] == "Markdown"
    assert out[0]["assimilation_original_language"] == "PowerShell"
    assert out[1]["language"] == "Markdown"
    assert out[2]["language"] == "TypeScript"
    assert out[3]["language"] == "PowerShell"
    assert is_runtime_candidate_path("docs/capture-window.ps1") is False
    assert is_runtime_candidate_path("main.ps1") is True


def test_context_filter_never_mutates_canonical_file_rows():
    row = {"path": "docs/helper.ps1", "language": "PowerShell", "is_binary": 0}
    original = dict(row)
    out = files_for_assimilation_detection([row])

    assert row == original
    assert out[0] is not row
    assert out[0]["language"] == "Markdown"
