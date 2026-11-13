"""Round 7 guard/clipboard integration and cumulative preservation tests."""
import tempfile
from pathlib import Path
import unittest

from notepad_clipboard import NeutralClipboardSelection, SelectionRange
from notepad_document import NeutralDocument
from notepad_files import NeutralFileSession
from notepad_guard import CommandRejected, WhiteHoleCommandGuard
from notepad_history import NeutralEditHistory
from notepad_input import BlackHoleEditorInput
from notepad_surface import NeutralEditorSurface, TkNotepadWindow


class MemoryClipboard:
    """Host test adapter, not an Anchor or extra document owner."""
    def __init__(self, text=""):
        self.text = text
        self.read_count = 0
        self.write_count = 0
        self.fail_read = False
        self.fail_write = False

    def read(self):
        self.read_count += 1
        if self.fail_read:
            raise RuntimeError("host clipboard unavailable")
        return self.text

    def write(self, text):
        self.write_count += 1
        if self.fail_write:
            raise RuntimeError("host clipboard write unavailable")
        self.text = text


class TestClipboardSelection(unittest.TestCase):
    def setUp(self):
        self.host = MemoryClipboard()
        self.surface = NeutralEditorSurface()
        self.surface.enable_clipboard(self.host.read, self.host.write)

    def snapshot_triplet(self):
        return (self.surface.document.snapshot(), self.surface.history.snapshot(),
                self.host.text)

    def test_seventh_anchor_identity_and_explicit_host_binding(self):
        self.assertEqual(self.surface.clipboard.anchor_id, "N-CLIPBOARD-SELECTION")
        self.assertEqual(self.surface.clipboard.canonical_type, "Neutral")
        self.assertIs(self.surface.clipboard._document, self.surface.document)
        with self.assertRaisesRegex(ValueError, "already enabled"):
            self.surface.enable_clipboard(self.host.read, self.host.write)

    def test_no_new_document_text_or_history_owners(self):
        self.surface.text_changed("abc")
        self.surface.copy_selection(0, 1)
        self.assertEqual(self.surface.document.snapshot().text, "abc")
        self.assertEqual(self.surface.history.snapshot().undo_count, 1)
        self.assertEqual(self.host.text, "a")

    def test_unbound_clipboard_command_rejected_before_effect(self):
        surface = NeutralEditorSurface()
        surface.text_changed("keep")
        previous = (surface.document.snapshot(), surface.history.snapshot())
        for action, payload in (("copy", {"start":0, "end":2}),
                                ("cut", {"start":0, "end":2}),
                                ("paste", {"start":0, "end":0}),
                                ("select-all", None)):
            with self.subTest(action=action):
                with self.assertRaises(CommandRejected):
                    surface.dispatch(action, payload)
                self.assertEqual((surface.document.snapshot(), surface.history.snapshot()), previous)

    def test_clipboard_capture_alone_has_no_host_or_document_effect(self):
        self.surface.text_changed("hello")
        before = self.snapshot_triplet()
        intent = BlackHoleEditorInput.receive("cut", {"start":0, "end":2})
        self.assertEqual(intent.action, "cut")
        self.assertEqual(self.snapshot_triplet(), before)
        self.assertEqual(self.host.write_count, 0)

    def test_copy_unicode_selected_text_exactly_without_mutation(self):
        self.surface.text_changed("a📝b\nc")
        before = (self.surface.document.snapshot(), self.surface.history.snapshot())
        self.assertEqual(self.surface.copy_selection(1, 3).text, "a📝b\nc")
        self.assertEqual(self.host.text, "📝b")
        self.assertEqual((self.surface.document.snapshot(), self.surface.history.snapshot()), before)
        self.assertEqual(self.host.write_count, 1)

    def test_cut_is_one_undoable_edit_and_pastes_correctly(self):
        self.surface.text_changed("abcdef")
        after = self.surface.cut_selection(1, 4)
        self.assertEqual(after.text, "aef")
        self.assertEqual(self.host.text, "bcd")
        self.assertEqual(self.surface.history.snapshot().undo_count, 2)
        self.assertEqual(self.surface.undo().text, "abcdef")
        self.assertEqual(self.surface.redo().text, "aef")
        self.assertEqual(self.surface.paste_at(1, 1).text, "abcdef")
        self.assertEqual(self.surface.undo().text, "aef")

    def test_paste_replaces_selection_atomically_and_undoes_once(self):
        self.surface.text_changed("hello world")
        self.host.text = "📝\n"
        after = self.surface.paste_at(6, 11)
        self.assertEqual(after.text, "hello 📝\n")
        self.assertEqual(self.surface.history.snapshot().undo_count, 2)
        self.assertEqual(self.surface.undo().text, "hello world")
        self.assertEqual(self.surface.redo().text, "hello 📝\n")

    def test_paste_empty_clipboard_can_delete_selected_text(self):
        self.surface.text_changed("ABC")
        self.assertEqual(self.surface.paste_at(1, 2).text, "AC")
        self.assertEqual(self.surface.undo().text, "ABC")

    def test_paste_empty_clipboard_at_caret_is_noop(self):
        self.surface.text_changed("ABC")
        previous = self.surface.history.snapshot()
        result = self.surface.paste_at(1, 1)
        self.assertEqual(result.text, "ABC")
        self.assertEqual(self.surface.history.snapshot(), previous)

    def test_select_all_returns_unicode_offsets_without_side_effect(self):
        self.surface.text_changed("📝 hello\nworld")
        previous = self.snapshot_triplet()
        self.assertEqual(self.surface.select_all(), SelectionRange(0, len("📝 hello\nworld")))
        self.assertEqual(self.snapshot_triplet(), previous)
        self.assertEqual((self.host.read_count, self.host.write_count), (0, 0))

    def test_select_all_empty_document(self):
        self.assertEqual(self.surface.select_all(), SelectionRange(0, 0))

    def test_reject_bad_range_without_clipboard_or_history_effect(self):
        self.surface.text_changed("abcd")
        previous = self.snapshot_triplet()
        cases = [
            {"start":0,"end":5}, {"start":3,"end":2}, {"start":-1,"end":2},
            {"start":False,"end":2}, {"start":0,"end":2.0},
            {"start":"0","end":2}, {"start":0,"end":2,"extra":True},
            {"start":0}, None, "bad",
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                for action in ("copy", "cut", "paste"):
                    with self.assertRaises(CommandRejected):
                        self.surface.dispatch(action, payload)
                    self.assertEqual(self.snapshot_triplet(), previous)
        self.assertEqual(self.host.read_count, 0)
        self.assertEqual(self.host.write_count, 0)

    def test_copy_and_cut_empty_selection_rejected_without_host_effect(self):
        self.surface.text_changed("abc")
        previous = self.snapshot_triplet()
        for action in ("copy", "cut"):
            with self.assertRaises(CommandRejected):
                self.surface.dispatch(action, {"start":1,"end":1})
            self.assertEqual(self.snapshot_triplet(), previous)

    def test_select_all_payload_rejected_effect_free(self):
        self.surface.text_changed("hello")
        before = self.snapshot_triplet()
        for payload in (0, "all", {}, {"start":0,"end":5}):
            with self.assertRaises(CommandRejected):
                self.surface.dispatch("select-all", payload)
            self.assertEqual(self.snapshot_triplet(), before)

    def test_bad_clipboard_read_preserves_document_and_history(self):
        self.surface.text_changed("original")
        before = self.snapshot_triplet()
        self.host.fail_read = True
        with self.assertRaisesRegex(CommandRejected, "clipboard read failed"):
            self.surface.paste_at(0, 3)
        self.assertEqual(self.snapshot_triplet(), before)

    def test_bad_clipboard_write_prevents_cut(self):
        self.surface.text_changed("original")
        before = self.snapshot_triplet()
        self.host.fail_write = True
        with self.assertRaisesRegex(CommandRejected, "clipboard write failed"):
            self.surface.cut_selection(0, 3)
        self.assertEqual(self.snapshot_triplet(), before)

    def test_clipboard_nonstr_returns_rejected_no_change(self):
        self.surface.text_changed("ABC")
        before = self.snapshot_triplet()
        self.host.text = 42
        with self.assertRaisesRegex(CommandRejected, "plain text"):
            self.surface.paste_at(1, 1)
        self.assertEqual(self.snapshot_triplet()[0:2], before[0:2])

    def test_reentrant_clipboard_read_does_not_apply_stale_paste(self):
        self.surface.text_changed("hello")
        def stale_read():
            self.surface.document.replace_text("changed by host")
            return "X"
        clip = self.surface.clipboard
        clip._read_text = stale_read
        before_history = self.surface.history.snapshot()
        with self.assertRaises(CommandRejected):
            self.surface.paste_at(1, 2)
        self.assertEqual(self.surface.document.snapshot().text, "changed by host")
        self.assertEqual(self.surface.history.snapshot(), before_history)

    def test_reentrant_clipboard_write_does_not_apply_stale_cut(self):
        self.surface.text_changed("hello")
        def stale_write(_text):
            self.surface.document.replace_text("changed by host")
        self.surface.clipboard._write_text = stale_write
        with self.assertRaises(CommandRejected):
            self.surface.cut_selection(1, 2)
        self.assertEqual(self.surface.document.snapshot().text, "changed by host")

    def test_cross_document_binding_is_rejected(self):
        other = NeutralEditorSurface()
        other.text_changed("abc")
        original = other.document.snapshot()
        with self.assertRaisesRegex(ValueError, "another document"):
            NeutralClipboardSelection(other.document, self.surface.history, self.host.read, self.host.write)
        with self.assertRaisesRegex(ValueError, "another document"):
            other.clipboard = self.surface.clipboard
            other.select_all()
        self.assertEqual(other.document.snapshot(), original)

    def test_invalid_clipboard_host_adapters_are_rejected(self):
        no_host = NeutralEditorSurface()
        with self.assertRaises(TypeError):
            no_host.enable_clipboard(None, lambda x: None)
        with self.assertRaises(TypeError):
            no_host.enable_clipboard(lambda: "text", 5)
        self.assertIsNone(no_host.clipboard)

    def test_undo_redo_preserves_clean_baseline_with_copy_cut_paste(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "note.txt"
            self.surface.enable_files()
            self.surface.text_changed("keep")
            self.surface.save_file_as(str(path))
            self.surface.copy_selection(0, 2)
            self.assertFalse(self.surface.dispatch("read").dirty)
            self.surface.cut_selection(0, 2)
            self.assertTrue(self.surface.dispatch("read").dirty)
            self.surface.undo()
            self.assertFalse(self.surface.dispatch("read").dirty)
            self.surface.redo()
            self.assertTrue(self.surface.dispatch("read").dirty)
            self.assertEqual(path.read_text(), "keep")

    def test_clipboard_capability_persists_across_new_open(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "a.txt"
            path.write_text("opened 📝", encoding="utf-8")
            self.surface.enable_files()
            self.surface.text_changed("draft")
            self.surface.new_document(discard=True)
            self.surface.open_file(str(path))
            self.assertEqual(self.surface.select_all(), SelectionRange(0, len("opened 📝")))
            self.surface.copy_selection(0, 6)
            self.assertEqual(self.host.text, "opened")
            self.assertEqual(self.surface.history.snapshot().undo_count, 0)

    def test_legacy_edit_undo_redo_unbound_guard_still_works(self):
        doc = NeutralDocument()
        guard = WhiteHoleCommandGuard()
        intent = BlackHoleEditorInput.receive("edit", "one")
        self.assertEqual(guard.execute(intent, doc).text, "one")
        history = NeutralEditHistory(doc)
        self.assertEqual(guard.execute(BlackHoleEditorInput.receive("read"), doc).text, "one")
        self.assertEqual(history.snapshot().undo_count, 0)


class TestTkClipboard(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk
            self.root = tk.Tk()
            self.root.withdraw()
        except (ImportError, tk.TclError) as exc:
            self.skipTest(f"Tk display not available: {exc}")
        self.window = TkNotepadWindow(root=self.root)
        self.window.messagebox.showerror = lambda *args, **kwargs: self.fail(f"Unexpected error {args}")
        self.root.update()

    def tearDown(self):
        if getattr(self, "root", None):
            try:
                self.root.destroy()
            except Exception:
                pass

    def set_text(self, text):
        self.window.surface.text_changed(text)
        self.window.surface.display(self.window._paint)
        self.root.update()

    def choose(self, start, end):
        self.window.text.tag_add("sel", f"1.0+{start}c", f"1.0+{end}c")

    def test_gui_menu_and_keyboard_routes(self):
        for name in ("Copy", "Cut", "Paste", "Select All"):
            self.assertEqual(self.window.edit_menu.entrycget(name, "state"), "normal")
        for sequence in ("<<Copy>>", "<<Cut>>", "<<Paste>>", "<Control-a>",
                         "<Control-c>", "<Control-x>", "<Control-v>"):
            self.assertIn("callback", self.window.text.bind(sequence))
        # Round 8 explicitly authorizes Find/Replace through the new
        # document-bound search owner and existing WhiteHole.
        for name in ("Find…", "Replace…"):
            self.assertEqual(self.window.edit_menu.entrycget(name, "state"), "normal")

    def test_select_all_projects_selection_without_history(self):
        self.set_text("hello 📝\nworld")
        before = (self.window.surface.document.snapshot(), self.window.surface.history.snapshot())
        self.assertTrue(self.window.select_all())
        self.assertEqual(self.window.text.get("sel.first", "sel.last"), "hello 📝\nworld")
        self.assertEqual((self.window.surface.document.snapshot(), self.window.surface.history.snapshot()), before)

    def test_copy_cut_paste_real_tk_clipboard(self):
        self.set_text("123📝567")
        self.choose(1, 4)
        self.assertTrue(self.window.copy_selection())
        self.assertEqual(self.root.clipboard_get(), "23📝")
        self.assertEqual(self.window.surface.document.snapshot().text, "123📝567")
        self.assertTrue(self.window.cut_selection())
        self.assertEqual(self.window.surface.document.snapshot().text, "1567")
        self.assertEqual(self.window.text.get("1.0", "end-1c"), "1567")
        self.assertEqual(self.root.clipboard_get(), "23📝")
        self.window.text.mark_set("insert", "1.0+1c")
        self.assertTrue(self.window.paste_clipboard())
        self.assertEqual(self.window.surface.document.snapshot().text, "123📝567")
        self.assertEqual(self.window.surface.undo().text, "1567")

    def test_paste_over_selection_and_correct_caret(self):
        self.set_text("hello world")
        self.root.clipboard_clear()
        self.root.clipboard_append("📝")
        self.choose(6, 11)
        self.assertTrue(self.window.paste_clipboard())
        self.assertEqual(self.window.surface.document.snapshot().text, "hello 📝")
        self.assertEqual(self.window.text.index("insert"), "1.8")
        self.assertFalse(bool(self.window.text.tag_ranges("sel")))

    def test_native_unsupported_clipboard_effects_blocked(self):
        self.set_text("keep")
        self.assertEqual(self.window._blocked_clipboard(None), "break")
        for sequence in ("<<PasteSelection>>", "<<Clear>>", "<Button-2>"):
            self.assertIn("_blocked_clipboard", self.window.text.bind(sequence))
        self.assertEqual(self.window.surface.document.snapshot().text, "keep")

    def test_no_selection_cut_copy_are_effect_free(self):
        self.set_text("abcd")
        before = (self.window.surface.document.snapshot(), self.window.surface.history.snapshot())
        self.assertFalse(self.window.cut_selection())
        self.assertFalse(self.window.copy_selection())
        self.assertEqual((self.window.surface.document.snapshot(), self.window.surface.history.snapshot()), before)

    def test_tk_paste_clipboard_failure_preserves_document(self):
        self.set_text("keep")
        before = self.window.surface.document.snapshot()
        self.window.messagebox.showerror = lambda *args, **kw: None
        self.window._read_clipboard = lambda: self.fail("adapter is already bound")
        self.window.surface.clipboard._read_text = lambda: (_ for _ in ()).throw(ValueError("not available"))
        self.assertFalse(self.window.paste_clipboard())
        self.assertEqual(self.window.surface.document.snapshot(), before)


if __name__ == "__main__":
    unittest.main()
