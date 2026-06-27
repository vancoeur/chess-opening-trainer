"""Aufräumen verwaister/eigener Bäume: »Repertoire leeren« entfernt jetzt ALLE
Bäume, und die Liste der »eigenen Bäume« zeigt die Nicht-Auto-Bäume. Offscreen.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets  # noqa: E402

from opening_trainer.repertoire_tree import RepertoireTree, BLACK  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _win(tmp_path, monkeypatch):
    import qt_app.main_window as mw
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    return mw.MainWindow()


def _tree(name, auto, ucis=("e2e4", "c7c6")):
    t = RepertoireTree.new(name, BLACK)
    p = t.root_id
    for u in ucis:
        p = t.add_child(p, u).id
    if auto:
        t.headers["_auto"] = "1"
    return t


def test_custom_trees_lists_only_non_auto(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    win.tree_store.add(_tree("auto", auto=True))
    win.tree_store.add(_tree("ghost", auto=False))
    customs = win._custom_trees()
    assert len(customs) == 1
    assert customs[0].name == "ghost"


def test_clear_repertoire_removes_all_trees(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    win.tree_store.add(_tree("auto", auto=True))
    win.tree_store.add(_tree("ghost", auto=False))
    # „Ja" auf die Sicherheitsabfrage
    monkeypatch.setattr(QtWidgets.QMessageBox, "question",
                        lambda *a, **k: QtWidgets.QMessageBox.StandardButton.Yes)
    win._reset_repertoire()
    assert win.tree_store.all() == []           # auch die Geister sind weg
    assert win._catalog() == []
