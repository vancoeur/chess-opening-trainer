"""Lade-/Auswahl-Robustheit (Red-Team-Folge): keine Dubletten aus überlappenden
Quellen, Lehr-/Puzzle-Material nicht als Repertoire-Familie, verwaiste Seiten-
Zuordnungen beim Entfernen einer Quelle aufräumen. Offscreen gegen die echte
MainWindow; schreibt nur in einen Wegwerf-Datenordner."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets  # noqa: E402

from opening_trainer.repertoire_tree import RepertoireTree, BLACK  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

WHITE_PGN = '[Event "x"]\n[ChapterName "Italienisch"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 *\n'


def _win(tmp_path, monkeypatch):
    import qt_app.main_window as mw
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    monkeypatch.setattr(QtWidgets.QMessageBox, "information", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QtWidgets.QMessageBox, "warning", staticmethod(lambda *a, **k: None))
    return mw.MainWindow()


def _sources_of(k):
    return k.split("\t", 1)[0]


# --- F5: Datei im schon geladenen Ordner nicht doppelt aufnehmen ---------------

def test_file_inside_loaded_folder_not_added_twice(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    folder = tmp_path / "rep"; folder.mkdir()
    (folder / "Weiss.pgn").write_text(WHITE_PGN, encoding="utf-8")
    win._add_pgn_source(str(folder))
    win._add_pgn_source(str(folder / "Weiss.pgn"))     # dieselbe Datei, jetzt einzeln
    assert str(folder / "Weiss.pgn") not in win._effective_sources()   # nicht als 2. Quelle
    assert [e.name for e in win._catalog()].count("Italienisch") == 1  # keine Dublette


def test_new_folder_replaces_contained_file_source(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    folder = tmp_path / "rep"; folder.mkdir()
    (folder / "Weiss.pgn").write_text(WHITE_PGN, encoding="utf-8")
    win._add_pgn_source(str(folder / "Weiss.pgn"))     # erst die Datei
    win._add_pgn_source(str(folder))                   # dann der Ordner -> ersetzt die Datei-Quelle
    srcs = win._effective_sources()
    assert str(folder) in srcs and str(folder / "Weiss.pgn") not in srcs
    assert [e.name for e in win._catalog()].count("Italienisch") == 1


# --- F4: Quelle entfernen räumt verwaiste Seiten-Zuordnungen auf ---------------

def test_removing_source_prunes_orphan_sides(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    folder = tmp_path / "rep"; folder.mkdir()
    (folder / "Weiss.pgn").write_text(WHITE_PGN, encoding="utf-8")
    win._add_pgn_source(str(folder))
    win._auto_fill_sides_by_filename()
    assert any(_sources_of(k) == "Weiss.pgn" for k in win.opening_sides.sides)
    win._remove_pgn_source(str(folder))
    assert not any(_sources_of(k) == "Weiss.pgn" for k in win.opening_sides.sides)


# --- F3: Lehr-/Puzzle-Material nicht als Repertoire-Familie ---------------------

def _black(name, ucis):
    t = RepertoireTree.new(name, BLACK)
    p = t.root_id
    for u in ucis:
        p = t.add_child(p, u).id
    return t


def test_instructional_tree_not_a_family(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    win.tree_store.add(_black("Tactical Theme - Game Puzzle #1", ["e2e4", "e7e5", "g1f3", "b8c6"]))
    win.tree_store.add(_black("Caro", ["e2e4", "c7c6", "d2d4", "d7d5"]))
    caro = next(t for t in win.tree_store.by_side("black") if t.name == "Caro")
    caro_fam = win._tree_family(caro)
    # NUR die echte Eröffnung ist eine Familie — das Puzzle steuert keine bei
    assert win._reptree_families("black") == [caro_fam]
