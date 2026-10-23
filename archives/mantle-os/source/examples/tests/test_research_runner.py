import sys
from pathlib import Path

import pytest

from mantle.research import BoundedProcessError, BoundedProcessRunner, ProcessBudget


def _runner(tmp_path: Path):
    return BoundedProcessRunner(allowed_env={"PYTHONIOENCODING"}), ProcessBudget(
        wall_seconds=1, cpu_seconds=1, memory_bytes=128 * 1024 * 1024,
        output_bytes=1024, file_count=16,
    )


def test_runner_bounds_wall_output_and_census(tmp_path: Path):
    runner, budget = _runner(tmp_path)
    result = runner.run(
        [sys.executable, "-c", "print('ok')"], cwd=tmp_path,
        env={"PYTHONIOENCODING": "utf-8"}, budget=budget,
    )
    assert result.ok and result.stdout.strip() == b"ok"
    result = runner.run(
        [sys.executable, "-c", "import time; time.sleep(5)"], cwd=tmp_path,
        env={"PYTHONIOENCODING": "utf-8"}, budget=budget,
    )
    assert result.timed_out and not result.ok
    result = runner.run(
        [sys.executable, "-c", "print('x' * 5000)"], cwd=tmp_path,
        env={"PYTHONIOENCODING": "utf-8"}, budget=budget,
    )
    assert result.output_limited and len(result.stdout) <= budget.output_bytes


def test_runner_rejects_unallowlisted_environment_and_unavailable_network_guarantee(tmp_path: Path):
    runner, budget = _runner(tmp_path)
    with pytest.raises(ValueError):
        runner.run([sys.executable, "-c", "pass"], cwd=tmp_path,
                   env={"SECRET": "no"}, budget=budget)
    if sys.platform.startswith("win"):
        with pytest.raises(BoundedProcessError):
            runner.run([sys.executable, "-c", "pass"], cwd=tmp_path,
                       env={}, budget=budget, require_network_isolation=True)
