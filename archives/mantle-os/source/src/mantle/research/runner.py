"""Shared bounded subprocess boundary for skills and research."""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
from typing import Dict, Iterable, List, Optional


class BoundedProcessError(RuntimeError):
    """The process could not be run within the declared boundary."""


@dataclass(frozen=True)
class ProcessBudget:
    wall_seconds: float
    cpu_seconds: int
    memory_bytes: int
    output_bytes: int
    file_count: int | None = None

    def validate(self) -> None:
        if self.wall_seconds <= 0 or self.cpu_seconds <= 0:
            raise ValueError("process time budgets must be positive")
        if self.memory_bytes <= 0 or self.output_bytes <= 0:
            raise ValueError("process memory/output budgets must be positive")
        if self.file_count is not None and self.file_count < 0:
            raise ValueError("file_count cannot be negative")


@dataclass(frozen=True)
class ProcessResult:
    returncode: int | None
    stdout: bytes
    stderr: bytes
    timed_out: bool
    output_limited: bool
    changed_paths: tuple[str, ...]
    network_isolated: bool

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out and not self.output_limited


def _census(root: Path) -> set[str]:
    if not root.exists():
        return set()
    return {str(path.relative_to(root)) for path in root.rglob("*") if path.is_file()}


class BoundedProcessRunner:
    """Run one argv in a caller-owned workspace with no inherited environment."""

    def __init__(self, *, allowed_env: Iterable[str] = ()) -> None:
        self.allowed_env = frozenset(allowed_env)

    def run(self, argv: List[str], *, cwd: str | Path, env: Optional[Dict[str, str]],
            budget: ProcessBudget, network: bool = False,
            require_network_isolation: bool = False) -> ProcessResult:
        budget.validate()
        if not argv or any(not isinstance(item, str) or not item for item in argv):
            raise ValueError("argv must be a non-empty list of strings")
        workspace = Path(cwd).resolve()
        if not workspace.is_dir():
            raise ValueError("process workspace is not a directory")
        if env is None:
            raise ValueError("process environment must be explicit")
        unknown_env = set(env) - self.allowed_env
        if unknown_env:
            raise ValueError("environment key(s) not allowlisted: %s" % sorted(unknown_env))
        # Python's standard library cannot deny network on Windows without a job/firewall
        # policy supplied by the host. Refuse callers that demand that stronger promise.
        network_isolated = os.name == "posix"
        if require_network_isolation and not network_isolated:
            raise BoundedProcessError("network isolation is unavailable on this platform")
        before = _census(workspace)
        child_env = {key: str(value) for key, value in env.items()}
        kwargs = {
            "cwd": str(workspace), "env": child_env, "stdin": subprocess.DEVNULL,
            "stdout": subprocess.PIPE, "stderr": subprocess.PIPE,
        }
        if os.name == "posix":
            def limits():
                import resource
                resource.setrlimit(resource.RLIMIT_CPU, (budget.cpu_seconds, budget.cpu_seconds))
                resource.setrlimit(resource.RLIMIT_AS, (budget.memory_bytes, budget.memory_bytes))
            kwargs["preexec_fn"] = limits
            kwargs["start_new_session"] = True
        elif os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        proc = subprocess.Popen(argv, **kwargs)
        stdout_buf = bytearray()
        stderr_buf = bytearray()
        overflow = threading.Event()

        def drain(stream, target):
            while True:
                chunk = stream.read(8192)
                if not chunk:
                    return
                if len(target) < budget.output_bytes:
                    target.extend(chunk[:budget.output_bytes - len(target)])
                if len(target) >= budget.output_bytes or len(chunk) > budget.output_bytes:
                    overflow.set()

        threads = [threading.Thread(target=drain, args=(proc.stdout, stdout_buf), daemon=True),
                   threading.Thread(target=drain, args=(proc.stderr, stderr_buf), daemon=True)]
        for thread in threads:
            thread.start()
        timed_out = False
        try:
            proc.wait(timeout=budget.wall_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            self._terminate(proc)
            proc.wait(timeout=5)
        for thread in threads:
            thread.join(timeout=5)
        after = _census(workspace)
        changed = tuple(sorted(before.symmetric_difference(after)))
        return ProcessResult(proc.returncode, bytes(stdout_buf), bytes(stderr_buf),
                             timed_out, overflow.is_set(), changed, network_isolated)

    @staticmethod
    def _terminate(proc: subprocess.Popen) -> None:
        if proc.poll() is not None:
            return
        if os.name == "posix":
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        else:
            proc.kill()
