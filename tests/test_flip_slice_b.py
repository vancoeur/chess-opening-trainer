"""Slice B: ein einziger Lade-Eintrag; Bearbeiten eines Auto-Baums macht ihn dauerhaft."""
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


def test_no_separate_import_as_trees_path(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    # Der separate „als Bäume importieren"-Weg ist entfernt (Methode + Menü-Verdrahtung).
    assert not hasattr(win, "_import_pgn_as_trees")
    # Der normale Lade-Weg deckt es ab (erzeugt selbst varianten-erhaltende Auto-Bäume).
    assert hasattr(win, "_load_pgn_dialog") and hasattr(win, "_sync_auto_trees")


def test_editing_auto_tree_makes_it_permanent(tmp_path, monkeypatch):
    from opening_trainer.repertoire_tree import RepertoireTree
    win = _win(tmp_path, monkeypatch)
    auto = RepertoireTree.new("Auto Skandi", "black")
    auto.headers["_auto"] = "1"
    auto.headers["_source"] = "Schwarz.pgn"
    nid = auto.add_child(auto.root_id, "e2e4").id
    win.tree_store.add(auto)
    win.editor_tree = auto
    win._editor_goto_node(nid)                       # auf eine Stellung (Schwarz am Zug)

    # einen Zug anhängen -> Baum wird dauerhaft (Marke weg)
    import chess
    b = chess.Board(); b.push_uci("e2e4")
    mv = chess.Move.from_uci("d7d5")
    win._editor_on_move(mv.from_square, mv.to_square)

    assert auto.headers.get("_auto") is None          # nicht mehr Auto -> Sync lässt ihn in Ruhe
    assert "_source" not in auto.headers
