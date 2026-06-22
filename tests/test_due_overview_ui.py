"""Schritt 3: »Heute fällig«-Übersicht — Vorschau, Aufschlüsselung, gezieltes Üben."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

PGN_BLACK = """[Event "x"]
[ChapterName "Skandinavisch"]

1. e4 d5 2. exd5 Qxd5 3. Nc3 Qa5 *

[Event "x"]
[ChapterName "Caro-Kann"]

1. e4 c6 2. d4 d5 3. Nc3 dxe4 *
"""


def _win(tmp_path, monkeypatch):
    import qt_app.main_window as mw
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    win = mw.MainWindow()
    from qt_app import i18n
    i18n.set_language("en")
    return win


def _load_black(win, tmp_path):
    f = tmp_path / "Schwarz Repertoire.pgn"
    f.write_text(PGN_BLACK, encoding="utf-8")
    win._add_pgn_source(str(f))
    win._auto_fill_sides_by_filename()


def test_overview_lists_openings_and_forecast(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _load_black(win, tmp_path)
    win._open_due_overview()
    assert win.stack.currentIndex() == 11
    assert "Today:" in win.due_overview_forecast.text()
    # zwei Eröffnungen als Zeilen (mit Knopf-Widgets)
    rows = [win.due_overview_list.item(i) for i in range(win.due_overview_list.count())]
    widgets = [win.due_overview_list.itemWidget(it) for it in rows]
    assert sum(1 for w in widgets if w is not None) == 2
    assert "Train all" in win.due_overview_all_btn.text()


def test_overview_train_one_opening_filters_session(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _load_black(win, tmp_path)
    win._open_due_overview()
    # gezielt nur den Caro-Kann-Baum üben
    caro = next(t for t in win.tree_store.all() if "Caro" in t.name)
    win._start_due_session(only_tree=caro)
    assert win.stack.currentIndex() == 10
    assert win._due_total > 0
    # alle Items dieser Sitzung gehören zum Caro-Baum
    assert all(tr is caro for tr, _node, _color in win._due_queue)


def test_overview_empty_state(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)              # nichts geladen
    win._open_due_overview()
    assert win.stack.currentIndex() == 11
    assert not win.due_overview_all_btn.isEnabled()   # nichts zu üben
