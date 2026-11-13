"""Round 7: N-CLIPBOARD-SELECTION (Neutral).

A document-bound, host-injected clipboard interaction capability. The Anchor
interprets document-relative selections and marshals explicit clipboard
reads/writes after WH-COMMAND-GUARD authorization. It does not own document
text, undo history, or an independent text buffer. The Tk selection is
transient presentation state, not a second authoritative text owner.

The clipboard is an external host effect. A successful write acknowledgement
must precede Cut's deletion; a successful text read must precede Paste's edit.
Only the host adapter has access to the operating-system clipboard.
"""
from dataclasses import dataclass
from collections.abc import Callable

from notepad_document import DocumentSnapshot, NeutralDocument
from notepad_history import NeutralEditHistory


class ClipboardOperationError(ValueError):
    """A clipboard interaction failed; no guarded document edit was requested."""


@dataclass(frozen=True)
class SelectionRange:
    """Document-codepoint range [start, end), never an editable text copy."""
    start: int
    end: int


class NeutralClipboardSelection:
    """N-CLIPBOARD-SELECTION: selection semantics and guarded host clipboard I/O."""

    anchor_id = "N-CLIPBOARD-SELECTION"
    canonical_type = "Neutral"

    def __init__(
        self,
        document: NeutralDocument,
        history: NeutralEditHistory,
        read_text: Callable[[], str],
        write_text: Callable[[str], None],
    ) -> None:
        if not isinstance(document, NeutralDocument):
            raise TypeError("clipboard selection requires N-DOCUMENT")
        if not isinstance(history, NeutralEditHistory):
            raise TypeError("clipboard selection requires N-EDIT-HISTORY")
        history.validate_for(document)
        if not callable(read_text) or not callable(write_text):
            raise TypeError("clipboard requires readable and writable host adapters")
        self._document = document
        self._history = history
        self._read_text = read_text
        self._write_text = write_text

    def validate_for(self, document: NeutralDocument, history: NeutralEditHistory) -> None:
        if document is not self._document or history is not self._history:
            raise ClipboardOperationError("clipboard selection belongs to another document/history")
        history.validate_for(document)

    @staticmethod
    def select_all(snapshot: DocumentSnapshot) -> SelectionRange:
        if not isinstance(snapshot, DocumentSnapshot):
            raise TypeError("selection requires a document snapshot")
        return SelectionRange(0, len(snapshot.text))

    def write_selection(self, snapshot: DocumentSnapshot, selected: SelectionRange) -> None:
        """Write exactly the selected text; never modify document/history."""
        try:
            self._write_text(snapshot.text[selected.start:selected.end])
        except Exception as exc:
            raise ClipboardOperationError(f"clipboard write failed: {exc}") from exc

    def read_selection_text(self) -> str:
        """Read plain text from host; reject incompatible/missing content."""
        try:
            text = self._read_text()
        except Exception as exc:
            raise ClipboardOperationError(f"clipboard read failed: {exc}") from exc
        if type(text) is not str:
            raise ClipboardOperationError("clipboard does not contain plain text")
        return text
