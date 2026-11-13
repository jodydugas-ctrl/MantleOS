"""Executable local checks for Round 1 only."""
import unittest

from notepad_input import BlackHoleEditorInput, EditorIntent


class TestBlackHoleEditorInput(unittest.TestCase):
    def test_receives_text_edit_intent_without_changing_it(self):
        text = "A notepad draft\nSecond line"
        intent = BlackHoleEditorInput.receive("edit", text)
        self.assertEqual(intent, EditorIntent("edit", text))

    def test_receives_file_action(self):
        path = "draft.txt"
        intent = BlackHoleEditorInput.receive("save-as", path)
        self.assertEqual((intent.action, intent.payload), ("save-as", path))

    def test_does_not_prematurely_validate_unknown_input(self):
        token = object()
        intent = BlackHoleEditorInput.receive("unknown", token)
        self.assertEqual(intent.action, "unknown")
        self.assertIs(intent.payload, token)

    def test_input_event_is_not_mutated(self):
        event = BlackHoleEditorInput.receive("edit", "hello")
        with self.assertRaises(AttributeError):
            event.action = "save"

    def test_ignores_no_input_or_internal_state(self):
        left = BlackHoleEditorInput.receive("edit", "first")
        right = BlackHoleEditorInput.receive("edit", "second")
        self.assertEqual(left.payload, "first")
        self.assertEqual(right.payload, "second")
        self.assertIsNot(left, right)


if __name__ == "__main__":
    unittest.main()
