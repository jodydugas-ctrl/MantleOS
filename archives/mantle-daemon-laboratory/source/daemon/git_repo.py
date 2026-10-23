from __future__ import annotations

import subprocess
from pathlib import Path


class StaleCheckpoint(RuntimeError):
    pass


class GitRepo:
    def __init__(self, root: Path):
        self.root = Path(root)

    def _run(self, *args: str, check: bool = True) -> str:
        # The laboratory may be created by a sandbox identity and later exercised by
        # the desktop user. Scope Git's trust exception to this exact repository rather
        # than mutating global configuration.
        command = ["git", "-c", f"safe.directory={self.root.resolve()}", *args]
        proc = subprocess.run(command, cwd=self.root, text=True, capture_output=True)
        if check and proc.returncode:
            raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "git failed")
        if not check and proc.returncode:
            return ""
        return proc.stdout.strip()

    def init_birth(self) -> str:
        if not (self.root / ".git").exists():
            self._run("init", "-q")
            self._run("config", "user.email", "daemon-lab@example.invalid")
            self._run("config", "user.name", "Mantle Daemon Laboratory")
        if not self.head():
            self._run("add", "--", ".")
            self._run("commit", "-qm", "birth: initialize laboratory specimen")
        return self.head()

    def head(self) -> str:
        return self._run("rev-parse", "HEAD", check=False)

    def status(self) -> list[str]:
        text = self._run("status", "--porcelain", check=False)
        return [line for line in text.splitlines() if line]

    def commit(self, paths: list[str], message: str, expected_parent: str | None = None) -> str:
        current = self.head()
        if expected_parent is not None and current != expected_parent:
            raise StaleCheckpoint(f"expected parent {expected_parent}, repository is at {current}")
        if not paths:
            raise ValueError("checkpoint needs at least one path")
        self._run("add", "--", *paths)
        staged = self._run("diff", "--cached", "--name-only")
        if not staged:
            raise ValueError("checkpoint has no staged changes")
        self._run("commit", "-qm", message)
        return self.head()

    def changed_paths(self, parent: str) -> list[str]:
        text = self._run("diff", "--name-only", parent, "HEAD")
        return [line for line in text.splitlines() if line]
