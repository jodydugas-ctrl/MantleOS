"""Round 5 checks for the fifth Anchor and Round 1-4 preservation."""
import unittest

from notepad_document import DocumentSnapshot, NeutralDocument
from notepad_guard import CommandRejected, WhiteHoleCommandGuard
from notepad_history import NeutralEditHistory
from notepad_input import BlackHoleEditorInput
from notepad_surface import NeutralEditorSurface, TkNotepadWindow


class TestNeutralEditorSurface(unittest.TestCase):
    def setUp(self):
        self.surface = NeutralEditorSurface()

    def test_anchor_identity_and_new_document(self):
        self.assertEqual(self.surface.anchor_id, 'N-EDITOR-SURFACE')
        self.assertEqual(self.surface.canonical_type, 'Neutral')
        self.assertEqual(self.surface.dispatch('read'), DocumentSnapshot('', 0, False))

    def test_gui_edit_flows_through_guarded_core(self):
        result = self.surface.text_changed('Plain 📝 text\nline two\n')
        self.assertEqual(result, DocumentSnapshot('Plain 📝 text\nline two\n', 1, True))
        self.assertEqual(self.surface.history.snapshot().undo_count, 1)

    def test_edit_undo_redo_accumulate(self):
        self.surface.text_changed('first')
        self.surface.text_changed('second')
        self.assertEqual(self.surface.undo().text, 'first')
        self.assertEqual(self.surface.redo().text, 'second')
        self.assertTrue(self.surface.dispatch('read').dirty)

    def test_noop_does_not_add_history(self):
        self.surface.text_changed('word')
        self.surface.text_changed('word')
        self.assertEqual(self.surface.history.snapshot().undo_count, 1)

    def test_redo_cleared_after_new_input(self):
        self.surface.text_changed('A')
        self.surface.text_changed('AB')
        self.surface.undo()
        self.surface.text_changed('AC')
        self.assertEqual(self.surface.history.snapshot().redo_count, 0)
        with self.assertRaises(CommandRejected):
            self.surface.redo()
        self.assertEqual(self.surface.dispatch('read').text, 'AC')

    def test_display_sink_receives_immutable_authoritative_snapshot(self):
        self.surface.text_changed('Hi')
        frames=[]
        snap = self.surface.display(frames.append)
        self.assertEqual(frames, [DocumentSnapshot('Hi', 1, True)])
        self.assertEqual(snap, frames[0])
        self.assertIsInstance(snap, DocumentSnapshot)

    def test_display_invalid_sink_rejected_without_change(self):
        before=self.surface.dispatch('read')
        with self.assertRaises(TypeError):
            self.surface.display(None)
        self.assertEqual(self.surface.dispatch('read'), before)

    def test_bad_payload_rejected_without_effect(self):
        before=self.surface.dispatch('read')
        for payload in (None, ['bad'], 7, {'text':'x'}):
            with self.subTest(payload=repr(payload)):
                with self.assertRaises(CommandRejected):
                    self.surface.text_changed(payload)
                self.assertEqual(self.surface.dispatch('read'), before)

    def test_unauthorized_file_and_clipboard_commands_still_rejected(self):
        self.surface.text_changed('Safe')
        before=self.surface.dispatch('read')
        history=self.surface.history.snapshot()
        for action in ('new','open','save','save-as','copy','cut','paste','find','replace'):
            with self.subTest(action=action):
                with self.assertRaises(CommandRejected):
                    self.surface.dispatch(action, 'arbitrary')
                self.assertEqual(self.surface.dispatch('read'), before)
                self.assertEqual(self.surface.history.snapshot(), history)

    def test_bound_history_preserved_no_parallel_state(self):
        document = NeutralDocument('base')
        history = NeutralEditHistory(document)
        surface = NeutralEditorSurface(document, history)
        surface.text_changed('changed')
        self.assertIs(surface.document, document)
        self.assertIs(surface.history, history)
        self.assertEqual(document.snapshot().text, 'changed')
        self.assertEqual(surface.undo().text, 'base')

    def test_surface_rejects_foreign_or_stale_history(self):
        doc = NeutralDocument()
        with self.assertRaisesRegex(ValueError,'another document'):
            NeutralEditorSurface(doc, NeutralEditHistory(NeutralDocument()))
        hist = NeutralEditHistory(doc)
        doc.replace_text('stale')
        with self.assertRaisesRegex(ValueError,'outside this history'):
            NeutralEditorSurface(doc, hist)

    def test_surface_type_checks_are_effect_free(self):
        with self.assertRaises(TypeError):
            NeutralEditorSurface(document='not a document')
        with self.assertRaises(TypeError):
            NeutralEditorSurface(history='not history')
        with self.assertRaises(TypeError):
            NeutralEditorSurface(guard='not guard')

    def test_exit_clean_does_not_call_confirm(self):
        calls=[]
        self.assertTrue(self.surface.can_exit(lambda: calls.append(1)))
        self.assertEqual(calls, [])

    def test_exit_dirty_requires_explicit_confirmation(self):
        self.surface.text_changed('unsaved')
        self.assertFalse(self.surface.can_exit(lambda: False))
        self.assertFalse(self.surface.can_exit(lambda: 'yes'))
        self.assertTrue(self.surface.can_exit(lambda: True))
        self.assertEqual(self.surface.dispatch('read').text,'unsaved')

    def test_exit_invalid_confirmation_leaves_dirty_data(self):
        self.surface.text_changed('unsaved')
        with self.assertRaises(TypeError):
            self.surface.can_exit(None)
        self.assertTrue(self.surface.dispatch('read').dirty)

    def test_preserve_blackhole_observation_does_not_mutate(self):
        before=self.surface.dispatch('read')
        _ = BlackHoleEditorInput.receive('edit','unsafe')
        self.assertEqual(self.surface.dispatch('read'), before)


class TestTkNotepadWindow(unittest.TestCase):
    """Real Tk integration tests; run via xvfb-run on a headless host."""
    def setUp(self):
        try:
            import tkinter as tk
            self.root=tk.Tk()
            self.root.withdraw()
        except (ImportError, tk.TclError) as exc:
            self.skipTest(f'Tk display not available: {exc}')
        self.window=TkNotepadWindow(root=self.root)
        self.root.update()

    def tearDown(self):
        if getattr(self, 'root', None):
            try:
                self.root.destroy()
            except Exception:
                pass

    def test_window_initially_read_only_projection_and_guarded_files(self):
        self.assertEqual(self.window.text.get('1.0','end-1c'), '')
        self.assertEqual(self.window.file_menu.entrycget('Save','state'), 'normal')
        self.assertEqual(self.window.file_menu.entrycget('Open…','state'), 'normal')
        self.assertEqual(self.window.edit_menu.entrycget('Paste','state'), 'normal')
        self.assertEqual(str(self.window.text.cget('exportselection')), '0')
        self.assertEqual(str(self.window.text.cget('undo')), '0')

    def test_typing_through_real_tk_modified_event(self):
        self.window.text.insert('1.0', 'hello 📝\n')
        self.root.update()
        snap=self.window.surface.dispatch('read')
        self.assertEqual(snap.text, 'hello 📝\n')
        self.assertTrue(snap.dirty)
        self.assertEqual(self.window.edit_menu.entrycget('Undo','state'),'normal')
        self.assertIn('Unsaved',self.window.status_var.get())

    def test_tk_undo_redo_then_redraw_authoritative_text(self):
        self.window.text.insert('1.0','one')
        self.root.update()
        self.window.text.insert('end-1c','two')
        self.root.update()
        self.window.undo()
        self.root.update()
        self.assertEqual(self.window.text.get('1.0','end-1c'),'one')
        self.assertEqual(self.window.surface.document.snapshot().text,'one')
        self.window.redo()
        self.root.update()
        self.assertEqual(self.window.text.get('1.0','end-1c'),'onetwo')
        self.assertEqual(self.window.surface.history.snapshot().redo_count,0)

    def test_tk_blocked_clipboard_virtual_events(self):
        self.assertEqual(self.window._blocked_clipboard(None),'break')
        for name in TkNotepadWindow.BLOCKED_CLIPBOARD_VIRTUAL_EVENTS:
            self.assertIn('break', self.window.text.bind(name))
        for name in TkNotepadWindow.BLOCKED_CLIPBOARD_KEYS:
            self.assertIn('break', self.window.text.bind(name))

    def test_tk_paint_restore_from_guarded_snapshot(self):
        self.window.surface.text_changed('source of truth')
        self.window.surface.display(self.window._paint)
        self.root.update()
        self.assertEqual(self.window.text.get('1.0','end-1c'),'source of truth')
        self.assertEqual(self.window.surface.history.snapshot().undo_count,1)
        self.assertEqual(self.window.surface.document.snapshot().revision,1)

    def test_tk_dirty_close_cancel_keeps_window(self):
        self.window.text.insert('1.0','unsaved')
        self.root.update()
        self.window.messagebox.askyesno=lambda *a, **kw: False
        self.assertFalse(self.window.request_close())
        self.assertTrue(self.root.winfo_exists())
        self.assertEqual(self.window.surface.dispatch('read').text,'unsaved')

    def test_tk_close_clean_without_dialog(self):
        self.window.messagebox.askyesno=lambda *a, **kw: self.fail('should not ask for clean doc')
        self.assertTrue(self.window.request_close())
        with self.assertRaises(self.window.tk.TclError):
            self.root.winfo_exists()


if __name__ == '__main__':
    unittest.main()
