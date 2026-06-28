"""Notiz-Knopf in der Bibliothek: persönlichen Merktext zu einer Eröffnung
anlegen (war mit dem Cutover an der alten Trainingsseite verloren gegangen,
2026-06-28 wieder eingebaut)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets, QtCore  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

PGN = '[Event "x"]\n[ChapterName "Italienisch"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bc4 *\n'


def _win(tmp_path, monkeypatch):
    import qt_app.main_window as mw
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    return mw.MainWindow()


def _select_first_line(win):
    """Markiert den ersten Eröffnungs-Eintrag (keine Überschrift, kein Baum)."""
    for i in range(win.library_list.count()):
        it = win.library_list.item(i)
        d = it.data(QtCore.Qt.UserRole)
        if d is not None and not win._is_tree_item(d) and getattr(d, "name", None):
            win.library_list.clearSelection()
            it.setSelected(True)
            return d
    return None


def test_note_button_creates_and_persists_note(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    f = tmp_path / "Weiss Repertoire.pgn"
    f.write_text(PGN, encoding="utf-8")
    win._add_pgn_source(str(f))
    win._auto_fill_sides_by_filename()
    win._open_library()

    entry = _select_first_line(win)
    assert entry is not None
    win._on_library_selection()
    assert win.note_btn.isEnabled()                      # Notiz-Knopf aktiv bei Auswahl

    monkeypatch.setattr(
        QtWidgets.QInputDialog, "getMultiLineText",
        staticmethod(lambda *a, **k: ("Plan: schnelles d4 anstreben", True)))
    win._edit_note_selected()

    assert win.line_notes.note_of(entry.source_name, entry.name) == "Plan: schnelles d4 anstreben"
    assert win.line_notes.has_note(entry.source_name, entry.name)

    # bleibt auf der Platte (Neustart-fest)
    from opening_trainer.line_notes import LineNotes
    reloaded = LineNotes.load(win.notes_path)
    assert reloaded.note_of(entry.source_name, entry.name) == "Plan: schnelles d4 anstreben"


def test_note_button_disabled_without_selection(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    win._open_library()
    win._on_library_selection()
    assert not win.note_btn.isEnabled()                  # ohne Auswahl deaktiviert
