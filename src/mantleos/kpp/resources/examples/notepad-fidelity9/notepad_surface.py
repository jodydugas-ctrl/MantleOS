"""Round 8 extension of N-EDITOR-SURFACE (Neutral): desktop Notepad.

The window is a projection of the existing document state, not an additional
owner of text, clean baseline, or editing history. Every user-driven text
change and undo/redo operation is captured by BH-EDITOR-INPUT and authorized
by WH-COMMAND-GUARD before the document owner changes.

Round 6 opts the GUI into guarded file operations via N-FILE-SESSION.
Round 7 routes clipboard commands via N-CLIPBOARD-SELECTION and WH.
Round 8 routes Find/Replace via N-SEARCH-REPLACE and WH.
"""
from __future__ import annotations

from collections.abc import Callable

from notepad_document import DocumentSnapshot, NeutralDocument
from notepad_guard import CommandRejected, WhiteHoleCommandGuard
from notepad_history import NeutralEditHistory
from notepad_files import NeutralFileSession
from notepad_input import BlackHoleEditorInput
from notepad_clipboard import NeutralClipboardSelection, SelectionRange
from notepad_search import NeutralSearchReplace, MatchRange, ReplaceResult


class NeutralEditorSurface:
    """Neutral N-EDITOR-SURFACE: map UI interactions to guarded core actions.

    This controller intentionally does not keep a parallel editable text
    value. Tk widgets may transiently display keystrokes, but after every
    dispatch their content is projected from the authoritative snapshot.
    """

    anchor_id = "N-EDITOR-SURFACE"
    canonical_type = "Neutral"

    def __init__(
        self,
        document: NeutralDocument | None = None,
        history: NeutralEditHistory | None = None,
        guard: WhiteHoleCommandGuard | None = None,
        file_session: NeutralFileSession | None = None,
        clipboard: NeutralClipboardSelection | None = None,
        search: NeutralSearchReplace | None = None,
    ) -> None:
        self.document = document if document is not None else NeutralDocument()
        self.history = history if history is not None else NeutralEditHistory(self.document)
        self.guard = guard if guard is not None else WhiteHoleCommandGuard()
        if not isinstance(self.document, NeutralDocument):
            raise TypeError("surface requires N-DOCUMENT")
        if not isinstance(self.history, NeutralEditHistory):
            raise TypeError("surface requires N-EDIT-HISTORY")
        if not isinstance(self.guard, WhiteHoleCommandGuard):
            raise TypeError("surface requires WH-COMMAND-GUARD")
        self.history.validate_for(self.document)
        if file_session is not None and not isinstance(file_session, NeutralFileSession):
            raise TypeError("surface requires N-FILE-SESSION")
        if file_session is not None:
            file_session.validate_for(self.document, self.history)
        self.file_session = file_session
        if clipboard is not None and not isinstance(clipboard, NeutralClipboardSelection):
            raise TypeError("surface requires N-CLIPBOARD-SELECTION")
        if clipboard is not None:
            clipboard.validate_for(self.document, self.history)
        self.clipboard = clipboard
        if search is not None and not isinstance(search, NeutralSearchReplace):
            raise TypeError("surface requires N-SEARCH-REPLACE")
        if search is not None:
            search.validate_for(self.document, self.history)
        self.search = search

    def enable_files(self) -> None:
        """Explicitly opt in to the guarded file operations capability."""
        if self.file_session is None:
            self.file_session = NeutralFileSession(self.document, self.history)

    def enable_clipboard(self, read_text: Callable[[], str],
                         write_text: Callable[[str], None]) -> None:
        """Opt in to the current host's explicitly guarded clipboard adapter."""
        if self.clipboard is not None:
            raise ValueError("clipboard adapter already enabled")
        self.clipboard = NeutralClipboardSelection(
            self.document, self.history, read_text, write_text
        )

    def enable_search(self) -> None:
        """Explicit opt-in for document/history-bound search capability."""
        if self.search is None:
            self.search = NeutralSearchReplace(self.document, self.history)

    def find(self, query: str, start: int = 0, match_case: bool = False,
             wrap: bool = True, backwards: bool = False) -> MatchRange | None:
        return self.dispatch("find", {"query": query, "start": start,
                                      "match_case": match_case, "wrap": wrap,
                                      "backwards": backwards})

    def replace_one(self, query: str, replacement: str, start: int, end: int,
                    match_case: bool = False) -> ReplaceResult:
        return self.dispatch("replace-one", {"query": query, "replacement": replacement,
                                             "start": start, "end": end, "match_case": match_case})

    def replace_all(self, query: str, replacement: str,
                    match_case: bool = False) -> ReplaceResult:
        return self.dispatch("replace-all", {"query": query, "replacement": replacement,
                                             "match_case": match_case})

    def copy_selection(self, start: int, end: int) -> DocumentSnapshot:
        return self.dispatch("copy", {"start": start, "end": end})

    def cut_selection(self, start: int, end: int) -> DocumentSnapshot:
        return self.dispatch("cut", {"start": start, "end": end})

    def paste_at(self, start: int, end: int) -> DocumentSnapshot:
        return self.dispatch("paste", {"start": start, "end": end})

    def select_all(self) -> SelectionRange:
        return self.dispatch("select-all")

    def new_document(self, discard: bool = False) -> DocumentSnapshot:
        return self.dispatch("new", {"discard": discard})

    def open_file(self, path: str, discard: bool = False) -> DocumentSnapshot:
        return self.dispatch("open", {"path": path, "discard": discard})

    def save_file(self) -> DocumentSnapshot:
        return self.dispatch("save")

    def save_file_as(self, path: str, overwrite: bool = False) -> DocumentSnapshot:
        return self.dispatch("save-as", {"path": path, "overwrite": overwrite})

    def dispatch(self, action: str, payload: object = None) -> DocumentSnapshot | SelectionRange | MatchRange | ReplaceResult | None:
        """BH captures; WH validates; Neutral state owners apply/read."""
        intent = BlackHoleEditorInput.receive(action, payload)
        return self.guard.execute(intent, self.document, self.history, self.file_session, self.clipboard, self.search)

    def display(self, sink: Callable[[DocumentSnapshot], None]) -> DocumentSnapshot:
        """Render only a guarded read of authoritative document state."""
        if not callable(sink):
            raise TypeError("display sink must be callable")
        snap = self.dispatch("read")
        sink(snap)
        return snap

    def text_changed(self, text: str) -> DocumentSnapshot:
        return self.dispatch("edit", text)

    def undo(self) -> DocumentSnapshot:
        return self.dispatch("undo")

    def redo(self) -> DocumentSnapshot:
        return self.dispatch("redo")

    def can_exit(self, confirm_discard: Callable[[], bool]) -> bool:
        """Prevent accidental data loss without inventing a save capability."""
        if not self.dispatch("read").dirty:
            return True
        if not callable(confirm_discard):
            raise TypeError("confirmation callback must be callable")
        return confirm_discard() is True


class TkNotepadWindow:
    """Tk host adapter for the one N-EDITOR-SURFACE Anchor.

    Toolkit display interaction is a host effect. This adapter is neither a
    second Anchor nor a state owner; it only forwards user intents and paints
    the resulting snapshots. File and clipboard effects require WH authorization.
    """

    # These unsupported native Text operations must remain blocked: all
    # supported clipboard operations instead use the guarded command path.
    BLOCKED_CLIPBOARD_VIRTUAL_EVENTS = ("<<PasteSelection>>", "<<Clear>>")
    BLOCKED_CLIPBOARD_KEYS = ("<Button-2>", "<ButtonRelease-2>")
    ROUTED_CLIPBOARD_EVENTS = {
        "<<Copy>>": "copy_selection", "<<Cut>>": "cut_selection",
        "<<Paste>>": "paste_clipboard",
    }
    ROUTED_CLIPBOARD_KEYS = {
        "<Control-c>": "copy_selection", "<Control-x>": "cut_selection",
        "<Control-v>": "paste_clipboard", "<Control-C>": "copy_selection",
        "<Control-X>": "cut_selection", "<Control-V>": "paste_clipboard",
        "<Command-c>": "copy_selection", "<Command-x>": "cut_selection",
        "<Command-v>": "paste_clipboard", "<Command-C>": "copy_selection",
        "<Command-X>": "cut_selection", "<Command-V>": "paste_clipboard",
        "<Control-Insert>": "copy_selection", "<Shift-Insert>": "paste_clipboard",
        "<Shift-Delete>": "cut_selection", "<Control-a>": "select_all",
        "<Control-A>": "select_all", "<Command-a>": "select_all",
        "<Command-A>": "select_all",
    }

    def __init__(self, root=None, surface: NeutralEditorSurface | None = None) -> None:
        # Lazy import keeps headless controller tests usable without Tk installed.
        import tkinter as tk
        from tkinter import messagebox, filedialog

        self.tk = tk
        self.messagebox = messagebox
        self.filedialog = filedialog
        self.root = root if root is not None else tk.Tk()
        self.surface = surface if surface is not None else NeutralEditorSurface()
        if not isinstance(self.surface, NeutralEditorSurface):
            raise TypeError("window requires N-EDITOR-SURFACE")
        self.surface.enable_files()
        self.surface.enable_search()
        if self.surface.clipboard is None:
            self.surface.enable_clipboard(self._read_clipboard, self._write_clipboard)
        self._painting = False
        self.search_dialog = None
        self.find_query = tk.StringVar(master=self.root, value="")
        self.replace_value = tk.StringVar(master=self.root, value="")
        self.find_match_case = tk.BooleanVar(master=self.root, value=False)
        self.root.geometry("780x520")
        self.root.minsize(360, 240)

        self._make_menus()
        frame = tk.Frame(self.root)
        frame.pack(fill="both", expand=True)
        scroll = tk.Scrollbar(frame)
        scroll.pack(side="right", fill="y")
        self.text = tk.Text(
            frame, wrap="word", undo=False, exportselection=False,
            yscrollcommand=scroll.set, font=("TkFixedFont", 12),
            padx=12, pady=12,
        )
        self.text.pack(side="left", fill="both", expand=True)
        scroll.config(command=self.text.yview)
        self.status_var = tk.StringVar(master=self.root, value="")
        self.status = tk.Label(self.root, textvariable=self.status_var,
                               anchor="w", padx=10)
        self.status.pack(fill="x")

        self.text.bind("<<Modified>>", self._on_text_modified)
        self.text.bind("<Control-z>", self._undo_event)
        self.text.bind("<Control-y>", self._redo_event)
        self.text.bind("<Control-Shift-Z>", self._redo_event)
        self.text.bind("<Command-z>", self._undo_event)
        self.text.bind("<Command-Shift-Z>", self._redo_event)
        for binding in self.BLOCKED_CLIPBOARD_VIRTUAL_EVENTS + self.BLOCKED_CLIPBOARD_KEYS:
            self.text.bind(binding, self._blocked_clipboard)
        for binding, method_name in (list(self.ROUTED_CLIPBOARD_EVENTS.items())
                                     + list(self.ROUTED_CLIPBOARD_KEYS.items())):
            self.text.bind(binding, self._guarded_clipboard_event(method_name))
        for keysym, method in (("n", self.new_file), ("o", self.open_file),
                               ("s", self.save_file)):
            for modifier in ("Control", "Command"):
                self.root.bind(f"<{modifier}-{keysym}>", lambda _e, m=method: (m(), "break")[1])
        for modifier in ("Control", "Command"):
            for target in (self.root, self.text):
                target.bind(f"<{modifier}-f>", lambda _e: (self.open_find(), "break")[1])
                target.bind(f"<{modifier}-h>", lambda _e: (self.open_replace(), "break")[1])
        for target in (self.root, self.text):
            target.bind("<F3>", lambda _e: (self.find_next(), "break")[1])
            target.bind("<Shift-F3>", lambda _e: (self.find_previous(), "break")[1])
        for modifier in ("Control", "Command"):
            self.root.bind(f"<{modifier}-Shift-S>", lambda _e: (self.save_file_as(), "break")[1])
        self.root.protocol("WM_DELETE_WINDOW", self.request_close)
        self.surface.display(self._paint)
        self.text.focus_set()

    def _make_menus(self) -> None:
        tk = self.tk
        bar = tk.Menu(self.root)
        file_menu = tk.Menu(bar, tearoff=False)
        file_menu.add_command(label="New", command=self.new_file, accelerator="Ctrl+N")
        file_menu.add_command(label="Open…", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Save", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As…", command=self.save_file_as, accelerator="Ctrl+Shift+S")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.request_close)
        bar.add_cascade(label="File", menu=file_menu)

        self.edit_menu = tk.Menu(bar, tearoff=False)
        self.edit_menu.add_command(label="Undo", command=self.undo, state="disabled")
        self.edit_menu.add_command(label="Redo", command=self.redo, state="disabled")
        self.edit_menu.add_separator()
        for name, method, accelerator in (
            ("Cut", self.cut_selection, "Ctrl+X"),
            ("Copy", self.copy_selection, "Ctrl+C"),
            ("Paste", self.paste_clipboard, "Ctrl+V"),
            ("Select All", self.select_all, "Ctrl+A"),
        ):
            self.edit_menu.add_command(label=name, command=method, accelerator=accelerator)
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Find…", command=self.open_find, accelerator="Ctrl+F")
        self.edit_menu.add_command(label="Find Next", command=self.find_next, accelerator="F3")
        self.edit_menu.add_command(label="Find Previous", command=self.find_previous, accelerator="Shift+F3")
        self.edit_menu.add_command(label="Replace…", command=self.open_replace, accelerator="Ctrl+H")
        bar.add_cascade(label="Edit", menu=self.edit_menu)
        self.root.config(menu=bar)
        self.file_menu = file_menu

    @staticmethod
    def _blocked_clipboard(_event) -> str:
        return "break"

    def _read_clipboard(self) -> str:
        """OS clipboard reads happen only after an authorized paste intent."""
        return self.root.clipboard_get()

    def _write_clipboard(self, text: str) -> None:
        """OS clipboard writes happen only after an authorized cut/copy intent."""
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update_idletasks()

    def _guarded_clipboard_event(self, method_name: str):
        def callback(_event):
            getattr(self, method_name)()
            return "break"  # prevent Tk class binding from bypassing WH
        return callback

    def _selected_offsets(self) -> tuple[int, int] | None:
        """Convert transient Tk selection to document-codepoint offsets."""
        try:
            start = self.text.index("sel.first")
            end = self.text.index("sel.last")
        except self.tk.TclError:
            return None
        # Tcl's "chars" count can count supplementary Unicode as two units.
        # Python's document offsets count Unicode code points, so derive the
        # offsets from the actual Tk text prefix instead.
        return (len(self.text.get("1.0", start)), len(self.text.get("1.0", end)))

    def _selection_or_caret(self) -> tuple[int, int]:
        selected = self._selected_offsets()
        if selected is not None:
            return selected
        offset = len(self.text.get("1.0", "insert"))
        return offset, offset

    def _clipboard_action(self, action, new_cursor: int | None = None) -> bool:
        try:
            snapshot = action()
            self._paint(snapshot)
            if new_cursor is not None:
                self.text.mark_set("insert", f"1.0+{new_cursor}c")
                self.text.tag_remove("sel", "1.0", "end")
            return True
        except CommandRejected as exc:
            self.surface.display(self._paint)
            self.messagebox.showerror("Clipboard operation failed", str(exc), parent=self.root)
            return False

    def copy_selection(self) -> bool:
        selected = self._selected_offsets()
        if selected is None or selected[0] == selected[1]:
            return False
        return self._clipboard_action(lambda: self.surface.copy_selection(*selected))

    def cut_selection(self) -> bool:
        selected = self._selected_offsets()
        if selected is None or selected[0] == selected[1]:
            return False
        return self._clipboard_action(lambda: self.surface.cut_selection(*selected), selected[0])

    def paste_clipboard(self) -> bool:
        start, end = self._selection_or_caret()
        try:
            # The guarded read must be the one that supplies the inserted text.
            # Compute the cursor from the actual document delta, not an unguarded
            # second clipboard read that could return a different value.
            before = self.surface.dispatch("read")
            after = self.surface.paste_at(start, end)
            length = len(after.text) - (len(before.text) - (end - start))
            self._paint(after)
            self.text.mark_set("insert", f"1.0+{start + length}c")
            self.text.tag_remove("sel", "1.0", "end")
            return True
        except CommandRejected as exc:
            self.surface.display(self._paint)
            self.messagebox.showerror("Clipboard operation failed", str(exc), parent=self.root)
            return False

    def select_all(self) -> bool:
        try:
            selection = self.surface.select_all()
        except CommandRejected as exc:
            self.messagebox.showerror("Selection failed", str(exc), parent=self.root)
            return False
        self.text.tag_remove("sel", "1.0", "end")
        if selection.end > selection.start:
            self.text.tag_add("sel", f"1.0+{selection.start}c", f"1.0+{selection.end}c")
            self.text.mark_set("insert", f"1.0+{selection.end}c")
        return True

    def _open_search_dialog(self, replacing: bool) -> None:
        """Nonmodal transient Tk inputs; never an authoritative document store."""
        tk = self.tk
        if self.search_dialog is not None and self.search_dialog.winfo_exists():
            if replacing != self._replace_widgets_shown:
                self._close_search_dialog()
            else:
                self.search_dialog.lift()
                self.search_entry.focus_set()
                return
        dialog = tk.Toplevel(self.root)
        dialog.title("Replace" if replacing else "Find")
        dialog.transient(self.root)
        dialog.resizable(False, False)
        self.search_dialog = dialog
        self._replace_widgets_shown = replacing
        tk.Label(dialog, text="Find what:").grid(row=0, column=0, padx=8, pady=6, sticky="w")
        self.search_entry = tk.Entry(dialog, textvariable=self.find_query, width=32)
        self.search_entry.grid(row=0, column=1, padx=8, pady=6, sticky="ew")
        if replacing:
            tk.Label(dialog, text="Replace with:").grid(row=1, column=0, padx=8, pady=6, sticky="w")
            tk.Entry(dialog, textvariable=self.replace_value, width=32).grid(row=1, column=1, padx=8, pady=6)
        opts = tk.Frame(dialog)
        opts.grid(row=2, column=0, columnspan=2, sticky="w", padx=8)
        tk.Checkbutton(opts, text="Match case", variable=self.find_match_case).pack(side="left")
        controls = tk.Frame(dialog)
        controls.grid(row=3, column=0, columnspan=2, padx=8, pady=8)
        tk.Button(controls, text="Find Next", command=self.find_next).pack(side="left", padx=3)
        if replacing:
            tk.Button(controls, text="Replace", command=self.replace_selection).pack(side="left", padx=3)
            tk.Button(controls, text="Replace All", command=self.replace_all).pack(side="left", padx=3)
        tk.Button(controls, text="Close", command=self._close_search_dialog).pack(side="left", padx=3)
        dialog.protocol("WM_DELETE_WINDOW", self._close_search_dialog)
        dialog.bind("<Escape>", lambda _e: (self._close_search_dialog(), "break")[1])
        self.search_entry.focus_set()
        self.search_entry.selection_range(0, "end")

    def _close_search_dialog(self) -> None:
        if self.search_dialog is not None:
            try:
                self.search_dialog.destroy()
            except self.tk.TclError:
                pass
            self.search_dialog = None
        self.text.focus_set()

    def open_find(self) -> None:
        self._open_search_dialog(False)

    def open_replace(self) -> None:
        self._open_search_dialog(True)

    def _find_in_direction(self, backwards: bool) -> bool:
        query = self.find_query.get()
        if not query:
            self.open_find()
            return False
        selected = self._selected_offsets()
        # The next match starts after the current selection; previous search
        # begins before its start. No document mutation from a search.
        origin = (selected[0] if backwards else selected[1]) if selected else None
        if origin is None:
            origin = len(self.text.get("1.0", "insert"))
        try:
            match = self.surface.find(query, origin, bool(self.find_match_case.get()),
                                      wrap=True, backwards=backwards)
        except CommandRejected as exc:
            self.messagebox.showerror("Find failed", str(exc), parent=self.root)
            return False
        if match is None:
            self.root.bell()
            return False
        self.text.tag_remove("sel", "1.0", "end")
        self.text.tag_add("sel", f"1.0+{match.start}c", f"1.0+{match.end}c")
        self.text.mark_set("insert", f"1.0+{match.start}c")
        self.text.see(f"1.0+{match.start}c")
        return True

    def find_next(self) -> bool:
        return self._find_in_direction(False)

    def find_previous(self) -> bool:
        return self._find_in_direction(True)

    def replace_selection(self) -> bool:
        selected = self._selected_offsets()
        if selected is None:
            return self.find_next()
        try:
            result = self.surface.replace_one(self.find_query.get(),
                                              self.replace_value.get(), *selected,
                                              match_case=bool(self.find_match_case.get()))
        except CommandRejected as exc:
            self.messagebox.showerror("Replace failed", str(exc), parent=self.root)
            return False
        self._paint(result.snapshot)
        self.text.tag_remove("sel", "1.0", "end")
        self.text.mark_set("insert", f"1.0+{selected[0] + len(self.replace_value.get())}c")
        return True

    def replace_all(self) -> int:
        try:
            result = self.surface.replace_all(self.find_query.get(), self.replace_value.get(),
                                              match_case=bool(self.find_match_case.get()))
        except CommandRejected as exc:
            self.messagebox.showerror("Replace failed", str(exc), parent=self.root)
            return 0
        self._paint(result.snapshot)
        self.text.tag_remove("sel", "1.0", "end")
        self.messagebox.showinfo("Replace All", f"Replaced {result.count} occurrence(s).", parent=self.root)
        return result.count

    def _on_text_modified(self, _event=None) -> None:
        if self._painting or not self.text.edit_modified():
            return
        changed = self.text.get("1.0", "end-1c")
        try:
            snap = self.surface.text_changed(changed)
        except CommandRejected as exc:
            # Never leave a rejected widget edit diverging from the document.
            self.surface.display(self._paint)
            self.messagebox.showerror("Edit rejected", str(exc), parent=self.root)
            return
        self._paint(snap)

    def _paint(self, snapshot: DocumentSnapshot) -> None:
        # A Tk Text field is a cache of the snapshot, NEVER a second owner.
        self._painting = True
        try:
            displayed = self.text.get("1.0", "end-1c")
            if displayed != snapshot.text:
                offset = len(self.text.get("1.0", "insert"))
                self.text.delete("1.0", "end")
                self.text.insert("1.0", snapshot.text)
                self.text.mark_set("insert", f"1.0+{min(offset, len(snapshot.text))}c")
            self.text.edit_modified(False)
            path = self.surface.file_session.snapshot().path if self.surface.file_session else None
            import os
            filename = os.path.basename(path) if path else "Untitled"
            self.root.title(("● " if snapshot.dirty else "") + filename + " — Anchor Notepad")
            self.status_var.set(
                ("Unsaved edits" if snapshot.dirty else "No unsaved edits")
                + "  |  " + (path if path else "Untitled (not saved)")
            )
            history = self.surface.history.snapshot()
            self.edit_menu.entryconfigure("Undo", state="normal" if history.undo_count else "disabled")
            self.edit_menu.entryconfigure("Redo", state="normal" if history.redo_count else "disabled")
        finally:
            self._painting = False

    def undo(self) -> None:
        try:
            self._paint(self.surface.undo())
        except CommandRejected:
            self.surface.display(self._paint)

    def redo(self) -> None:
        try:
            self._paint(self.surface.redo())
        except CommandRejected:
            self.surface.display(self._paint)

    def _undo_event(self, _event) -> str:
        self.undo()
        return "break"

    def _redo_event(self, _event) -> str:
        self.redo()
        return "break"

    def _confirm_discard(self) -> bool:
        if not self.surface.dispatch("read").dirty:
            return True
        return self.messagebox.askyesno(
            "Unsaved changes", "Discard your unsaved edits?", parent=self.root
        ) is True

    def _file_action(self, action) -> bool:
        try:
            self._paint(action())
            return True
        except CommandRejected as exc:
            self.surface.display(self._paint)
            self.messagebox.showerror("File operation failed", str(exc), parent=self.root)
            return False

    def new_file(self) -> bool:
        if not self._confirm_discard():
            return False
        return self._file_action(lambda: self.surface.new_document(discard=True))

    def open_file(self) -> bool:
        path = self.filedialog.askopenfilename(
            parent=self.root, title="Open text file",
            filetypes=[("Text files", "*.txt"), ("All files", "*")],
        )
        if not path or not self._confirm_discard():
            return False
        return self._file_action(lambda: self.surface.open_file(path, discard=True))

    def save_file(self) -> bool:
        session = self.surface.file_session
        if session is None or session.snapshot().path is None:
            return self.save_file_as()
        return self._file_action(self.surface.save_file)

    def save_file_as(self) -> bool:
        path = self.filedialog.asksaveasfilename(
            parent=self.root, title="Save text file",
            defaultextension=".txt", confirmoverwrite=True,
            filetypes=[("Text files", "*.txt"), ("All files", "*")],
        )
        if not path:
            return False
        # The native file dialog handles overwrite confirmation; the explicit
        # permission flag is also checked by WH before any host write.
        return self._file_action(lambda: self.surface.save_file_as(path, overwrite=True))

    def request_close(self) -> bool:
        def confirm() -> bool:
            return self.messagebox.askyesno(
                "Discard unsaved changes?",
                "This document is not saved. Closing will discard its text. Exit anyway?",
                parent=self.root,
            )
        if not self.surface.can_exit(confirm):
            return False
        self.root.destroy()
        return True

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    """Launch the local, file-capable Notepad desktop application."""
    TkNotepadWindow().run()


if __name__ == "__main__":
    main()
