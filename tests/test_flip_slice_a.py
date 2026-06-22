"""Slice A end-to-end (offscreen): nach normalem PGN-Laden ist die positions-basierte
Tagessitzung (⌘D) NICHT mehr leer — der zentrale Fund #0/#2 des UX-Red-Teams."""
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
    return mw.MainWindow()


def test_loading_pgn_makes_due_session_nonempty(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    f = tmp_path / "Schwarz Repertoire.pgn"          # Dateiname -> Auto-Zuordnung Schwarz
    f.write_text(PGN_BLACK, encoding="utf-8")

    win._add_pgn_source(str(f))
    win._auto_fill_sides_by_filename()               # setzt Schwarz + re-synct die Auto-Bäume

    # Auto-Bäume sind entstanden und Schwarz zugeordnet
    auto = [t for t in win.tree_store.all() if t.headers.get("_auto") == "1"]
    assert len(auto) == 2
    assert all(t.side == "black" for t in auto)

    # ⌘D ist jetzt befüllt (vorher immer leer für normal geladene Repertoires)
    win._start_due_session()
    assert win._due_total > 0
    assert win.stack.currentIndex() == 10


def test_loading_is_idempotent_no_duplicate_trees(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    f = tmp_path / "Schwarz Repertoire.pgn"
    f.write_text(PGN_BLACK, encoding="utf-8")
    win._add_pgn_source(str(f))
    win._auto_fill_sides_by_filename()
    n1 = len([t for t in win.tree_store.all() if t.headers.get("_auto") == "1"])
    # erneut laden derselben Quelle -> keine Duplikate
    win._add_pgn_source(str(f))
    win._auto_fill_sides_by_filename()
    n2 = len([t for t in win.tree_store.all() if t.headers.get("_auto") == "1"])
    assert n1 == n2 == 2


def test_editor_tree_survives_load(tmp_path, monkeypatch):
    from opening_trainer.repertoire_tree import RepertoireTree
    win = _win(tmp_path, monkeypatch)
    # ein echter Editor-Baum (ohne _auto, eigene Linie)
    ed = RepertoireTree.new("Mein Londoner System", "white")
    nid = ed.root_id
    for u in ["d2d4", "d7d5", "c1f4"]:
        nid = ed.add_child(nid, u).id
    win.tree_store.add(ed)
    win.tree_store.save(win.trees_path)

    f = tmp_path / "Schwarz Repertoire.pgn"
    f.write_text(PGN_BLACK, encoding="utf-8")
    win._add_pgn_source(str(f))
    win._auto_fill_sides_by_filename()

    assert "Mein Londoner System" in {t.name for t in win.tree_store.all()}
