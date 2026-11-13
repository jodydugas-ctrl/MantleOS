"""Round 8: N-SEARCH-REPLACE (Neutral).

Document/history-bound, stateless literal substring search and replacement
semantics. WH validates every untrusted request and authorizes edits. This
Anchor never owns document text, revision, clean baseline, or undo history.
"""
from dataclasses import dataclass
import re

from notepad_document import DocumentSnapshot, NeutralDocument
from notepad_history import NeutralEditHistory


class SearchOperationError(ValueError):
    """Search parameters or a requested match are invalid."""


@dataclass(frozen=True)
class MatchRange:
    start: int
    end: int


@dataclass(frozen=True)
class ReplaceResult:
    snapshot: DocumentSnapshot
    count: int


class NeutralSearchReplace:
    """N-SEARCH-REPLACE: calculate literal matches, not document state."""

    anchor_id = "N-SEARCH-REPLACE"
    canonical_type = "Neutral"

    def __init__(self, document: NeutralDocument, history: NeutralEditHistory):
        if not isinstance(document, NeutralDocument):
            raise TypeError("search requires N-DOCUMENT")
        if not isinstance(history, NeutralEditHistory):
            raise TypeError("search requires N-EDIT-HISTORY")
        history.validate_for(document)
        self._document = document
        self._history = history

    def validate_for(self, document: NeutralDocument, history: NeutralEditHistory):
        if document is not self._document or history is not self._history:
            raise SearchOperationError("search belongs to another document/history")
        history.validate_for(document)

    @staticmethod
    def _pattern(query: str, match_case: bool) -> re.Pattern:
        if type(query) is not str or not query:
            raise SearchOperationError("search query must be nonempty plain text")
        if type(match_case) is not bool:
            raise SearchOperationError("match_case must be a boolean")
        return re.compile(re.escape(query), 0 if match_case else re.IGNORECASE)

    @classmethod
    def find(cls, snapshot: DocumentSnapshot, query: str, start: int,
             match_case: bool, wrap: bool, backwards: bool = False) -> MatchRange | None:
        """Find next/previous non-overlapping literal occurrence, with wrap."""
        if not isinstance(snapshot, DocumentSnapshot):
            raise SearchOperationError("expected document snapshot")
        if type(start) is not int or not 0 <= start <= len(snapshot.text):
            raise SearchOperationError("start must be a valid document codepoint offset")
        if type(wrap) is not bool or type(backwards) is not bool:
            raise SearchOperationError("wrap/backwards must be booleans")
        pattern = cls._pattern(query, match_case)
        matches = tuple(pattern.finditer(snapshot.text))
        if backwards:
            chosen = next((m for m in reversed(matches) if m.end() <= start), None)
            if chosen is None and wrap:
                chosen = next((m for m in reversed(matches) if m.end() > start), None)
        else:
            chosen = next((m for m in matches if m.start() >= start), None)
            if chosen is None and wrap:
                chosen = next((m for m in matches if m.start() < start), None)
        return MatchRange(chosen.start(), chosen.end()) if chosen is not None else None

    @classmethod
    def selected_match(cls, snapshot: DocumentSnapshot, query: str,
                       start: int, end: int, match_case: bool) -> bool:
        pattern = cls._pattern(query, match_case)
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(snapshot.text):
            raise SearchOperationError("replacement requires a valid selected match")
        return pattern.fullmatch(snapshot.text[start:end]) is not None

    @classmethod
    def replace_all_text(cls, snapshot: DocumentSnapshot, query: str,
                         replacement: str, match_case: bool) -> tuple[str, int]:
        if not isinstance(snapshot, DocumentSnapshot):
            raise SearchOperationError("expected document snapshot")
        if type(replacement) is not str:
            raise SearchOperationError("replacement must be plain text")
        pattern = cls._pattern(query, match_case)
        # Lambda avoids interpreting replacement as a regex substitution template.
        return pattern.subn(lambda _match: replacement, snapshot.text)
