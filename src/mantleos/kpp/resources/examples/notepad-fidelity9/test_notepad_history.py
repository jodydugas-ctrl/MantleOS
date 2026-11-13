"""Round 4 cumulative tests: new Neutral history + old guarded pathways."""
import unittest
from dataclasses import FrozenInstanceError

from notepad_document import DocumentSnapshot, NeutralDocument
from notepad_guard import CommandRejected, WhiteHoleCommandGuard
from notepad_history import HistoryConflict, HistorySnapshot, NeutralEditHistory
from notepad_input import BlackHoleEditorInput


class TestNeutralEditHistory(unittest.TestCase):
    def setUp(self):
        self.document = NeutralDocument("one")
        self.history = NeutralEditHistory(self.document)
        self.guard = WhiteHoleCommandGuard()

    def act(self, action, payload=None, history=None):
        return self.guard.execute(
            BlackHoleEditorInput.receive(action, payload),
            self.document,
            self.history if history is None else history,
        )

    def test_identity_and_owner(self):
        self.assertEqual(self.history.anchor_id, "N-EDIT-HISTORY")
        self.assertEqual(self.history.canonical_type, "Neutral")
        self.assertFalse(hasattr(self.history, "_text"))
        self.assertFalse(hasattr(self.history, "_baseline_text"))

    def test_single_edit_undo_redo(self):
        self.assertEqual(self.act("edit", "two"), DocumentSnapshot("two", 1, True))
        self.assertEqual(self.history.snapshot(), HistorySnapshot(1, 0, 1))
        self.assertEqual(self.act("undo"), DocumentSnapshot("one", 2, False))
        self.assertEqual(self.history.snapshot(), HistorySnapshot(0, 1, 2))
        self.assertEqual(self.act("redo"), DocumentSnapshot("two", 3, True))
        self.assertEqual(self.history.snapshot(), HistorySnapshot(1, 0, 3))

    def test_undo_multiple_edits_in_reverse_order(self):
        self.act("insert", {"offset": 3, "text": "!"})
        self.act("delete", {"start": 0, "end": 1})
        self.act("edit", "DONE")
        self.assertEqual(self.act("undo").text, "ne!")
        self.assertEqual(self.act("undo").text, "one!")
        self.assertEqual(self.act("undo").text, "one")
        self.assertFalse(self.document.snapshot().dirty)
        self.assertEqual(self.act("redo").text, "one!")

    def test_new_edit_invalidates_redo(self):
        self.act("edit", "two")
        self.act("undo")
        self.act("edit", "three")
        self.assertEqual(self.history.snapshot().redo_count, 0)
        before = self.document.snapshot()
        with self.assertRaises(CommandRejected):
            self.act("redo")
        self.assertEqual(self.document.snapshot(), before)

    def test_noop_edit_does_not_enter_history(self):
        self.act("edit", "one")
        self.act("insert", {"offset": 0, "text": ""})
        self.act("delete", {"start": 2, "end": 2})
        self.assertEqual(self.history.snapshot(), HistorySnapshot(0, 0, 0))

    def test_invalid_command_preserves_both_anchors(self):
        self.act("edit", "two")
        before_doc = self.document.snapshot()
        before_hist = self.history.snapshot()
        for action, payload in (
            ("save", None),
            ("insert", {"offset": -1, "text": "hi"}),
            ("undo", "unexpected"),
            ("delete", {"start": 3, "end": 2}),
        ):
            with self.subTest(action=action):
                with self.assertRaises(CommandRejected):
                    self.act(action, payload)
                self.assertEqual(self.document.snapshot(), before_doc)
                self.assertEqual(self.history.snapshot(), before_hist)

    def test_empty_undo_and_redo_reject_atomically(self):
        for action in ("undo", "redo"):
            before = self.document.snapshot(), self.history.snapshot()
            with self.assertRaises(CommandRejected):
                self.act(action)
            self.assertEqual((self.document.snapshot(), self.history.snapshot()), before)

    def test_undo_requires_history(self):
        before = self.document.snapshot()
        with self.assertRaises(CommandRejected):
            self.guard.execute(BlackHoleEditorInput.receive("undo"), self.document)
        self.assertEqual(self.document.snapshot(), before)

    def test_other_document_history_rejected(self):
        other = NeutralEditHistory(NeutralDocument("another"))
        before = self.document.snapshot()
        with self.assertRaises(CommandRejected):
            self.act("edit", "not accepted", other)
        self.assertEqual(self.document.snapshot(), before)
        self.assertEqual(other.snapshot().undo_count, 0)

    def test_stale_history_rejected_before_edit(self):
        self.document.replace_text("external change")
        before = self.document.snapshot(), self.history.snapshot()
        for action, payload in (("edit", "forbidden"), ("undo", None)):
            with self.assertRaises(CommandRejected):
                self.act(action, payload)
            self.assertEqual((self.document.snapshot(), self.history.snapshot()), before)

    def test_read_never_changes_history(self):
        before = self.history.snapshot()
        self.assertEqual(self.act("read"), self.document.snapshot())
        self.assertEqual(self.history.snapshot(), before)

    def test_bounded_history_discards_oldest(self):
        doc = NeutralDocument()
        hist = NeutralEditHistory(doc, max_entries=2)
        for text in ("a", "ab", "abc"):
            self.guard.execute(BlackHoleEditorInput.receive("edit", text), doc, hist)
        self.assertEqual(hist.snapshot().undo_count, 2)
        for expected in ("ab", "a"):
            self.assertEqual(self.guard.execute(BlackHoleEditorInput.receive("undo"), doc, hist).text, expected)
        with self.assertRaises(CommandRejected):
            self.guard.execute(BlackHoleEditorInput.receive("undo"), doc, hist)
        self.assertEqual(doc.snapshot().text, "a")

    def test_unicode_restoration(self):
        self.act("insert", {"offset": 3, "text": "📝"})
        self.assertEqual(self.act("undo").text, "one")
        self.assertEqual(self.act("redo").text, "one📝")

    def test_history_snapshot_immutable(self):
        snap = self.history.snapshot()
        with self.assertRaises(FrozenInstanceError):
            snap.undo_count = 100

    def test_constructor_rejects_invalid_document_and_bounds(self):
        for value in (None, "not a document"):
            with self.assertRaises(TypeError):
                NeutralEditHistory(value)
        for value in (0, -1, True, "2"):
            with self.assertRaises(ValueError):
                NeutralEditHistory(self.document, value)

    def test_original_guard_without_history_still_works(self):
        other = NeutralDocument("original")
        self.assertEqual(self.guard.execute(BlackHoleEditorInput.receive("edit", "changed"), other).text, "changed")

    def test_no_external_effect_functions(self):
        for name in ("open_file", "save_file", "save", "write_clipboard"):
            self.assertFalse(hasattr(self.history, name))


if __name__ == "__main__":
    unittest.main()
