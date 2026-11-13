"""Round 3 checks: WhiteHole validation and cumulative BH → WH → N flow."""
import unittest

from notepad_document import DocumentSnapshot, NeutralDocument
from notepad_guard import CommandRejected, WhiteHoleCommandGuard
from notepad_input import BlackHoleEditorInput, EditorIntent


class TestWhiteHoleCommandGuard(unittest.TestCase):
    def setUp(self):
        self.guard = WhiteHoleCommandGuard()
        self.document = NeutralDocument("abcd")

    def command(self, action, payload=None):
        return self.guard.execute(BlackHoleEditorInput.receive(action, payload), self.document)

    def test_declared_identity(self):
        self.assertEqual(self.guard.anchor_id, "WH-COMMAND-GUARD")
        self.assertEqual(self.guard.canonical_type, "WhiteHole")

    def test_guarded_replace_and_dirty_revision(self):
        self.assertEqual(self.command("edit", "replaced"), DocumentSnapshot("replaced", 1, True))

    def test_guarded_insert_from_blackhole(self):
        result = self.command("insert", {"offset": 2, "text": "📝"})
        self.assertEqual(result, DocumentSnapshot("ab📝cd", 1, True))

    def test_guarded_delete_from_blackhole(self):
        self.assertEqual(self.command("delete", {"start": 1, "end": 3}), DocumentSnapshot("ad", 1, True))

    def test_read_returns_immutable_snapshot_without_edit(self):
        self.assertEqual(self.command("read"), DocumentSnapshot("abcd", 0, False))
        self.assertEqual(self.command("read"), self.document.snapshot())

    def test_blackhole_capture_alone_still_never_edits(self):
        intent = BlackHoleEditorInput.receive("edit", "new")
        self.assertEqual(self.document.snapshot(), DocumentSnapshot("abcd", 0, False))
        self.assertEqual(self.guard.execute(intent, self.document).text, "new")

    def test_reject_unknown_and_file_commands_without_mutation(self):
        for action in ("save", "save-as", "open", "new", "copy", "unknown", "REPLACE"):
            before = self.document.snapshot()
            with self.subTest(action=action):
                with self.assertRaises(CommandRejected):
                    self.command(action, "some input")
                self.assertEqual(self.document.snapshot(), before)

    def test_reject_bad_action_types_without_mutation(self):
        for action in (None, 123, True, {}, ["edit"]):
            before = self.document.snapshot()
            with self.subTest(action=repr(action)):
                with self.assertRaises(CommandRejected):
                    self.command(action, "text")
                self.assertEqual(self.document.snapshot(), before)

    def test_reject_malformed_intent_and_document(self):
        before = self.document.snapshot()
        with self.assertRaises(CommandRejected):
            self.guard.execute({"action": "edit", "payload": "bad"}, self.document)
        with self.assertRaises(CommandRejected):
            self.guard.execute(EditorIntent("edit", "bad"), object())
        self.assertEqual(self.document.snapshot(), before)

    def test_reject_non_text_full_replace(self):
        for value in (None, b"bytes", 3, ["text"], {"text": "hi"}):
            before = self.document.snapshot()
            with self.subTest(value=repr(value)):
                with self.assertRaises(CommandRejected):
                    self.command("edit", value)
                self.assertEqual(self.document.snapshot(), before)

    def test_reject_non_null_read_payload(self):
        before = self.document.snapshot()
        with self.assertRaises(CommandRejected):
            self.command("read", "junk")
        self.assertEqual(self.document.snapshot(), before)

    def test_reject_bad_insert_structure_without_mutation(self):
        values = (None, [2, "x"], {"offset": 2}, {"offset": 2, "text": "x", "other": 0}, {"offset": 2, "text": 1})
        for payload in values:
            before = self.document.snapshot()
            with self.subTest(payload=repr(payload)):
                with self.assertRaises(CommandRejected):
                    self.command("insert", payload)
                self.assertEqual(self.document.snapshot(), before)

    def test_reject_invalid_insert_indices(self):
        for offset in (-1, True, 1.0, "2", 5):
            before = self.document.snapshot()
            with self.subTest(offset=repr(offset)):
                with self.assertRaises(CommandRejected):
                    self.command("insert", {"offset": offset, "text": "x"})
                self.assertEqual(self.document.snapshot(), before)

    def test_reject_bad_delete_structure(self):
        for payload in (None, [], {"start": 1}, {"start": 0, "end": 2, "unused": True}):
            before = self.document.snapshot()
            with self.subTest(payload=repr(payload)):
                with self.assertRaises(CommandRejected):
                    self.command("delete", payload)
                self.assertEqual(self.document.snapshot(), before)

    def test_reject_invalid_delete_bounds_atomically(self):
        for start, end in ((-1, 1), (3, 2), (0, 5), (True, 1), (0, 1.0)):
            before = self.document.snapshot()
            with self.subTest(start=start, end=end):
                with self.assertRaises(CommandRejected):
                    self.command("delete", {"start": start, "end": end})
                self.assertEqual(self.document.snapshot(), before)

    def test_valid_noops_do_not_increment_revision(self):
        self.command("insert", {"offset": 0, "text": ""})
        self.command("delete", {"start": 1, "end": 1})
        self.command("edit", "abcd")
        self.assertEqual(self.document.snapshot(), DocumentSnapshot("abcd", 0, False))

    def test_state_is_only_changed_via_neutral(self):
        # Guard owns no document text, baseline, or revision itself.
        self.assertFalse(hasattr(self.guard, "_text"))
        self.assertFalse(hasattr(self.guard, "_revision"))
        self.command("edit", "changed")
        self.assertEqual(self.document.snapshot().revision, 1)

    def test_no_file_or_clipboard_effect_methods(self):
        for method in ("open_file", "save", "save_as", "copy_to_clipboard"):
            self.assertFalse(hasattr(self.guard, method))
        self.assertEqual(self.command("read").text, "abcd")

    def test_preserves_blackhole_uninterpreted_capture(self):
        token = object()
        captured = BlackHoleEditorInput.receive("unsupported", token)
        self.assertIs(captured.payload, token)
        with self.assertRaises(CommandRejected):
            self.guard.execute(captured, self.document)
        self.assertEqual(self.document.snapshot().text, "abcd")


if __name__ == "__main__":
    unittest.main()
