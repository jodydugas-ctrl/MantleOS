"""User-invoked commands in disposable copies. This is NOT an OS sandbox."""
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time
from .common import ScanError, outside, source_paths, tree_identity, write_json, sha
import shutil


def copy_source(source, target):
    target.mkdir()
    for path in source_paths(source):
        dest = target / path.relative_to(source)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)


def run_command(command, cwd, timeout):
    if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
        raise ScanError("Commands must be nonempty argument arrays; no shell strings")
    argv = [sys.executable if x == "{python}" else x for x in command]
    if command[0] == "{python}" and len(argv)>1 and argv[1].endswith('.py'):
        # Bundled isolated Python deliberately ignores ambient sys.path. Give the
        # explicitly authorized script the same local import root as normal Python.
        script = "import runpy,sys,pathlib; sys.argv=sys.argv[1:]; sys.path.insert(0,str(pathlib.Path(sys.argv[0]).resolve().parent)); runpy.run_path(sys.argv[0],run_name='__main__')"
        argv = [sys.executable, '-c', script, *argv[1:]]
    # Files bound in-memory capture; excessive output cannot be accepted as a complete oracle.
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        start = time.perf_counter()
        try:
            process = subprocess.run(argv, cwd=cwd, stdout=out, stderr=err, timeout=timeout, shell=False)
            status, code = "COMPLETED", process.returncode
        except subprocess.TimeoutExpired:
            status, code = "TIMEOUT", None
        elapsed = time.perf_counter() - start
        out.seek(0); err.seek(0)
        stdout, stderr = out.read(1_000_001), err.read(1_000_001)
    truncated = len(stdout) > 1_000_000 or len(stderr) > 1_000_000
    return {"status": status, "exit_code": code, "seconds": elapsed, "truncated": truncated,
            "stdout_sha256": sha(stdout), "stderr_sha256": sha(stderr),
            "stdout": stdout[:1_000_000].decode("utf-8", errors="replace"), "stderr": stderr[:1_000_000].decode("utf-8", errors="replace")}


def experiment(baseline, candidate, specification, output):
    baseline, candidate, output = Path(baseline).resolve(), Path(candidate).resolve(), Path(output).resolve()
    if baseline == candidate or not baseline.is_dir() or not candidate.is_dir(): raise ScanError("Supply distinct baseline and candidate directories")
    outside(output, baseline); outside(output, candidate)
    repeats = specification.get("repeats", 5)
    timeout = specification.get("timeout_seconds", 20)
    threshold = specification.get("minimum_improvement_percent", 3)
    budget = specification.get("total_seconds", 300)
    if type(budget) is not int or not 1 <= budget <= 3600: raise ScanError("Use a 1..3600 second total budget")
    if type(repeats) is not int or not 3 <= repeats <= 15: raise ScanError("Use 3..15 repeats")
    if type(timeout) is not int or not 1 <= timeout <= 120: raise ScanError("Use a 1..120 second command timeout")
    if type(threshold) not in (int, float) or not 0 <= threshold < 100: raise ScanError("Invalid improvement threshold")
    for key in ("check", "measure"):
        command = specification.get(key)
        if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
            raise ScanError("Supply check and measure argument arrays")
    initial = {"baseline": tree_identity(baseline), "candidate": tree_identity(candidate)}
    result = {"schema": "scan.experiment/1", "status": "EXPERIMENTAL_CANDIDATE", "specification": specification,
              "identities_before": initial, "checks": {}, "trials": [],
              "scope": "User-provided checks and measured commands only. Fresh-copy construction excluded; process startup included. No deployment performed.",
              "isolation": "Disposable working copies, not an OS security sandbox; commands require trusted user authorization"}
    def valid(run): return run["status"] == "COMPLETED" and run["exit_code"] == 0 and not run["truncated"]
    started = time.monotonic()
    def execute(command, folder):
        remaining = budget - (time.monotonic() - started)
        if remaining <= 0: raise ScanError("Experiment total time budget exhausted")
        return run_command(command, folder, min(timeout, remaining))
    try:
        with tempfile.TemporaryDirectory(prefix="scan-experiment-", dir=output.parent if output.parent.exists() else None) as temporary:
            work = Path(temporary)
            for name, source in (("baseline", baseline), ("candidate", candidate)):
                folder = work / (name + "-check")
                copy_source(source, folder)
                result["checks"][name] = execute(specification["check"], folder)
            if not all(valid(run) for run in result["checks"].values()):
                result["status"] = "CHECK_FAILED"
            else:
                # One discarded warmup, followed by alternating-order matched trials.
                for trial in range(-1, repeats):
                    row = {"trial": trial, "warmup": trial == -1}
                    order = [("baseline", baseline), ("candidate", candidate)]
                    if trial % 2: order.reverse()
                    for name, source in order:
                        folder = work / (name + "-" + str(trial))
                        copy_source(source, folder)
                        row[name] = execute(specification["measure"], folder)
                    result["trials"].append(row)
                    if not all(valid(row[name]) for name in ("baseline", "candidate")):
                        result["status"] = "MEASUREMENT_FAILED"
                        break
                    if specification.get("compare_stdout", True) and row["baseline"]["stdout_sha256"] != row["candidate"]["stdout_sha256"]:
                        result["status"] = "OUTPUT_MISMATCH"
                        break
                else:
                    old = [r["baseline"]["seconds"] for r in result["trials"] if not r["warmup"]]
                    new = [r["candidate"]["seconds"] for r in result["trials"] if not r["warmup"]]
                    before, after = statistics.median(old), statistics.median(new)
                    gain = 100 * (before - after) / before
                    # Require benefit in every paired sample as a conservative noise gate.
                    consistent = all(c < b for b, c in zip(old, new))
                    result["measurement"] = {"baseline_median_seconds": before, "candidate_median_seconds": after,
                                             "improvement_percent": gain, "every_pair_improved": consistent}
                    result["status"] = "VERIFIED_WITHIN_DECLARED_CHECK_SCOPE" if gain >= threshold and consistent else "NO_SUPPORTED_IMPROVEMENT"
    except (OSError, ValueError) as exc:
        result["status"] = "BLOCKED"
        result["error"] = str(exc)
    finally:
        result["identities_after"] = {"baseline": tree_identity(baseline), "candidate": tree_identity(candidate)}
        if result["identities_after"] != initial: result["status"] = "SOURCE_CHANGED"
        write_json(output, result)
    return result
