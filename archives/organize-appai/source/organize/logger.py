from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from platformdirs import user_log_dir

logger = logging.getLogger(name="organize")


def workspace_log_dir(start: str | Path = ".") -> Path | None:
    """Use project-local logs when a self-consistent workspace marker is present."""

    configured = os.environ.get("ORGANIZE_APPAI_WORKSPACE")
    current = Path(configured or start).resolve()
    candidates = (current,) if configured else (current, *current.parents)
    for candidate in candidates:
        marker = candidate / "WORKSPACE.txt"
        if not marker.is_file():
            continue
        try:
            recorded = Path(marker.read_text(encoding="utf-8").strip()).resolve()
        except OSError:
            continue
        if recorded == candidate:
            return candidate / "logs" / "organize"
    return None


def enable_logfile():
    local = workspace_log_dir()
    logdir = local or Path(user_log_dir(appname="organize", ensure_exists=True))
    logdir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            RotatingFileHandler(
                filename=logdir / "organize-errors.log",
                backupCount=5,
                maxBytes=5_000_000,
            )
        ],
    )
