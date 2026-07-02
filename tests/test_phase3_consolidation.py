"""Phase 3: die verstreuten »Üben«-Knöpfe eingesammelt.

Die Bibliothek hat keine eigenen Üben-Knöpfe mehr — ein »Im Repertoire-Baum
öffnen«-Knopf routet die markierte Eröffnung in den Baum (den einen Übe-Ort,
wo der anpassbare Üben-Knopf sitzt). Der Fehler-Knopf heißt jetzt wie im
Dashboard »Schwächen üben«.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets, QtCore  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

PGN_BLACK = """[Event "x"]
[ChapterName "Caro-Kann"]

1. e4 c6 2. d4 d5 3. Nc3 dxe4 *
"""


def _win(tmp_path, monkeypatch):
    import qt_app.main_window as mw
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    return mw.MainWindow()


def _load_caro_black(win, tmp_path):
    f = tmp_path / "Schwarz Caro.pgn"
    f.write_text(PGN_BLACK, encoding="utf-8")
    win._add_pgn_source(str(f))
    win._auto_fill_sides_by_filename()


def _select_first_line(win):
    win._open_library()
    for i in range(win.library_list.count()):
        it = win.library_list.item(i)
        data = it.data(QtCore.Qt.UserRole)
        if data is not None and getattr(data, "moves_uci", None):
            win.library_list.setCurrentItem(it)
            return it
    return None


def test_library_has_no_standalone_train_buttons(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    # die zwei alten Bibliotheks-Üben-Knöpfe sind ersatzlos weg
    assert not hasattr(win, "train_side_btn")
    assert not hasattr(win, "train_one_btn")


def test_open_in_tree_button_routes_to_repertoire_tree(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _load_caro_black(win, tmp_path)
    it = _select_first_line(win)
    assert it is not None
    assert win.reptree_open_btn.isEnabled()          # bei Auswahl aktiv
    win.reptree_open_btn.click()
    assert win.stack.currentIndex() == 13            # im Repertoire-Baum gelandet
    assert win.reptree_side_combo.currentData() == "black"        # richtige Seite
    assert win.reptree_family_combo.currentData() == "Caro-Kann"  # Eröffnung vorgewählt


def test_open_in_tree_button_disabled_without_selection(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _load_caro_black(win, tmp_path)
    win._open_library()
    win.library_list.clearSelection()
    assert not win.reptree_open_btn.isEnabled()      # nichts markiert -> aus


def test_stats_button_named_weak_spots(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    txt = win.stats_drill_all.text()
    assert "Schwächen" in txt or "weak" in txt.lower()   # gleicher Name wie im Dashboard
