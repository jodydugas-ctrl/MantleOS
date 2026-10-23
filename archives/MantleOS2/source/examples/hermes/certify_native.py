"""Compare focused native Hermes behavior before and after direct innervation."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

TESTS = (
    "tests/agent/test_turn_context.py",
    "tests/agent/test_turn_finalizer_iteration_limit_exit.py",
    "tests/agent/test_turn_finalizer_interrupt_alternation.py",
    "tests/agent/test_turn_finalizer_final_response_persistence.py",
    "tests/agent/test_turn_finalizer_cleanup_guard.py",
    "tests/agent/test_tool_executor_checkpoint_paths.py",
    "tests/run_agent/test_authorization_gate.py",
    "tests/cli/test_single_query_session_finalize.py",
    "tests/cli/test_session_boundary_hooks.py",
    "tests/tui_gateway/test_finalize_session_persist.py",
    "tests/gateway/test_finalize_session_off_loop.py",
    "tests/hermes_cli/test_lifecycle.py",
)

PROVIDER_ENVIRONMENT_KEYS = (
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _validate(pristine: Path, constructed: Path, expected_commit: str) -> None:
    for label, root in (("pristine", pristine), ("constructed", constructed)):
        if not root.is_dir():
            raise SystemExit(f"{label} checkout is missing: {root}")
        if _git(root, "rev-parse", "HEAD") != expected_commit:
            raise SystemExit(f"{label} checkout is not at the certified commit")
        missing = [relative for relative in TESTS if not (root / relative).is_file()]
        if missing:
            raise SystemExit(f"{label} checkout is missing test: {missing[0]}")
    if (pristine / "mantle").exists():
        raise SystemExit("pristine checkout unexpectedly contains Mantle tissue")
    if not (constructed / "mantle" / "ASSIMILATION.json").is_file():
        raise SystemExit("constructed checkout is missing Mantle tissue")


def _run(label: str, root: Path, temp_root: Path) -> dict[str, object]:
    base_temp = temp_root / label
    environment = dict(os.environ)
    for key in PROVIDER_ENVIRONMENT_KEYS:
        environment.pop(key, None)
    environment["TEMP"] = str(temp_root)
    environment["TMP"] = str(temp_root)
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "--basetemp",
        str(base_temp),
        *TESTS,
    ]
    completed = subprocess.run(
        command,
        cwd=root,
        env=environment,
        text=True,
        capture_output=True,
    )
    output = "\n".join(part.strip() for part in (completed.stdout, completed.stderr) if part.strip())
    return {
        "checkout": label,
        "exit_code": completed.returncode,
        "passed": completed.returncode == 0,
        "summary": output[-2_000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pristine", type=Path)
    parser.add_argument("constructed", type=Path)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    pristine = args.pristine.resolve()
    constructed = args.constructed.resolve()
    _validate(pristine, constructed, args.expected_commit)

    with tempfile.TemporaryDirectory(prefix="mantle-hermes-native-") as temporary:
        temp_root = Path(temporary)
        results = [
            _run("pristine", pristine, temp_root),
            _run("constructed", constructed, temp_root),
        ]
    report = {
        "schema": "mantle.hermes-native-certification.v2",
        "commit": args.expected_commit,
        "test_files": list(TESTS),
        "results": results,
        "equivalent": all(result["passed"] for result in results),
        "provider_credentials_forwarded": False,
        "birth_performed": False,
    }
    rendered = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["equivalent"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
