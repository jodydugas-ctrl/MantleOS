from __future__ import annotations

import json
from pathlib import Path
import sys

from scan.agent_blueprint import export_agent_blueprint
from scan.engine import ScanEngine
from scan.refinement_loop import run_refinement_loop
from scan.store import Store


SOURCE_HTML = """<!doctype html><html><body>
<button id="save" onclick="save()">Save</button>
<input id="name" type="text" aria-label="Name">
</body></html>
"""


def _source_blueprint(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "source"
    source.mkdir()
    (source / "index.html").write_text(SOURCE_HTML, encoding="utf-8")
    scan_root = tmp_path / "source.scan"
    ScanEngine().scan(source, scan_root, "refinement-fixture")
    body = json.loads((scan_root / "machine_body_map.json").read_text(encoding="utf-8"))
    blueprint = tmp_path / "Fixture Anchor Blueprint.md"
    store = Store(scan_root / "scan_index.sqlite", readonly=True)
    try:
        export_agent_blueprint(
            store,
            body["specimen"],
            blueprint,
            engine_version="0.28.0",
        )
    finally:
        store.close()
    return source, blueprint


def _candidate(tmp_path: Path, html: str) -> Path:
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    (candidate / "index.html").write_text(html, encoding="utf-8")
    return candidate


def test_refinement_loop_completes_immediately_for_conformant_candidate(tmp_path: Path):
    source, blueprint = _source_blueprint(tmp_path)
    receipt = run_refinement_loop(
        blueprint, source, tmp_path / "loop", engine_version="0.28.0", max_iterations=3,
    )
    assert receipt["state"] == "COMPLETE"
    assert receipt["iteration_count"] == 1
    assert receipt["iterations"][0]["conformance_state"] == "PASS"
    assert Path(receipt["paths"]["receipt"]).is_file()
    assert Path(receipt["paths"]["report"]).is_file()


def test_refinement_loop_emits_task_when_no_patch_worker_is_supplied(tmp_path: Path):
    _, blueprint = _source_blueprint(tmp_path)
    candidate = _candidate(tmp_path, "<!doctype html><html><body></body></html>")
    receipt = run_refinement_loop(
        blueprint, candidate, tmp_path / "loop", engine_version="0.28.0", max_iterations=3,
    )
    assert receipt["state"] == "WAITING_FOR_PATCH"
    assert receipt["iteration_count"] == 1
    task = Path(receipt["iterations"][0]["paths"]["agent_task"])
    payload = json.loads(task.read_text(encoding="utf-8"))
    assert payload["directive"].startswith("PATCH THE EXISTING")
    assert payload["required_unresolved_contract_ids"]


def test_refinement_loop_converges_with_external_patch_worker(tmp_path: Path):
    _, blueprint = _source_blueprint(tmp_path)
    candidate = _candidate(tmp_path, "<!doctype html><html><body></body></html>")
    patcher = tmp_path / "patcher.py"
    patcher.write_text(
        """import os
from pathlib import Path
root = Path(os.environ["SCAN_REFINEMENT_CANDIDATE_ROOT"])
(root / "index.html").write_text('''<!doctype html><html><body>
<button id="save" onclick="save()">Save</button>
<input id="name" type="text" aria-label="Name">
</body></html>''', encoding="utf-8")
""",
        encoding="utf-8",
    )
    receipt = run_refinement_loop(
        blueprint,
        candidate,
        tmp_path / "loop",
        engine_version="0.28.0",
        patch_command=[sys.executable, str(patcher)],
        max_iterations=3,
    )
    assert receipt["state"] == "COMPLETE"
    assert receipt["iteration_count"] == 2
    assert receipt["iterations"][0]["score"]["hard_failures"] >= 1
    assert receipt["iterations"][0]["patch_command"]["return_code"] == 0
    assert receipt["iterations"][1]["conformance_state"] == "PASS"


def test_refinement_loop_stops_when_worker_makes_no_change(tmp_path: Path):
    _, blueprint = _source_blueprint(tmp_path)
    candidate = _candidate(tmp_path, "<!doctype html><html><body></body></html>")
    noop = tmp_path / "noop.py"
    noop.write_text("# intentionally unchanged\n", encoding="utf-8")
    receipt = run_refinement_loop(
        blueprint,
        candidate,
        tmp_path / "loop",
        engine_version="0.28.0",
        patch_command=[sys.executable, str(noop)],
        max_iterations=3,
    )
    assert receipt["state"] == "NO_CHANGE"
    assert receipt["iteration_count"] == 2
    assert receipt["iterations"][1]["action"] == "stopped_no_change"


def test_refinement_loop_blocks_regression_of_previously_satisfied_contract(tmp_path: Path):
    _, blueprint = _source_blueprint(tmp_path)
    candidate = _candidate(
        tmp_path,
        '<!doctype html><html><body><button id="save" onclick="save()">Save</button></body></html>',
    )
    patcher = tmp_path / "regress.py"
    patcher.write_text(
        """import os
from pathlib import Path
root = Path(os.environ["SCAN_REFINEMENT_CANDIDATE_ROOT"])
(root / "index.html").write_text('<!doctype html><html><body><input id="name" type="text" aria-label="Name"></body></html>', encoding="utf-8")
""",
        encoding="utf-8",
    )
    receipt = run_refinement_loop(
        blueprint,
        candidate,
        tmp_path / "loop",
        engine_version="0.28.0",
        patch_command=[sys.executable, str(patcher)],
        max_iterations=3,
        regression_policy="stop",
    )
    assert receipt["state"] == "REGRESSION_BLOCKED"
    assert receipt["iteration_count"] == 2
    assert receipt["iterations"][1]["score"]["regressions"] >= 1
    assert receipt["iterations"][1]["action"] == "stopped_regression"
