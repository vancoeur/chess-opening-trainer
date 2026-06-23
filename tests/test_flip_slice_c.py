"""Slice C: die stellungs-basierte Sitzung ist die primäre Tagessitzung."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

PGN_BLACK = """[Event "x"]
[ChapterName "Skandinavisch"]

1. e4 d5 2. exd5 Qxd5 3. Nc3 Qa5 *
"""


def _win(tmp_path, monkeypatch):
    import qt_app.main_window as mw
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    return mw.MainWindow()


def _load_black(win, tmp_path):
    f = tmp_path / "Schwarz Repertoire.pgn"
    f.write_text(PGN_BLACK, encoding="utf-8")
    win._add_pgn_source(str(f))
    win._auto_fill_sides_by_filename()


def test_open_default_session_lands_on_due_when_populated(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _load_black(win, tmp_path)
    win.stack.setCurrentIndex(0)
    win._open_default_session()
    assert win.stack.currentIndex() == 12        # Start-Hub


def test_open_default_session_opens_home_hub(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)             # keine Quellen -> keine Bäume
    win.stack.setCurrentIndex(0)
    win._open_default_session()
    assert win.stack.currentIndex() == 12         # Start-Hub (auch für neue Nutzer)


def test_due_session_button_visible_and_starts(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _load_black(win, tmp_path)
    win._start_next()                             # Sichtbarkeit aktualisieren
    assert not win.due_session_btn.isHidden()     # primärer Knopf sichtbar
    win.due_session_btn.click()
    assert win.stack.currentIndex() == 11         # öffnet die Übersicht
