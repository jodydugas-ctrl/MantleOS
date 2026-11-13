"""Round 4, N-EDIT-HISTORY (Neutral): bounded, document-bound undo/redo.

History owns the transition stacks, not document text, clean baseline, or
revision. Untrusted user intents must enter through WH-COMMAND-GUARD. This
module does not perform filesystem, clipboard, or network effects.
"""

from dataclasses import dataclass

from notepad_document import DocumentSnapshot, NeutralDocument


class HistoryConflict(ValueError):
    """History is stale, mismatched, or has no requested transition."""


@dataclass(frozen=True)
class HistorySnapshot:
    """Read-only counts and the revision of the bound document."""

    undo_count: int
    redo_count: int
    expected_revision: int


class NeutralEditHistory:
    """Neutral N-EDIT-HISTORY: owns bounded undo/redo transitions."""

    anchor_id = "N-EDIT-HISTORY"
    canonical_type = "Neutral"

    def __init__(self, document: NeutralDocument, max_entries: int = 100) -> None:
        if not isinstance(document, NeutralDocument):
            raise TypeError("history requires N-DOCUMENT")
        if type(max_entries) is not int or max_entries < 1:
            raise ValueError("max_entries must be a positive integer")
        self._document = document
        self._max_entries = max_entries
        self._undo: list[tuple[str, str]] = []
        self._redo: list[tuple[str, str]] = []
        self._expected_revision = document.snapshot().revision

    def snapshot(self) -> HistorySnapshot:
        return HistorySnapshot(len(self._undo), len(self._redo), self._expected_revision)

    def validate_for(self, document: NeutralDocument) -> None:
        """Refuse stale histories or histories attached to another document."""
        if document is not self._document:
            raise HistoryConflict("history belongs to another document")
        if document.snapshot().revision != self._expected_revision:
            raise HistoryConflict("document changed outside this history")

    def reset_for_document_load(self, document: NeutralDocument) -> None:
        """Trusted internal hook: new/open establishes a fresh edit timeline."""
        if document is not self._document:
            raise HistoryConflict("history belongs to another document")
        self._undo.clear()
        self._redo.clear()
        self._expected_revision = document.snapshot().revision

    def record_transition(self, before: DocumentSnapshot, after: DocumentSnapshot) -> None:
        """Record an already-applied, validated, document transition.

        This is a trusted internal hook, called only after WhiteHole dispatch.
        """
        if not isinstance(before, DocumentSnapshot) or not isinstance(after, DocumentSnapshot):
            raise HistoryConflict("record requires snapshots")
        if before.revision != self._expected_revision:
            raise HistoryConflict("unexpected history starting revision")
        if after != self._document.snapshot():
            raise HistoryConflict("transition does not match current document")
        if after.text == before.text:
            if after.revision != before.revision:
                raise HistoryConflict("no-op advanced the document revision")
            return
        if after.revision != before.revision + 1:
            raise HistoryConflict("edit must be a single document revision")
        self._undo.append((before.text, after.text))
        if len(self._undo) > self._max_entries:
            self._undo.pop(0)
        self._redo.clear()
        self._expected_revision = after.revision

    def undo(self) -> DocumentSnapshot:
        """Restore prior text via the document's owner; preserve its baseline."""
        self.validate_for(self._document)
        if not self._undo:
            raise HistoryConflict("nothing to undo")
        previous_text, resulting_text = self._undo[-1]
        if self._document.snapshot().text != resulting_text:
            raise HistoryConflict("document does not match recorded edit")
        result = self._document.replace_text(previous_text)
        self._undo.pop()
        self._redo.append((previous_text, resulting_text))
        self._expected_revision = result.revision
        return result

    def redo(self) -> DocumentSnapshot:
        """Reapply the most recently undone edit through N-DOCUMENT."""
        self.validate_for(self._document)
        if not self._redo:
            raise HistoryConflict("nothing to redo")
        previous_text, resulting_text = self._redo[-1]
        if self._document.snapshot().text != previous_text:
            raise HistoryConflict("document does not match recorded undo")
        result = self._document.replace_text(resulting_text)
        self._redo.pop()
        self._undo.append((previous_text, resulting_text))
        self._expected_revision = result.revision
        return result
