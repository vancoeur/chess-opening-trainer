"""Regression: Klick auf einen Zug weit unten in der Editor-Zugliste darf die
Ansicht NICHT auf den Anfang zurückspringen lassen. _editor_render_list baut die
Liste neu auf; danach muss der gewählte Zug das currentItem und sichtbar sein.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtWidgets  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

# B01 · Skandinavisch, 16 Halbzüge (wie im Fehlerbericht des Nutzers)
LINE = [
    "e2e4", "d7d5", "e4d5", "d8d5", "b1c3", "d5a5", "d2d4", "g8f6",
    "g1f3", "c7c6", "f1c4", "c8f5", "f3e5", "e7e6", "e1g1", "f8e7",
]


def _win(tmp_path, monkeypatch):
    import qt_app.main_window as mw
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    return mw.MainWindow()


def _long_tree():
    from opening_trainer.repertoire_tree import RepertoireTree
    t = RepertoireTree.new("B01 · Scandinavian", "black")
    nid = t.root_id
    last = nid
    for u in LINE:
        last = t.add_child(last, u).id
    return t, last


def test_clicking_a_late_move_keeps_it_selected_and_in_view(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    tree, last_node = _long_tree()
    win.tree_store.add(tree)
    win.editor_tree = tree

    win._editor_goto_node(last_node)            # auf den letzten (späten) Zug springen

    lw = win.editor_list
    assert lw.count() == len(LINE)              # ganze Linie gelistet
    cur = lw.currentItem()
    assert cur is not None
    assert cur.data(QtCore.Qt.UserRole) == last_node   # gewählter Zug bleibt aktiv
    assert lw.currentRow() == len(LINE) - 1            # die letzte Zeile …
    assert lw.currentRow() > 0                          # … und NICHT zurück auf Zeile 0


def test_clicking_via_handler_does_not_jump_to_top(tmp_path, monkeypatch):
    """Über den echten Klick-Handler (wie beim Mausklick) bleibt der Zug gewählt."""
    win = _win(tmp_path, monkeypatch)
    tree, last_node = _long_tree()
    win.tree_store.add(tree)
    win.editor_tree = tree
    win._editor_goto_node(tree.root_id)         # erst an den Anfang

    # das Listen-Element des letzten Zuges finden und den Klick-Handler aufrufen
    lw = win.editor_list
    target = next(lw.item(i) for i in range(lw.count())
                  if lw.item(i).data(QtCore.Qt.UserRole) == last_node)
    win._editor_list_clicked(target)

    assert lw.currentItem().data(QtCore.Qt.UserRole) == last_node
    assert lw.currentRow() > 0
