from __future__ import annotations

from pathlib import Path

import pytest

from scan.assimilation_candidate import validate_assimilation_candidate


def _candidate_source(name: str = "fixture-candidate") -> str:
    return f'''
from pathlib import Path
from scan.adapters.base import Adapter
from scan.inventory import FileRecord
from scan.model import Evidence, ExtractionResult, Node, stable_id

class CandidateAssimilationAdapter(Adapter):
    name = {name!r}
    version = "1"

    def accepts(self, record: FileRecord) -> bool:
        return record.language == "Python"

    def extract(self, root: Path, record: FileRecord, text: str) -> ExtractionResult:
        eid = stable_id("evidence", record.id, self.name, "module")
        nid = stable_id("node", record.id, self.name, "python-module")
        return ExtractionResult(
            nodes=[Node(nid, "symbol", "python-module", record.id, record.path, "MAPPED",
                        {{"language": "Python", "candidate_fixture": True}}, [eid])],
            evidence=[Evidence(eid, record.id, record.path, 1, 1, "MEASURED", self.name, text.splitlines()[0])],
        )
'''.lstrip()


def test_candidate_validator_runs_baseline_and_two_deterministic_candidate_scans(tmp_path: Path):
    specimen = tmp_path / "specimen"
    specimen.mkdir()
    (specimen / "app.py").write_text("value = 1\n", encoding="utf-8")
    candidate = tmp_path / "candidate_adapter.py"
    candidate.write_text(_candidate_source(), encoding="utf-8")

    report = validate_assimilation_candidate(
        specimen_root=specimen,
        candidate_path=candidate,
        output=tmp_path / "validation",
        specimen_id="candidate-fixture",
    )

    assert report["mechanical_gate"] == "PASS"
    assert report["determinism"]["state"] == "PASS"
    assert report["specimen"]["fingerprint_match"] is True
    assert report["integrity_gate"]["state"] == "PASS"
    assert report["delta"]["nodes"] >= 1
    assert report["promotion"]["state"] == "BLOCKED_PENDING_REVIEW"
    assert (tmp_path / "validation" / "candidate_validation.json").exists()


def test_candidate_validator_rejects_trusted_adapter_name_collision(tmp_path: Path):
    specimen = tmp_path / "specimen"
    specimen.mkdir()
    (specimen / "app.py").write_text("value = 1\n", encoding="utf-8")
    candidate = tmp_path / "candidate_adapter.py"
    candidate.write_text(_candidate_source("generic_text"), encoding="utf-8")

    with pytest.raises(ValueError, match="collides with trusted adapter"):
        validate_assimilation_candidate(
            specimen_root=specimen,
            candidate_path=candidate,
            output=tmp_path / "validation",
            specimen_id="candidate-fixture",
        )
