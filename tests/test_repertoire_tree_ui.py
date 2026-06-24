"""Repertoire-Baum-Seite (Stack 13): viele Linien einer Seite als EIN
verzweigter, eingerückter Baum; Klick zeigt die Stellung, eigene Züge drillbar.
Offscreen gegen die echte ``MainWindow``.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets, QtCore  # noqa: E402

from opening_trainer.repertoire_tree import RepertoireTree, BLACK  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _win(tmp_path, monkeypatch):
    import qt_app.main_window as mw
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    return mw.MainWindow()


def _black(name, ucis):
    t = RepertoireTree.new(name, BLACK)
    p = t.root_id
    for u in ucis:
        p = t.add_child(p, u).id
    return t


def _load_two_caro(win):
    win.tree_store.add(_black("Advance", ["e2e4", "c7c6", "d2d4", "d7d5", "e4e5", "c8f5"]))
    win.tree_store.add(_black("Klassisch", ["e2e4", "c7c6", "d2d4", "d7d5", "b1c3", "d5e4"]))


def test_page_merges_and_lists(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _load_two_caro(win)
    win._open_repertoire_tree()
    assert win.stack.currentIndex() == 13
    assert win.reptree_side_combo.currentData() == "black"      # Seite mit Repertoire
    assert win.reptree_list.count() > 0
    # eine Verzweigung ist vorhanden (markiert mit ⎇)
    texts = [win.reptree_list.item(i).text() for i in range(win.reptree_list.count())]
    assert any("⎇" in tx for tx in texts)


def test_click_user_move_enables_drill_and_drills(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _load_two_caro(win)
    win._open_repertoire_tree()
    idx = next(i for i in range(win.reptree_list.count())
               if win.reptree_list.item(i).data(QtCore.Qt.UserRole)["is_user_move"])
    item = win.reptree_list.item(idx)
    win._reptree_clicked(item)
    assert win.reptree_drill_btn.isEnabled() is True
    win._reptree_drill()
    assert win.stack.currentIndex() == 10                       # Stellungs-Drill


def test_opponent_move_not_drillable(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _load_two_caro(win)
    win._open_repertoire_tree()
    idx = next(i for i in range(win.reptree_list.count())
               if not win.reptree_list.item(i).data(QtCore.Qt.UserRole)["is_user_move"])
    win._reptree_clicked(win.reptree_list.item(idx))
    assert win.reptree_drill_btn.isEnabled() is False           # Weiß-Zug: nichts zu üben


def test_empty_side_shows_hint(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _load_two_caro(win)
    win._open_repertoire_tree()
    win.reptree_side_combo.setCurrentIndex(0)                   # Weiß: kein Repertoire
    assert win.reptree_list.count() == 0
    assert "kein Repertoire" in win.reptree_hint.text() or "No repertoire" in win.reptree_hint.text()
