"""Cutover Scheibe 5a: Editor-eigene Bäume (ohne PGN-Linien-Pendant) erscheinen
jetzt in der Bibliothek als eigene Sektion, sind drillbar, und die Seiten-
Zuordnung (für Linien) bleibt bei ihnen deaktiviert. Offscreen.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets, QtCore  # noqa: E402

from opening_trainer.repertoire_tree import RepertoireTree, WHITE  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _win(tmp_path, monkeypatch):
    import qt_app.main_window as mw
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    return mw.MainWindow()


def _editor_tree(win, name="Meine Idee", side="white"):
    t = RepertoireTree.new(name, side)
    t.add_child(t.root_id, "e2e4")        # ein eigener Zug -> drillbar
    win.tree_store.add(t)                  # kein _auto-Header -> Editor-Baum
    return t


def _tree_items(win):
    return [win.library_list.item(i) for i in range(win.library_list.count())
            if win._is_tree_item(win.library_list.item(i).data(QtCore.Qt.UserRole))]


def test_editor_tree_appears_in_library(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    win._side_filter = None
    win.search_query = ""
    t = _editor_tree(win)
    win._refresh_library()
    datas = [it.data(QtCore.Qt.UserRole) for it in _tree_items(win)]
    assert t in datas
    assert not win.library_empty.isVisible()      # nicht „leer", obwohl keine Linien


def test_editor_tree_click_starts_drill(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    win._side_filter = None
    win.search_query = ""
    _editor_tree(win)
    win._refresh_library()
    item = _tree_items(win)[0]
    win._train_from_library(item)
    assert win.stack.currentIndex() == 10


def test_editor_tree_row_blocks_side_assignment(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    win._side_filter = None
    win.search_query = ""
    _editor_tree(win)
    win._refresh_library()
    item = _tree_items(win)[0]
    win.library_list.setCurrentItem(item)
    win._on_library_selection()
    assert win.assign_white_btn.isEnabled() is False    # Zuordnung nur für Linien
    assert win.train_one_btn.isEnabled() is True        # üben geht
    assert win._selected_library_line() is None         # zählt nicht als Linie


def test_editor_tree_respects_side_filter(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    win.search_query = ""
    _editor_tree(win, side="white")
    win._side_filter = "black"
    win._refresh_library()
    assert _tree_items(win) == []                       # Weiß-Baum nicht im Schwarz-Tab
    win._side_filter = "white"
    win._refresh_library()
    assert len(_tree_items(win)) == 1
