"""Notepad Round 8: WH-COMMAND-GUARD (WhiteHole).

BH-EDITOR-INPUT => WH-COMMAND-GUARD => N-DOCUMENT, optionally coordinating
N-EDIT-HISTORY, N-FILE-SESSION, N-CLIPBOARD-SELECTION and N-SEARCH-REPLACE. Direct Neutral methods are trusted
internal APIs and are not security barriers; the host/UI routes untrusted
commands through this WhiteHole. Only validated, opt-in file operations
and clipboard effects are authorized; network effects remain denied.
"""

from notepad_document import DocumentSnapshot, NeutralDocument
from notepad_history import HistoryConflict, NeutralEditHistory
from notepad_files import FileSessionError, NeutralFileSession
from notepad_clipboard import ClipboardOperationError, NeutralClipboardSelection, SelectionRange
from notepad_search import MatchRange, NeutralSearchReplace, ReplaceResult, SearchOperationError
from notepad_input import EditorIntent


class CommandRejected(ValueError):
    """The command was not authorized; no document update was requested."""


class WhiteHoleCommandGuard:
    """WhiteHole WH-COMMAND-GUARD: validate, authorize, dispatch."""

    anchor_id = "WH-COMMAND-GUARD"
    canonical_type = "WhiteHole"
    supported_actions = frozenset({"edit", "insert", "delete", "read", "undo", "redo", "new", "open", "save", "save-as", "copy", "cut", "paste", "select-all", "find", "replace-one", "replace-all"})

    def execute(
        self,
        intent: EditorIntent,
        document: NeutralDocument,
        history: NeutralEditHistory | None = None,
        file_session: NeutralFileSession | None = None,
        clipboard: NeutralClipboardSelection | None = None,
        search: NeutralSearchReplace | None = None,
    ) -> DocumentSnapshot | SelectionRange | MatchRange | ReplaceResult | None:
        """Process one validated in-memory command with optional undo history.

        Backward compatible: edit/insert/delete/read without a history behave
        exactly as in Round 3. Undo/redo require a bound, current history.
        Clipboard commands require an explicitly bound N-CLIPBOARD-SELECTION.
        """
        if not isinstance(intent, EditorIntent):
            raise CommandRejected("expected a captured EditorIntent")
        if not isinstance(document, NeutralDocument):
            raise CommandRejected("expected an N-DOCUMENT owner")
        action = intent.action
        if type(action) is not str or action not in self.supported_actions:
            raise CommandRejected("unsupported editor command")
        if history is not None and not isinstance(history, NeutralEditHistory):
            raise CommandRejected("expected N-EDIT-HISTORY")

        payload = intent.payload
        if action in ("find", "replace-one", "replace-all"):
            if history is None or not isinstance(search, NeutralSearchReplace):
                raise CommandRejected("search actions require an explicitly bound search owner")
            try:
                search.validate_for(document, history)
            except (SearchOperationError, HistoryConflict) as exc:
                raise CommandRejected(str(exc)) from exc
            before = document.snapshot()
            if action == "find":
                self._require_fields(payload, {"query", "start", "match_case", "wrap", "backwards"})
                self._require_index(payload["start"], "start")
                if payload["start"] > len(before.text):
                    raise CommandRejected("search start exceeds document length")
                self._require_bool(payload["match_case"], "find.match_case")
                self._require_bool(payload["wrap"], "find.wrap")
                self._require_bool(payload["backwards"], "find.backwards")
                try:
                    return search.find(before, payload["query"], payload["start"],
                                       payload["match_case"], payload["wrap"], payload["backwards"])
                except SearchOperationError as exc:
                    raise CommandRejected(str(exc)) from exc
            if action == "replace-one":
                self._require_fields(payload, {"query", "replacement", "start", "end", "match_case"})
                self._require_index(payload["start"], "start")
                self._require_index(payload["end"], "end")
                if type(payload["replacement"]) is not str:
                    raise CommandRejected("replacement must be plain text")
                try:
                    matched = search.selected_match(before, payload["query"], payload["start"],
                                                    payload["end"], payload["match_case"])
                except SearchOperationError as exc:
                    raise CommandRejected(str(exc)) from exc
                if not matched:
                    raise CommandRejected("selected text does not match the search query")
                after = document.replace_text(before.text[:payload["start"]]
                                              + payload["replacement"] + before.text[payload["end"]:])
                history.record_transition(before, after)
                return ReplaceResult(after, 1)
            self._require_fields(payload, {"query", "replacement", "match_case"})
            self._require_bool(payload["match_case"], "replace-all.match_case")
            try:
                updated, count = search.replace_all_text(before, payload["query"],
                                                         payload["replacement"], payload["match_case"])
            except SearchOperationError as exc:
                raise CommandRejected(str(exc)) from exc
            after = document.replace_text(updated)
            history.record_transition(before, after)
            return ReplaceResult(after, count)
        if action in ("copy", "cut", "paste", "select-all"):
            if history is None or not isinstance(clipboard, NeutralClipboardSelection):
                raise CommandRejected("clipboard actions require an explicitly bound clipboard selection")
            try:
                clipboard.validate_for(document, history)
            except (ClipboardOperationError, HistoryConflict) as exc:
                raise CommandRejected(str(exc)) from exc
            before = document.snapshot()
            if action == "select-all":
                if payload is not None:
                    raise CommandRejected("select-all takes no payload")
                return clipboard.select_all(before)
            self._require_fields(payload, {"start", "end"})
            start, end = payload["start"], payload["end"]
            self._require_index(start, "start")
            self._require_index(end, "end")
            if start > end or end > len(before.text):
                raise CommandRejected("invalid clipboard selection range")
            if action in ("copy", "cut") and start == end:
                raise CommandRejected("copy/cut requires selected text")
            try:
                if action == "paste":
                    inserted = clipboard.read_selection_text()
                else:
                    # Before Cut changes text, the host must confirm copying.
                    clipboard.write_selection(before, SelectionRange(start, end))
                # Host callbacks are externally supplied. Recheck state after
                # effects, preventing edits to a stale range/history.
                history.validate_for(document)
                if document.snapshot() != before:
                    raise CommandRejected("document changed during clipboard operation")
            except (ClipboardOperationError, HistoryConflict) as exc:
                raise CommandRejected(str(exc)) from exc
            if action == "copy":
                return before
            if action == "cut":
                after = document.delete_range(start, end)
            else:
                after = document.replace_text(before.text[:start] + inserted + before.text[end:])
            history.record_transition(before, after)
            return after
        if action in ("new", "open", "save", "save-as"):
            if history is None or file_session is None or not isinstance(file_session, NeutralFileSession):
                raise CommandRejected("file operations require an explicitly bound file session")
            try:
                file_session.validate_for(document, history)
            except (FileSessionError, HistoryConflict) as exc:
                raise CommandRejected(str(exc)) from exc
            if action == "new":
                self._require_fields(payload, {"discard"})
                self._require_bool(payload["discard"], "new.discard")
                if document.snapshot().dirty and not payload["discard"]:
                    raise CommandRejected("unsaved changes require confirmed discard")
                return file_session.new_document()
            if action == "open":
                self._require_fields(payload, {"path", "discard"})
                self._require_bool(payload["discard"], "open.discard")
                if document.snapshot().dirty and not payload["discard"]:
                    raise CommandRejected("unsaved changes require confirmed discard")
                path = self._require_path(payload["path"])
                try:
                    return file_session.open_file(path)
                except FileSessionError as exc:
                    raise CommandRejected(str(exc)) from exc
            if action == "save":
                if payload is not None:
                    raise CommandRejected("save takes no payload")
                try:
                    return file_session.save_file()
                except FileSessionError as exc:
                    raise CommandRejected(str(exc)) from exc
            self._require_fields(payload, {"path", "overwrite"})
            self._require_bool(payload["overwrite"], "save-as.overwrite")
            path = self._require_path(payload["path"])
            try:
                return file_session.save_file_as(path, payload["overwrite"])
            except FileSessionError as exc:
                raise CommandRejected(str(exc)) from exc

        if action in ("undo", "redo", "read"):
            if payload is not None:
                raise CommandRejected(f"{action} takes no payload")
            if action == "read":
                return document.snapshot()
            if history is None:
                raise CommandRejected(f"{action} requires editing history")
            try:
                history.validate_for(document)
                return history.undo() if action == "undo" else history.redo()
            except HistoryConflict as exc:
                raise CommandRejected(str(exc)) from exc

        # Validate the entire command payload before requesting any state change.
        if action == "edit":
            if type(payload) is not str:
                raise CommandRejected("edit requires plain text")
        elif action == "insert":
            self._require_fields(payload, {"offset", "text"})
            self._require_index(payload["offset"], "offset")
            if type(payload["text"]) is not str:
                raise CommandRejected("insert.text must be plain text")
            if payload["offset"] > len(document.snapshot().text):
                raise CommandRejected("insert.offset exceeds document length")
        else:
            self._require_fields(payload, {"start", "end"})
            self._require_index(payload["start"], "start")
            self._require_index(payload["end"], "end")
            if payload["start"] > payload["end"] or payload["end"] > len(document.snapshot().text):
                raise CommandRejected("invalid delete range")

        if history is not None:
            try:
                history.validate_for(document)
            except HistoryConflict as exc:
                raise CommandRejected(str(exc)) from exc
        before = document.snapshot()
        if action == "edit":
            after = document.replace_text(payload)
        elif action == "insert":
            after = document.insert_text(payload["offset"], payload["text"])
        else:
            after = document.delete_range(payload["start"], payload["end"])
        if history is not None:
            history.record_transition(before, after)
        return after

    @staticmethod
    def _require_bool(value: object, label: str) -> None:
        if type(value) is not bool:
            raise CommandRejected(f"{label} must be a boolean")

    @staticmethod
    def _require_path(value: object) -> str:
        try:
            return NeutralFileSession.require_path(value)
        except FileSessionError as exc:
            raise CommandRejected(str(exc)) from exc

    @staticmethod
    def _require_fields(payload: object, expected: set[str]) -> None:
        if type(payload) is not dict or payload.keys() != expected:
            raise CommandRejected(f"payload must have exactly {sorted(expected)}")

    @staticmethod
    def _require_index(value: object, label: str) -> None:
        if type(value) is not int or value < 0:
            raise CommandRejected(f"{label} must be a nonnegative integer")
