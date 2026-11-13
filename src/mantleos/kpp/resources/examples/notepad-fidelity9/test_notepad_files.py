"""Round 6 file capability and Round 1-5 cumulative preservation checks."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from notepad_document import NeutralDocument
from notepad_files import FileSessionError, NeutralFileSession
from notepad_guard import CommandRejected, WhiteHoleCommandGuard
from notepad_history import NeutralEditHistory
from notepad_input import BlackHoleEditorInput
from notepad_surface import NeutralEditorSurface, TkNotepadWindow


class TestFileSession(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.surface = NeutralEditorSurface()
        self.surface.enable_files()
        self.path = self.folder / 'notes 📝.txt'

    def test_identity_sixth_anchor(self):
        self.assertEqual(self.surface.file_session.anchor_id, 'N-FILE-SESSION')
        self.assertEqual(self.surface.file_session.canonical_type, 'Neutral')
        self.assertEqual(self.surface.file_session.snapshot().path, None)

    def test_capture_only_does_not_save(self):
        self.surface.text_changed('abc')
        BlackHoleEditorInput.receive('save-as', {'path': str(self.path), 'overwrite': False})
        self.assertFalse(self.path.exists())
        self.assertTrue(self.surface.dispatch('read').dirty)

    def test_save_as_utf8_file_clean_document(self):
        self.surface.text_changed('one 📝\nsecond\n')
        revision = self.surface.dispatch('read').revision
        snap = self.surface.save_file_as(str(self.path))
        self.assertEqual(self.path.read_bytes(), 'one 📝\nsecond\n'.encode('utf-8'))
        self.assertFalse(snap.dirty)
        self.assertEqual(snap.revision, revision)
        self.assertEqual(self.surface.file_session.snapshot().path, str(self.path))
        self.assertEqual(self.surface.history.snapshot().undo_count, 1)

    def test_save_existing_association_and_undo_after_save(self):
        self.surface.text_changed('first')
        self.surface.save_file_as(str(self.path))
        self.surface.text_changed('second')
        self.surface.save_file()
        self.assertEqual(self.path.read_text(encoding='utf-8'), 'second')
        self.assertFalse(self.surface.dispatch('read').dirty)
        self.surface.undo()
        self.assertTrue(self.surface.dispatch('read').dirty)
        self.surface.redo()
        self.assertFalse(self.surface.dispatch('read').dirty)

    def test_untitled_save_does_not_create_file_or_change_baseline(self):
        self.surface.text_changed('unsaved')
        before = self.surface.dispatch('read')
        with self.assertRaises(CommandRejected):
            self.surface.save_file()
        self.assertEqual(self.surface.dispatch('read'), before)
        self.assertIsNone(self.surface.file_session.snapshot().path)

    def test_open_valid_file_clears_old_history_and_dirty(self):
        self.path.write_bytes('loaded 📝\n'.encode('utf-8'))
        self.surface.text_changed('old')
        self.surface.text_changed('changed')
        before = self.surface.dispatch('read').revision
        snap = self.surface.open_file(str(self.path), discard=True)
        self.assertEqual(snap.text, 'loaded 📝\n')
        self.assertEqual(snap.revision, before + 1)
        self.assertFalse(snap.dirty)
        self.assertEqual(self.surface.history.snapshot().undo_count, 0)
        with self.assertRaises(CommandRejected):
            self.surface.undo()

    def test_open_dirty_without_confirm_preserves_everything(self):
        self.path.write_text('file', encoding='utf-8')
        self.surface.text_changed('unsaved')
        before = self.surface.dispatch('read')
        hist = self.surface.history.snapshot()
        with self.assertRaisesRegex(CommandRejected, 'unsaved changes'):
            self.surface.open_file(str(self.path))
        self.assertEqual(self.surface.dispatch('read'), before)
        self.assertEqual(self.surface.history.snapshot(), hist)
        self.assertIsNone(self.surface.file_session.snapshot().path)

    def test_new_dirty_requires_discard(self):
        self.surface.text_changed('unsaved')
        with self.assertRaises(CommandRejected):
            self.surface.new_document()
        self.assertEqual(self.surface.dispatch('read').text, 'unsaved')
        snap = self.surface.new_document(discard=True)
        self.assertEqual(snap.text, '')
        self.assertFalse(snap.dirty)
        self.assertEqual(self.surface.history.snapshot().undo_count, 0)

    def test_new_clears_file_association_even_when_clean(self):
        self.surface.text_changed('abc')
        self.surface.save_file_as(str(self.path))
        self.surface.new_document()
        self.assertIsNone(self.surface.file_session.snapshot().path)
        self.assertTrue(self.path.exists())
        self.assertEqual(self.path.read_text(encoding='utf-8'), 'abc')
        with self.assertRaises(CommandRejected):
            self.surface.save_file()

    def test_open_invalid_utf8_preserves_unsaved_and_history(self):
        self.path.write_bytes(b'\xff\xfe')
        self.surface.text_changed('old')
        before = self.surface.dispatch('read')
        hist = self.surface.history.snapshot()
        with self.assertRaisesRegex(CommandRejected, 'UTF-8'):
            self.surface.open_file(str(self.path), discard=True)
        self.assertEqual(self.surface.dispatch('read'), before)
        self.assertEqual(self.surface.history.snapshot(), hist)

    def test_open_missing_file_is_effect_free(self):
        before = self.surface.dispatch('read')
        with self.assertRaises(CommandRejected):
            self.surface.open_file(str(self.path))
        self.assertEqual(self.surface.dispatch('read'), before)

    def test_reject_relative_paths_and_nul(self):
        for path in ('../outside.txt', 'file.txt', '', '/tmp/bad\x00path'):
            with self.subTest(path=path):
                with self.assertRaises(CommandRejected):
                    self.surface.open_file(path)
                with self.assertRaises(CommandRejected):
                    self.surface.save_file_as(path)
        self.assertIsNone(self.surface.file_session.snapshot().path)

    def test_existing_other_file_requires_overwrite_grant(self):
        self.path.write_text('original', encoding='utf-8')
        self.surface.text_changed('replacement')
        with self.assertRaisesRegex(CommandRejected, 'overwrite confirmation'):
            self.surface.save_file_as(str(self.path))
        self.assertEqual(self.path.read_text(encoding='utf-8'), 'original')
        self.assertTrue(self.surface.dispatch('read').dirty)
        self.surface.save_file_as(str(self.path), overwrite=True)
        self.assertEqual(self.path.read_text(encoding='utf-8'), 'replacement')

    def test_external_file_change_blocks_save(self):
        self.surface.text_changed('original')
        self.surface.save_file_as(str(self.path))
        self.surface.text_changed('my edit')
        self.path.write_text('outside edit', encoding='utf-8')
        before = self.surface.dispatch('read')
        with self.assertRaisesRegex(CommandRejected, 'changed externally'):
            self.surface.save_file()
        self.assertEqual(self.path.read_text(encoding='utf-8'), 'outside edit')
        self.assertEqual(self.surface.dispatch('read'), before)
        self.assertTrue(self.surface.dispatch('read').dirty)

    def test_deleted_original_file_blocks_save(self):
        self.surface.text_changed('original')
        self.surface.save_file_as(str(self.path))
        self.surface.text_changed('next')
        self.path.unlink()
        with self.assertRaisesRegex(CommandRejected, 'disappeared'):
            self.surface.save_file()
        self.assertFalse(self.path.exists())

    def test_failed_replace_keeps_original_file_and_dirty_state(self):
        self.surface.text_changed('saved')
        self.surface.save_file_as(str(self.path))
        self.surface.text_changed('unsaved')
        with patch('notepad_files.os.replace', side_effect=OSError('disk failure')):
            with self.assertRaisesRegex(CommandRejected, 'disk failure'):
                self.surface.save_file()
        self.assertEqual(self.path.read_text(encoding='utf-8'), 'saved')
        self.assertTrue(self.surface.dispatch('read').dirty)
        self.assertEqual(list(self.folder.glob('.anchornotepad-*')), [])

    def test_failed_save_as_preserves_association(self):
        self.surface.text_changed('saved')
        self.surface.save_file_as(str(self.path))
        self.surface.text_changed('more')
        second = self.folder / 'missing' / 'other.txt'
        with self.assertRaises(CommandRejected):
            self.surface.save_file_as(str(second))
        self.assertEqual(self.surface.file_session.snapshot().path, str(self.path))
        self.assertTrue(self.surface.dispatch('read').dirty)

    def test_symlink_target_refused(self):
        self.surface.text_changed('data')
        target = self.folder / 'target.txt'
        target.write_text('sensitive', encoding='utf-8')
        link = self.folder / 'shortcut.txt'
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks not supported')
        with self.assertRaisesRegex(CommandRejected, 'symbolic link'):
            self.surface.save_file_as(str(link), overwrite=True)
        self.assertEqual(target.read_text(encoding='utf-8'), 'sensitive')

    def test_no_file_permission_still_rejects_even_valid_payload(self):
        document = NeutralDocument()
        history = NeutralEditHistory(document)
        guard = WhiteHoleCommandGuard()
        with self.assertRaisesRegex(CommandRejected, 'explicitly bound file session'):
            guard.execute(BlackHoleEditorInput.receive('new', {'discard': True}), document, history)
        self.assertEqual(document.snapshot().text, '')

    def test_cross_document_file_session_is_rejected(self):
        another = NeutralEditorSurface()
        another.enable_files()
        intent = BlackHoleEditorInput.receive('new', {'discard': True})
        with self.assertRaisesRegex(CommandRejected, 'another document/history'):
            self.surface.guard.execute(intent, another.document, another.history, self.surface.file_session)

    def test_boolean_validation_not_truthy_confirmation(self):
        self.surface.text_changed('abc')
        before = self.surface.dispatch('read')
        for value in (1, 'yes', None):
            with self.subTest(value=value):
                with self.assertRaises(CommandRejected):
                    self.surface.new_document(discard=value)
                self.assertEqual(self.surface.dispatch('read'), before)

    def test_save_as_rejects_malformed_payload_and_unsupported_effects(self):
        before = self.surface.dispatch('read')
        for action, payload in (
            ('save', 'file.txt'), ('save-as', {'path': str(self.path)}),
            ('save-as', {'path': str(self.path), 'overwrite': 1}),
            ('open', {'path': str(self.path)}), ('new', None),
            ('paste', {'text': 'bad'}), ('network', None),
        ):
            with self.subTest(action=action):
                with self.assertRaises(CommandRejected):
                    self.surface.dispatch(action, payload)
                self.assertEqual(self.surface.dispatch('read'), before)

    def test_read_and_undo_remain_guarded_after_open(self):
        self.path.write_text('initial', encoding='utf-8')
        self.surface.open_file(str(self.path))
        self.surface.text_changed('changed')
        self.assertEqual(self.surface.undo().text, 'initial')
        self.assertFalse(self.surface.dispatch('read').dirty)
        self.assertEqual(self.surface.redo().text, 'changed')
        self.assertTrue(self.surface.dispatch('read').dirty)

    def test_failed_save_as_does_not_clear_redo(self):
        self.surface.text_changed('one')
        self.surface.text_changed('two')
        self.surface.undo()
        history = self.surface.history.snapshot()
        with self.assertRaises(CommandRejected):
            self.surface.save_file_as('relative')
        self.assertEqual(self.surface.history.snapshot(), history)
        self.assertEqual(self.surface.redo().text, 'two')

    def test_file_session_rejects_foreign_history_without_state_change(self):
        with self.assertRaises(ValueError):
            self.surface.file_session.validate_for(NeutralDocument(), NeutralEditHistory(NeutralDocument()))
        self.assertIsNone(self.surface.file_session.snapshot().path)


class TestTkFileCommands(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk
            self.root = tk.Tk()
            self.root.withdraw()
        except (ImportError, tk.TclError) as exc:
            self.skipTest(f'Tk display not available: {exc}')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'gui.txt'
        self.window = TkNotepadWindow(root=self.root)
        self.root.update()

    def tearDown(self):
        if hasattr(self, 'root'):
            try:
                self.root.destroy()
            except Exception:
                pass

    def test_file_menu_enabled_and_shortcuts_bound(self):
        self.assertEqual(self.window.file_menu.entrycget('New', 'state'), 'normal')
        self.assertEqual(self.window.file_menu.entrycget('Open…', 'state'), 'normal')
        self.assertEqual(self.window.file_menu.entrycget('Save As…', 'state'), 'normal')
        self.assertIn('break', self.root.bind('<Control-s>'))
        self.assertEqual(self.window.edit_menu.entrycget('Paste','state'),'normal')

    def test_gui_save_as_and_new(self):
        self.window.text.insert('1.0', 'gui 📝')
        self.root.update()
        self.window.filedialog.asksaveasfilename=lambda **kw: str(self.path)
        self.assertTrue(self.window.save_file_as())
        self.assertEqual(self.path.read_text(encoding='utf-8'), 'gui 📝')
        self.assertNotIn('●', self.root.title())
        self.assertIn('gui.txt', self.root.title())
        self.assertTrue(self.window.new_file())
        self.assertEqual(self.window.text.get('1.0','end-1c'), '')
        self.assertIsNone(self.window.surface.file_session.snapshot().path)

    def test_gui_open_and_cancel_keep_unsaved(self):
        self.path.write_text('from disk', encoding='utf-8')
        self.window.text.insert('1.0', 'my edits')
        self.root.update()
        self.window.filedialog.askopenfilename=lambda **kw: str(self.path)
        self.window.messagebox.askyesno=lambda *a, **kw: False
        self.assertFalse(self.window.open_file())
        self.assertEqual(self.window.surface.dispatch('read').text, 'my edits')
        self.window.messagebox.askyesno=lambda *a, **kw: True
        self.assertTrue(self.window.open_file())
        self.assertEqual(self.window.text.get('1.0','end-1c'), 'from disk')
        self.assertFalse(self.window.surface.dispatch('read').dirty)

    def test_gui_save_failed_keeps_dirty_and_shows_error(self):
        self.window.text.insert('1.0', 'draft')
        self.root.update()
        self.window.filedialog.asksaveasfilename=lambda **kw: str(self.path)
        self.window.messagebox.showerror=lambda *a, **kw: None
        with patch('notepad_files.os.replace', side_effect=OSError('unavailable')):
            self.assertFalse(self.window.save_file())
        self.assertTrue(self.window.surface.dispatch('read').dirty)
        self.assertFalse(self.path.exists())

    def test_gui_save_as_cancel_does_not_clear_dirty(self):
        self.window.text.insert('1.0', 'draft')
        self.root.update()
        self.window.filedialog.asksaveasfilename=lambda **kw: ''
        self.assertFalse(self.window.save_file_as())
        self.assertEqual(self.window.surface.dispatch('read').text, 'draft')
        self.assertTrue(self.window.surface.dispatch('read').dirty)

    def test_gui_new_cancel_preserves_text(self):
        self.window.text.insert('1.0', 'unsaved')
        self.root.update()
        self.window.messagebox.askyesno=lambda *a, **kw: False
        self.assertFalse(self.window.new_file())
        self.assertEqual(self.window.text.get('1.0', 'end-1c'), 'unsaved')


if __name__ == '__main__':
    unittest.main()
