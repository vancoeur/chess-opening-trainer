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


def test_tree_report_lines_after_load(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _load_two_caro(win)
    lines = win._tree_report_lines()
    assert len(lines) == 1                                  # nur Schwarz hat Linien
    text = lines[0]
    assert ("Schwarz" in text or "Black" in text)
    assert ("Verzweigung" in text or "branch" in text)      # die zwei Linien verzweigen


def _families(win):
    return [win.reptree_family_combo.itemText(i) for i in range(win.reptree_family_combo.count())]


def test_family_selector_lists_repertoires(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    win.tree_store.add(_black("B18 · Caro-Kann: Klassisch", ["e2e4", "c7c6", "d2d4", "d7d5"]))
    win.tree_store.add(_black("C65 · Ruy López: Berliner", ["e2e4", "e7e5", "g1f3", "b8c6"]))
    win._open_repertoire_tree()
    fams = _families(win)
    assert fams[0] in ("Alles", "All")            # erste Option = alles
    assert "Caro-Kann" in fams and "Ruy López" in fams


def test_family_selection_filters_tree_and_trains(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    win.tree_store.add(_black("B18 · Caro-Kann: Klassisch", ["e2e4", "c7c6", "d2d4", "d7d5"]))
    win.tree_store.add(_black("C65 · Ruy López: Berliner", ["e2e4", "e7e5", "g1f3", "b8c6"]))
    win._open_repertoire_tree()
    # Caro-Kann wählen -> nur diese Linie im Baum (keine Ruy-Züge)
    idx = next(i for i in range(win.reptree_family_combo.count())
               if win.reptree_family_combo.itemData(i) == "Caro-Kann")
    win.reptree_family_combo.setCurrentIndex(idx)
    texts = " ".join(win.reptree_list.item(i).text() for i in range(win.reptree_list.count()))
    assert "c6" in texts and "e5" not in texts
    # dieses Repertoire üben -> Stellungs-Sitzung
    win._reptree_train()
    assert win.stack.currentIndex() == 10


def test_window_title_reflects_page(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    win.stack.setCurrentIndex(13)
    assert "Repertoire-Baum" in win.windowTitle() or "Repertoire tree" in win.windowTitle()
    win.stack.setCurrentIndex(11)
    assert "Heute fällig" in win.windowTitle() or "Due today" in win.windowTitle()


def test_empty_side_shows_hint(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _load_two_caro(win)
    win._open_repertoire_tree()
    win.reptree_side_combo.setCurrentIndex(0)                   # Weiß: kein Repertoire
    assert win.reptree_list.count() == 0
    assert "kein Repertoire" in win.reptree_hint.text() or "No repertoire" in win.reptree_hint.text()
