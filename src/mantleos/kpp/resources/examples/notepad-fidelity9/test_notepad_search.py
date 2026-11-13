"""Fidelity 8 verification: search/replace semantics and cumulative retention."""
import tempfile
from pathlib import Path
import unittest

from notepad_search import MatchRange, ReplaceResult, NeutralSearchReplace, SearchOperationError
from notepad_document import NeutralDocument
from notepad_history import NeutralEditHistory
from notepad_guard import WhiteHoleCommandGuard, CommandRejected
from notepad_input import BlackHoleEditorInput
from notepad_surface import NeutralEditorSurface, TkNotepadWindow


class TestSearchGuard(unittest.TestCase):
    def setUp(self):
        self.surface = NeutralEditorSurface()
        self.surface.enable_search()

    def state(self):
        return self.surface.document.snapshot(), self.surface.history.snapshot()

    def test_anchor_identity_and_binding(self):
        self.assertEqual(self.surface.search.anchor_id, 'N-SEARCH-REPLACE')
        self.assertEqual(self.surface.search.canonical_type, 'Neutral')
        self.assertIs(self.surface.search._document, self.surface.document)
        self.assertIs(self.surface.search._history, self.surface.history)

    def test_unbound_guard_denies_find_and_replace_without_mutation(self):
        doc = NeutralDocument('abc')
        history = NeutralEditHistory(doc)
        guard = WhiteHoleCommandGuard()
        original = (doc.snapshot(), history.snapshot())
        for action in ('find', 'replace-one', 'replace-all'):
            with self.subTest(action=action):
                with self.assertRaises(CommandRejected):
                    guard.execute(BlackHoleEditorInput.receive(action, None), doc, history)
                self.assertEqual((doc.snapshot(), history.snapshot()), original)

    def test_binding_foreign_document_and_history_rejected(self):
        other = NeutralEditorSurface()
        with self.assertRaisesRegex(ValueError, 'another document'):
            NeutralSearchReplace(other.document, self.surface.history)
        other.search = self.surface.search
        before = (other.document.snapshot(), other.history.snapshot())
        with self.assertRaisesRegex(CommandRejected, 'another document'):
            other.find('x')
        self.assertEqual((other.document.snapshot(), other.history.snapshot()), before)

    def test_stale_history_denies_find_without_state_effect(self):
        self.surface.document.replace_text('untracked')
        before = self.state()
        with self.assertRaises(CommandRejected):
            self.surface.find('untracked')
        self.assertEqual(self.state(), before)

    def test_find_forward_matches_positions_and_no_state_change(self):
        self.surface.text_changed('one two one')
        before = self.state()
        self.assertEqual(self.surface.find('one'), MatchRange(0, 3))
        self.assertEqual(self.surface.find('one', 3), MatchRange(8, 11))
        self.assertEqual(self.state(), before)

    def test_find_backward_and_wrap(self):
        self.surface.text_changed('one two one')
        self.assertEqual(self.surface.find('one', 8, backwards=True), MatchRange(0, 3))
        self.assertEqual(self.surface.find('one', 0, backwards=True), MatchRange(8, 11))
        self.assertIsNone(self.surface.find('one', 0, backwards=True, wrap=False))
        self.assertEqual(self.surface.find('one', 11), MatchRange(0, 3))
        self.assertIsNone(self.surface.find('one', 11, wrap=False))

    def test_case_sensitive_and_insensitive(self):
        self.surface.text_changed('ABC abc Abc')
        self.assertEqual(self.surface.find('abc', match_case=True), MatchRange(4, 7))
        self.assertEqual(self.surface.find('abc', match_case=False), MatchRange(0, 3))
        self.assertEqual(self.surface.find('abc', 3, match_case=False), MatchRange(4, 7))

    def test_unicode_codepoint_ranges(self):
        self.surface.text_changed('📝—hello 📝hello')
        self.assertEqual(self.surface.find('📝'), MatchRange(0, 1))
        self.assertEqual(self.surface.find('📝', 1), MatchRange(8, 9))
        self.assertEqual(self.surface.find('hello', 3), MatchRange(9, 14))

    def test_literal_regex_characters(self):
        self.surface.text_changed('a.b a+b [x] a.b')
        self.assertEqual(self.surface.find('a.b'), MatchRange(0, 3))
        self.assertEqual(self.surface.find('[x]'), MatchRange(8, 11))

    def test_missing_match_does_not_create_history(self):
        self.surface.text_changed('abc')
        before = self.state()
        self.assertIsNone(self.surface.find('missing'))
        self.assertEqual(self.state(), before)

    def test_bad_find_payloads_preserve_document(self):
        self.surface.text_changed('abc')
        good = dict(query='a', start=0, match_case=False, wrap=True, backwards=False)
        before = self.state()
        broken = [None, 'bad', {}, {**good, 'extra': 1},
                  {**good, 'query': ''}, {**good, 'query': None},
                  {**good, 'start': -1}, {**good, 'start': True},
                  {**good, 'start': 4}, {**good, 'match_case': 1},
                  {**good, 'wrap': 'true'}, {**good, 'backwards': 0}]
        for payload in broken:
            with self.subTest(payload=repr(payload)), self.assertRaises(CommandRejected):
                self.surface.dispatch('find', payload)
            self.assertEqual(self.state(), before)

    def test_replace_one_matches_literal_range_only(self):
        self.surface.text_changed('one two one')
        result = self.surface.replace_one('one', 'three', 8, 11)
        self.assertIsInstance(result, ReplaceResult)
        self.assertEqual(result.count, 1)
        self.assertEqual(result.snapshot.text, 'one two three')
        self.assertEqual(self.surface.history.snapshot().undo_count, 2)
        self.assertEqual(self.surface.undo().text, 'one two one')
        self.assertEqual(self.surface.redo().text, 'one two three')

    def test_replace_one_rejects_mismatched_selection_no_mutation(self):
        self.surface.text_changed('abc ABC')
        before = self.state()
        for args in [('abc', 'X', 4, 7, True), ('ab', 'X', 0, 3, False),
                     ('abc', 'X', 0, 0, False), ('abc', 'X', 0, 10, False)]:
            with self.subTest(args=args), self.assertRaises(CommandRejected):
                self.surface.replace_one(*args)
            self.assertEqual(self.state(), before)

    def test_replace_one_case_insensitive_and_unicode(self):
        self.surface.text_changed('📝Hi hi')
        self.assertEqual(self.surface.replace_one('HI', '📝', 1, 3).snapshot.text, '📝📝 hi')

    def test_replace_one_same_text_is_noop_history(self):
        self.surface.text_changed('abc')
        before = self.state()
        result = self.surface.replace_one('abc', 'abc', 0, 3)
        self.assertEqual(result.count, 1)
        self.assertEqual(self.state(), before)

    def test_replace_all_replaces_many_as_one_undo(self):
        self.surface.text_changed('a A a')
        result = self.surface.replace_all('a', '📝')
        self.assertEqual((result.count, result.snapshot.text), (3, '📝 📝 📝'))
        self.assertEqual(self.surface.history.snapshot().undo_count, 2)
        self.assertEqual(self.surface.undo().text, 'a A a')
        self.assertEqual(self.surface.redo().text, '📝 📝 📝')

    def test_replace_all_case_sensitive_and_delete(self):
        self.surface.text_changed('a A a')
        result = self.surface.replace_all('a', '', match_case=True)
        self.assertEqual((result.count, result.snapshot.text), (2, ' A '))

    def test_replace_all_replacement_is_literal_not_regex(self):
        self.surface.text_changed('a.a.a.')
        result = self.surface.replace_all('a.', r'\g<1>')
        self.assertEqual((result.count, result.snapshot.text), (3, r'\g<1>\g<1>\g<1>'))

    def test_replace_all_no_match_preserves_revision_redo(self):
        self.surface.text_changed('first')
        self.surface.text_changed('second')
        self.surface.undo()
        before = self.state()
        result = self.surface.replace_all('absent', 'x')
        self.assertEqual((result.count, result.snapshot), (0, before[0]))
        self.assertEqual(self.state(), before)
        self.assertEqual(self.surface.redo().text, 'second')

    def test_replace_all_same_replacement_preserves_revision(self):
        self.surface.text_changed('abc abc')
        before = self.state()
        self.assertEqual(self.surface.replace_all('abc', 'abc').count, 2)
        self.assertEqual(self.state(), before)

    def test_bad_replace_payloads_preserve_document(self):
        self.surface.text_changed('abc')
        one = dict(query='a', replacement='x', start=0, end=1, match_case=False)
        all_ = dict(query='a', replacement='x', match_case=False)
        before = self.state()
        for payload in (None, {**one, 'start': True}, {**one, 'end': -1},
                        {**one, 'replacement': None}, {**one, 'query': ''},
                        {**one, 'match_case': None}, {**one, 'extra': 2},
                        {**one, 'start': 2, 'end': 1}):
            with self.subTest(one=repr(payload)), self.assertRaises(CommandRejected):
                self.surface.dispatch('replace-one', payload)
            self.assertEqual(self.state(), before)
        for payload in (None, {**all_, 'replacement': 2}, {**all_, 'query': ''},
                        {**all_, 'match_case': 1}, {**all_, 'extra': 2}):
            with self.subTest(all_=repr(payload)), self.assertRaises(CommandRejected):
                self.surface.dispatch('replace-all', payload)
            self.assertEqual(self.state(), before)

    def test_search_preserves_file_baseline_and_save(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'file.txt'
            self.surface.enable_files()
            self.surface.text_changed('foo foo')
            self.surface.save_file_as(str(path))
            self.assertFalse(self.surface.dispatch('read').dirty)
            self.assertEqual(self.surface.find('foo'), MatchRange(0, 3))
            self.assertFalse(self.surface.dispatch('read').dirty)
            self.surface.replace_all('foo', 'bar')
            self.assertTrue(self.surface.dispatch('read').dirty)
            self.surface.undo()
            self.assertFalse(self.surface.dispatch('read').dirty)
            self.surface.redo()
            self.surface.save_file()
            self.assertEqual(path.read_text(encoding='utf-8'), 'bar bar')
            self.assertFalse(self.surface.dispatch('read').dirty)

    def test_search_capability_persists_across_new_open(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'file.txt'
            path.write_text('α β α', encoding='utf-8')
            self.surface.enable_files()
            self.surface.text_changed('original')
            self.surface.new_document(discard=True)
            self.surface.open_file(str(path))
            self.assertEqual(self.surface.find('α', 1), MatchRange(4, 5))
            self.assertEqual(self.surface.history.snapshot().undo_count, 0)

    def test_existing_clipboard_and_search_coexist(self):
        host = {'text': 'paste'}
        self.surface.enable_clipboard(lambda: host['text'], lambda x: host.__setitem__('text', x))
        self.surface.text_changed('foo foo')
        self.surface.copy_selection(0, 3)
        self.assertEqual(host['text'], 'foo')
        self.surface.replace_one('foo', 'bar', 0, 3)
        self.surface.paste_at(0, 0)
        self.assertEqual(self.surface.dispatch('read').text, 'foobar foo')

    def test_empty_document_find_and_replace_all_are_effect_free(self):
        before = self.state()
        self.assertIsNone(self.surface.find('x'))
        result = self.surface.replace_all('x', 'y')
        self.assertEqual(result.count, 0)
        self.assertEqual(self.state(), before)

    def test_nonoverlapping_literal_replace_all(self):
        self.surface.text_changed('aaaa')
        result = self.surface.replace_all('aa', 'b')
        self.assertEqual((result.count, result.snapshot.text), (2, 'bb'))

    def test_find_exact_multiline_phrase(self):
        self.surface.text_changed('line one\nline two\nline one')
        self.assertEqual(self.surface.find('one\nline'), MatchRange(5, 13))

    def test_replace_all_multiline_and_emoji(self):
        self.surface.text_changed('x📝\nx📝')
        result = self.surface.replace_all('x📝', '📝')
        self.assertEqual((result.count, result.snapshot.text), (2, '📝\n📝'))

    def test_replace_after_undo_clears_redo(self):
        self.surface.text_changed('a')
        self.surface.text_changed('a b')
        self.surface.undo()
        self.surface.replace_all('a', 'z')
        self.assertEqual(self.surface.history.snapshot().redo_count, 0)
        with self.assertRaises(CommandRejected):
            self.surface.redo()

    def test_unsupported_network_action_remains_rejected(self):
        before = self.state()
        with self.assertRaises(CommandRejected):
            self.surface.dispatch('fetch-url', {'url': 'https://example.org'})
        self.assertEqual(self.state(), before)

    def test_same_document_guard_legacy_without_search(self):
        doc = NeutralDocument()
        history = NeutralEditHistory(doc)
        guard = WhiteHoleCommandGuard()
        self.assertEqual(guard.execute(BlackHoleEditorInput.receive('edit', 'abc'), doc, history).text, 'abc')
        self.assertEqual(guard.execute(BlackHoleEditorInput.receive('read'), doc).text, 'abc')


class TestTkSearch(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk
            self.root = tk.Tk()
            self.root.withdraw()
        except (ImportError, tk.TclError) as exc:
            self.skipTest(f'Tk display not available: {exc}')
        self.window = TkNotepadWindow(root=self.root)
        self.window.messagebox.showerror = lambda *args, **kwargs: self.fail(str(args))
        self.window.messagebox.showinfo = lambda *args, **kwargs: None
        self.root.update()

    def tearDown(self):
        if getattr(self, 'root', None):
            try:
                self.root.destroy()
            except Exception:
                pass

    def set_text(self, text):
        self.window.surface.text_changed(text)
        self.window.surface.display(self.window._paint)
        self.root.update()

    def test_gui_search_menu_and_shortcuts(self):
        for name in ('Find…', 'Find Next', 'Find Previous', 'Replace…'):
            self.assertEqual(self.window.edit_menu.entrycget(name, 'state'), 'normal')
        for seq in ('<Control-f>', '<Control-h>', '<Command-f>', '<Command-h>', '<F3>', '<Shift-F3>'):
            self.assertIn('break', self.root.bind(seq))
        self.assertIsInstance(self.window.surface.search, NeutralSearchReplace)

    def test_gui_find_next_and_previous_unicode(self):
        self.set_text('hi 📝 hi 📝')
        self.window.find_query.set('📝')
        self.window.text.mark_set('insert', '1.0')
        self.assertTrue(self.window.find_next())
        self.assertEqual(self.window.text.get('sel.first', 'sel.last'), '📝')
        self.assertEqual(self.window._selected_offsets(), (3, 4))
        self.assertTrue(self.window.find_next())
        self.assertEqual(self.window._selected_offsets(), (8, 9))
        self.assertTrue(self.window.find_previous())
        self.assertEqual(self.window._selected_offsets(), (3, 4))

    def test_gui_find_does_not_edit_document_or_history(self):
        self.set_text('abc abc')
        self.window.find_query.set('abc')
        before = (self.window.surface.document.snapshot(), self.window.surface.history.snapshot())
        self.window.find_next()
        self.assertEqual((self.window.surface.document.snapshot(), self.window.surface.history.snapshot()), before)

    def test_gui_replace_selected_undoable(self):
        self.set_text('cat cat')
        self.window.find_query.set('cat')
        self.window.replace_value.set('dog')
        self.window.text.tag_add('sel', '1.0', '1.3')
        self.assertTrue(self.window.replace_selection())
        self.assertEqual(self.window.text.get('1.0', 'end-1c'), 'dog cat')
        self.assertEqual(self.window.surface.undo().text, 'cat cat')

    def test_gui_replace_all_single_history(self):
        self.set_text('a a a')
        self.window.find_query.set('a')
        self.window.replace_value.set('β')
        self.assertEqual(self.window.replace_all(), 3)
        self.assertEqual(self.window.text.get('1.0', 'end-1c'), 'β β β')
        self.assertEqual(self.window.surface.history.snapshot().undo_count, 2)

    def test_gui_find_and_replace_dialog_open_close(self):
        self.window.open_find()
        self.assertTrue(self.window.search_dialog.winfo_exists())
        self.assertEqual(self.window.search_dialog.title(), 'Find')
        self.window.open_replace()
        self.assertTrue(self.window.search_dialog.winfo_exists())
        self.assertEqual(self.window.search_dialog.title(), 'Replace')
        self.window._close_search_dialog()
        self.assertIsNone(self.window.search_dialog)

    def test_gui_search_shortcut_bindings_intercept_text_widget(self):
        for sequence in ('<Control-f>', '<Control-h>', '<Command-f>', '<Command-h>',
                         '<F3>', '<Shift-F3>'):
            self.assertIn('break', self.window.text.bind(sequence))

    def test_gui_find_previous_from_caret_without_selection(self):
        self.set_text('first and first')
        self.window.find_query.set('first')
        self.window.text.mark_set('insert', 'end-1c')
        self.assertTrue(self.window.find_previous())
        self.assertEqual(self.window._selected_offsets(), (10, 15))

    def test_gui_find_absent_preserves_state(self):
        self.set_text('safe text')
        self.window.find_query.set('absent')
        before = (self.window.surface.document.snapshot(), self.window.surface.history.snapshot())
        self.assertFalse(self.window.find_next())
        self.assertEqual((self.window.surface.document.snapshot(), self.window.surface.history.snapshot()), before)

    def test_gui_malformed_query_error_does_not_edit(self):
        self.set_text('unchanged')
        self.window.find_query.set('')
        self.window.replace_value.set('X')
        self.window.messagebox.showerror = lambda *args, **kw: None
        before = (self.window.surface.document.snapshot(), self.window.surface.history.snapshot())
        self.assertEqual(self.window.replace_all(), 0)
        self.assertEqual((self.window.surface.document.snapshot(), self.window.surface.history.snapshot()), before)


if __name__ == '__main__':
    unittest.main()
