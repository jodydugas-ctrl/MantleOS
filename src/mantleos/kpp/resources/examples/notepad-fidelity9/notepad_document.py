"""Notepad Round 2: N-DOCUMENT (Neutral).

Owns an in-memory plain-text document. A valid internal call updates document
state atomically; it does not interpret raw BlackHole intents, authorize a
user command, read/write files, or drive a UI. WH-COMMAND-GUARD authorizes untrusted command dispatch before this
Anchor changes state. N-FILE-SESSION invokes trusted baseline hooks.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentSnapshot:
    """Immutable observation of the document's current state."""
    text: str
    revision: int
    dirty: bool


class NeutralDocument:
    """Neutral N-DOCUMENT: the sole owner of document content and baseline."""

    anchor_id = "N-DOCUMENT"
    canonical_type = "Neutral"

    def __init__(self, initial_text: str = "") -> None:
        if not isinstance(initial_text, str):
            raise TypeError("initial_text must be a string")
        self._text = initial_text
        self._baseline_text = initial_text
        self._revision = 0

    def snapshot(self) -> DocumentSnapshot:
        """Return a point-in-time value; do not expose mutable state."""
        return DocumentSnapshot(
            text=self._text,
            revision=self._revision,
            dirty=self._text != self._baseline_text,
        )

    def replace_text(self, text: str) -> DocumentSnapshot:
        """Replace the content. Identical content is a no-op."""
        self._require_text(text)
        self._commit(text)
        return self.snapshot()

    def insert_text(self, offset: int, text: str) -> DocumentSnapshot:
        """Insert Unicode text at a code-point offset in the current text."""
        self._require_index(offset, "offset")
        self._require_text(text)
        if offset > len(self._text):
            raise ValueError("offset is beyond the end of the document")
        self._commit(self._text[:offset] + text + self._text[offset:])
        return self.snapshot()

    def delete_range(self, start: int, end: int) -> DocumentSnapshot:
        """Delete Unicode code points in the half-open range [start, end)."""
        self._require_index(start, "start")
        self._require_index(end, "end")
        if start > end or end > len(self._text):
            raise ValueError("invalid document range")
        self._commit(self._text[:start] + self._text[end:])
        return self.snapshot()

    def load_clean_text(self, text: str) -> DocumentSnapshot:
        """Trusted internal API: replace with the content of a new/opened file.

        Reset the clean baseline, maintaining sole ownership of text/revision.
        The caller must reset the bound edit history after this transaction.
        """
        self._require_text(text)
        self._commit(text)
        self._baseline_text = text
        return self.snapshot()

    def mark_saved(self, expected_revision: int) -> DocumentSnapshot:
        """Trusted internal API: acknowledge a completed write of this revision."""
        if type(expected_revision) is not int or expected_revision != self._revision:
            raise ValueError("document changed during save")
        self._baseline_text = self._text
        return self.snapshot()

    @staticmethod
    def _require_text(text: str) -> None:
        if not isinstance(text, str):
            raise TypeError("text must be a string")

    @staticmethod
    def _require_index(index: int, label: str) -> None:
        if type(index) is not int:
            raise TypeError(f"{label} must be an integer")
        if index < 0:
            raise ValueError(f"{label} must be nonnegative")

    def _commit(self, updated: str) -> None:
        if updated != self._text:
            self._text = updated
            self._revision += 1
