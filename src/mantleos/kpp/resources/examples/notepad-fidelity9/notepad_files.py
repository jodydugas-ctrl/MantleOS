"""Round 6: N-FILE-SESSION (Neutral) — file association and persistence.

Only the WH-COMMAND-GUARD may dispatch untrusted file intents here. This is
not a standalone security sandbox: its methods are trusted implementation
APIs. The GUI asks for human confirmation, then submits explicit proof flags
that the WhiteHole checks before any destructive change.

Plain-text UTF-8 files only. Writes are prepared in a sibling temporary file
and atomically replace their target when supported by the host filesystem.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import tempfile

from notepad_document import DocumentSnapshot, NeutralDocument
from notepad_history import NeutralEditHistory


class FileSessionError(ValueError):
    """File or association change rejected; no successful save was recorded."""


@dataclass(frozen=True)
class FileSessionSnapshot:
    path: str | None


class NeutralFileSession:
    """Neutral N-FILE-SESSION: owns active file association and disk I/O."""

    anchor_id = "N-FILE-SESSION"
    canonical_type = "Neutral"

    def __init__(self, document: NeutralDocument, history: NeutralEditHistory) -> None:
        if not isinstance(document, NeutralDocument):
            raise TypeError("file session requires N-DOCUMENT")
        if not isinstance(history, NeutralEditHistory):
            raise TypeError("file session requires N-EDIT-HISTORY")
        history.validate_for(document)
        self._document = document
        self._history = history
        self._path: str | None = None
        self._expected_hash: str | None = None

    def snapshot(self) -> FileSessionSnapshot:
        return FileSessionSnapshot(self._path)

    def validate_for(self, document: NeutralDocument, history: NeutralEditHistory) -> None:
        if document is not self._document or history is not self._history:
            raise FileSessionError("file session belongs to another document/history")
        history.validate_for(document)

    @staticmethod
    def require_path(path: object) -> str:
        """Explicit absolute regular-file destination/source only."""
        if type(path) is not str or not path or "\x00" in path or not os.path.isabs(path):
            raise FileSessionError("file path must be an absolute nonempty string")
        normalized = os.path.abspath(path)
        if os.path.isdir(normalized):
            raise FileSessionError("a directory cannot be used as a text file")
        return normalized

    def new_document(self) -> DocumentSnapshot:
        snapshot = self._document.load_clean_text("")
        self._history.reset_for_document_load(self._document)
        self._path = None
        self._expected_hash = None
        return snapshot

    def open_file(self, path: str) -> DocumentSnapshot:
        normalized = self.require_path(path)
        try:
            # Read/decode completely before mutating any document/session state.
            with open(normalized, "rb") as handle:
                data = handle.read()
            text = data.decode("utf-8")
        except (OSError, UnicodeError) as exc:
            raise FileSessionError(f"cannot open UTF-8 text file: {exc}") from exc
        snapshot = self._document.load_clean_text(text)
        self._history.reset_for_document_load(self._document)
        self._path = normalized
        self._expected_hash = hashlib.sha256(data).hexdigest()
        return snapshot

    def save_file(self) -> DocumentSnapshot:
        if self._path is None:
            raise FileSessionError("untitled document requires Save As")
        return self._write(self._path, overwrite=True)

    def save_file_as(self, path: str, overwrite: bool) -> DocumentSnapshot:
        return self._write(self.require_path(path), overwrite=overwrite)

    def _write(self, path: str, overwrite: bool) -> DocumentSnapshot:
        if type(overwrite) is not bool:
            raise FileSessionError("overwrite confirmation must be a boolean")
        path = self.require_path(path)
        snapshot = self._document.snapshot()
        data = snapshot.text.encode("utf-8")
        temporary: str | None = None
        try:
            # Reject symlink targets and refuse to overwrite an unknown file
            # without an explicit overwrite grant from the GUI/operator.
            if os.path.islink(path):
                raise FileSessionError("refusing to overwrite a symbolic link")
            exists = os.path.exists(path)
            if exists and not os.path.isfile(path):
                raise FileSessionError("target is not a regular file")
            if exists and not overwrite:
                raise FileSessionError("existing file requires overwrite confirmation")
            if path == self._path and self._expected_hash is not None:
                if not exists:
                    raise FileSessionError("the original file disappeared since opening/saving")
                with open(path, "rb") as handle:
                    current_hash = hashlib.sha256(handle.read()).hexdigest()
                if current_hash != self._expected_hash:
                    raise FileSessionError("file changed externally; use Save As to another path")
            folder = os.path.dirname(path)
            if not os.path.isdir(folder):
                raise FileSessionError("destination folder does not exist")
            with tempfile.NamedTemporaryFile(mode="wb", dir=folder, prefix=".anchornotepad-",
                                             suffix=".tmp", delete=False) as handle:
                temporary = handle.name
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
            temporary = None
        except (OSError, UnicodeError) as exc:
            raise FileSessionError(f"unable to save file: {exc}") from exc
        finally:
            if temporary is not None:
                try:
                    os.unlink(temporary)
                except OSError:
                    pass
        # No clean baseline or file association until the host confirms a write.
        self._path = path
        self._expected_hash = hashlib.sha256(data).hexdigest()
        return self._document.mark_saved(snapshot.revision)
