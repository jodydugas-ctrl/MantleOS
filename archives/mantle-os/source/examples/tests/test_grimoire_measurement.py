import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
JSON_PATH = ROOT / "documents" / "grimoire" / "measurements" / "v0.10-toolcraft.json"
MD_PATH = ROOT / "documents" / "grimoire" / "measurements" / "v0.10-toolcraft.md"


def test_toolcraft_measurement_is_explicitly_unmeasured_and_synchronized():
    record = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    report = MD_PATH.read_text(encoding="utf-8")
    assert record["edition"] == "grimoire-v0.10"
    assert record["statement_count"] == 9
    assert record["observed_statement_count"] == 0
    assert record["concept_recovery"]["status"] == "unmeasured"
    assert record["relation_recovery"]["status"] == "unmeasured"
    assert record["composition_review"] == {
        "tool": "unmeasured",
        "handwork": "unmeasured",
    }
    assert "**unmeasured**" in report
    assert "no B11/B12 clauses" in report
