"""Round 2 local checks for Neutral document state and cross-Anchor safety."""
import unittest
from dataclasses import FrozenInstanceError

from notepad_document import NeutralDocument, DocumentSnapshot
from notepad_input import BlackHoleEditorInput


class TestNeutralDocument(unittest.TestCase):
    def test_new_document_is_empty_and_clean(self):
        self.assertEqual(NeutralDocument().snapshot(), DocumentSnapshot("", 0, False))

    def test_initial_content_is_its_clean_baseline(self):
        self.assertEqual(NeutralDocument("existing").snapshot(), DocumentSnapshot("existing", 0, False))

    def test_replace_text_updates_state_and_marks_dirty(self):
        d = NeutralDocument()
        self.assertEqual(d.replace_text("Draft\nSecond line"), DocumentSnapshot("Draft\nSecond line", 1, True))

    def test_repeated_identical_edit_is_no_op(self):
        d = NeutralDocument()
        d.replace_text("draft")
        self.assertEqual(d.replace_text("draft").revision, 1)

    def test_insert_text_at_unicode_codepoint_offset(self):
        d = NeutralDocument("A📝B")
        self.assertEqual(d.insert_text(2, "!").text, "A📝!B")
        self.assertTrue(d.snapshot().dirty)

    def test_delete_range_and_revision(self):
        d = NeutralDocument("abcd")
        self.assertEqual(d.delete_range(1, 3), DocumentSnapshot("ad", 1, True))

    def test_dirty_is_derived_and_clears_when_reverted(self):
        d = NeutralDocument("saved")
        d.replace_text("unsaved")
        self.assertTrue(d.snapshot().dirty)
        self.assertEqual(d.replace_text("saved"), DocumentSnapshot("saved", 2, False))

    def test_invalid_text_does_not_change_any_state(self):
        d = NeutralDocument("hello")
        before = d.snapshot()
        with self.assertRaises(TypeError):
            d.replace_text(None)
        with self.assertRaises(TypeError):
            d.insert_text(1, 123)
        self.assertEqual(before, d.snapshot())

    def test_invalid_offsets_are_rejected_atomically(self):
        d = NeutralDocument("abc")
        before = d.snapshot()
        for op in (
            lambda: d.insert_text(-1, "x"),
            lambda: d.insert_text(4, "x"),
            lambda: d.insert_text(True, "x"),
            lambda: d.delete_range(2, 1),
            lambda: d.delete_range(0, 4),
            lambda: d.delete_range(-1, 2),
        ):
            with self.assertRaises((TypeError, ValueError)):
                op()
            self.assertEqual(before, d.snapshot())

    def test_no_op_insert_and_delete_leave_revision_unchanged(self):
        d = NeutralDocument("abc")
        d.insert_text(2, "")
        d.delete_range(1, 1)
        self.assertEqual(d.snapshot(), DocumentSnapshot("abc", 0, False))

    def test_snapshots_are_immutable_and_independent(self):
        d = NeutralDocument()
        old = d.snapshot()
        with self.assertRaises(FrozenInstanceError):
            old.text = "changed"
        d.replace_text("new")
        self.assertEqual(old, DocumentSnapshot("", 0, False))
        self.assertEqual(d.snapshot().text, "new")

    def test_blackhole_intents_do_not_implicitly_execute_in_neutral(self):
        d = NeutralDocument()
        before = d.snapshot()
        event = BlackHoleEditorInput.receive("edit", "should not be applied yet")
        self.assertEqual((event.action, event.payload), ("edit", "should not be applied yet"))
        self.assertEqual(d.snapshot(), before)

    def test_separate_documents_do_not_share_state(self):
        first, second = NeutralDocument(), NeutralDocument()
        first.replace_text("first")
        self.assertEqual(second.snapshot(), DocumentSnapshot("", 0, False))

    def test_no_filesystem_effect_on_edit(self):
        # No path or save API is present on this Anchor.
        d = NeutralDocument()
        self.assertFalse(hasattr(d, "save"))
        self.assertFalse(hasattr(d, "open_file"))
        self.assertEqual(d.replace_text("draft").text, "draft")


if __name__ == "__main__":
    unittest.main()
