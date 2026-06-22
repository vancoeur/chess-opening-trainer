"""UX-Bündel 4: Editor — Neuer Baum fragt Seite, Üben-Knopf bei fehlender Seite
deaktiviert, PGN-Export bestätigt."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _win(tmp_path, monkeypatch):
    import qt_app.main_window as mw
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    return mw.MainWindow()


def test_new_tree_asks_for_side(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    monkeypatch.setattr(QtWidgets.QInputDialog, "getText",
                        staticmethod(lambda *a, **k: ("Mein Schwarz-Repertoire", True)))
    # getItem zweiter Eintrag = Schwarz/Black
    monkeypatch.setattr(QtWidgets.QInputDialog, "getItem",
                        staticmethod(lambda *a, **k: (a[3][1], True)))
    win._editor_new_tree()
    assert win.editor_tree.side == "black"


def test_new_tree_cancel_side_aborts(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    before = len(win.tree_store.all())
    monkeypatch.setattr(QtWidgets.QInputDialog, "getText",
                        staticmethod(lambda *a, **k: ("X", True)))
    monkeypatch.setattr(QtWidgets.QInputDialog, "getItem",
                        staticmethod(lambda *a, **k: ("", False)))     # Abbruch
    win._editor_new_tree()
    assert len(win.tree_store.all()) == before                        # kein Baum angelegt


def test_train_button_disabled_without_side(tmp_path, monkeypatch):
    from opening_trainer.repertoire_tree import RepertoireTree
    win = _win(tmp_path, monkeypatch)
    none_tree = RepertoireTree.new("offen", "none")
    win.tree_store.add(none_tree)
    win.editor_tree = none_tree
    win._editor_goto_node(none_tree.root_id)
    assert not win.editor_train_btn.isEnabled()
    assert win.editor_train_btn.toolTip() != ""

    white = RepertoireTree.new("weiss", "white")
    win.tree_store.add(white)
    win.editor_tree = white
    win._editor_goto_node(white.root_id)
    assert win.editor_train_btn.isEnabled()


def test_export_confirms_success(tmp_path, monkeypatch):
    from opening_trainer.repertoire_tree import RepertoireTree
    win = _win(tmp_path, monkeypatch)
    tree = RepertoireTree.new("weiss", "white")
    tree.add_child(tree.root_id, "e2e4")
    win.tree_store.add(tree)
    win.editor_tree = tree
    out = tmp_path / "export.pgn"
    monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (str(out), "")))
    shown = []
    monkeypatch.setattr(QtWidgets.QMessageBox, "information",
                        staticmethod(lambda *a, **k: shown.append(a)))
    win._editor_export()
    assert out.exists() and out.read_text(encoding="utf-8").strip()    # Datei geschrieben
    assert shown                                                       # Erfolg bestätigt
