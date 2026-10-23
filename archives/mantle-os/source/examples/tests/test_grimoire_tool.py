import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parents[2]
TOOL = ROOT / "tools" / "grimoire_tool.py"
EDITION = ROOT / "documents" / "grimoire" / "editions" / "grimoire-v0.10.md"
LEGACY_EDITION = ROOT / "documents" / "grimoire" / "editions" / "grimoire-v0.9.md"


def run_tool(*args):
    return subprocess.run(
        [sys.executable, str(TOOL), *map(str, args)], cwd=ROOT,
        capture_output=True, text=True, encoding="utf-8",
    )


def test_verify_and_json_commands():
    verified = run_tool("verify", EDITION)
    assert verified.returncode == 0
    assert "SELFTEST PASS" in verified.stdout
    decoded = run_tool("decode", EDITION, "9a010801 212a0000 13400000 947f5c03", "--json")
    assert decoded.returncode == 0
    assert json.loads(decoded.stdout)["profile"] == "grimoire-v0.10"


def test_invalid_run_returns_nonzero_and_reasons():
    invalid = run_tool("decode", EDITION, "9a010801 947f5c03 13400000", "--allow-parity-absent")
    assert invalid.returncode != 0
    assert "interrupted and resumed" in invalid.stdout or "interrupted and resumed" in invalid.stderr


def test_legacy_edition_is_rejected_before_v010_rules_are_applied():
    result = run_tool("verify", LEGACY_EDITION, "--json")
    assert result.returncode == 2
    assert "supports GRIMOIRE v0.10 only" in result.stderr
    assert "BOOK FAIL" not in result.stdout


def test_compare_has_no_production_differences():
    compared = run_tool("compare", EDITION, "--profile", "grimoire-v0.10", "--json")
    assert compared.returncode == 0, compared.stdout + compared.stderr
    result = json.loads(compared.stdout)
    assert result["status"] == "PASS"
    assert result["differences"] == []
