"""Beim Laden eines Repertoires wird die Spielerfarbe automatisch zugeordnet,
sodass die Übersicht sofort »Weiß ▸ 1.e4« / »Schwarz ▸ gegen 1.e4« gruppiert.
"""
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

WHITE_PGN = """[Event "W1"]
[ChapterName "Italienisch"]

1. e4 e5 2. Nf3 Nc6 3. Bc4 *

[Event "W2"]
[ChapterName "Damengambit"]

1. d4 d5 2. c4 e6 *
"""


def _win(tmp_path, monkeypatch):
    import qt_app.main_window as mw
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    return mw.MainWindow()


def test_single_file_load_asks_and_assigns_chosen_side(tmp_path, monkeypatch):
    import qt_app.main_window as mw
    f = tmp_path / "Weissrepertoire.pgn"
    f.write_text(WHITE_PGN, encoding="utf-8")
    win = _win(tmp_path, monkeypatch)
    # Dialog beantwortet "Weiß" (erster Eintrag) mit ok=True
    monkeypatch.setattr(
        QtWidgets.QInputDialog, "getItem",
        staticmethod(lambda *a, **k: (a[3][0], True)),  # a[3] = items-Liste
    )
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getOpenFileName",
        staticmethod(lambda *a, **k: (str(f), "")),
    )
    win._load_pgn_dialog()
    # beide Eröffnungen der Datei sind jetzt Weiß
    for line in win.lines:
        assert win._side_of_line(line) == "white"
    # nach erstem Zug gruppiert, KEINE "Ohne Zuordnung"/"Unassigned"-Gruppe mehr
    assert {win._first_move_label(l) for l in win.lines} == {"1.e4", "1.d4"}
    for line in win.lines:
        g = win._group_label(line)
        assert "Ohne Zuordnung" not in g and "Unassigned" not in g
        assert g.endswith(win._first_move_label(line))   # endet auf 1.e4 / 1.d4


def test_assign_does_not_overwrite_existing(tmp_path, monkeypatch):
    f = tmp_path / "Repertoire.pgn"
    f.write_text(WHITE_PGN, encoding="utf-8")
    win = _win(tmp_path, monkeypatch)
    from opening_trainer.pgn_loader import load_pgn_file
    win.lines = load_pgn_file(f)
    # erste Linie schon als Schwarz markiert (manuell)
    first = win.lines[0]
    win.opening_sides.set_side(first.source_name, first.name, "black")
    n = win._assign_side_for_file("Repertoire.pgn", "white")
    assert n == 1                                   # nur die noch offene Linie
    assert win._side_of_line(first) == "black"      # bestehende bleibt


def test_folder_autofill_from_filename(tmp_path, monkeypatch):
    folder = tmp_path / "rep"
    folder.mkdir()
    (folder / "Weiss London.pgn").write_text(WHITE_PGN, encoding="utf-8")
    (folder / "Schwarz Pirc.pgn").write_text(
        '[Event "B"]\n[ChapterName "Pirc"]\n\n1. e4 d6 2. d4 Nf6 *\n', encoding="utf-8")
    win = _win(tmp_path, monkeypatch)
    from opening_trainer.pgn_loader import load_pgn_folder
    win.lines = load_pgn_folder(folder)
    n = win._auto_fill_sides_by_filename()
    assert n == 3
    for line in win.lines:
        want = "white" if "Weiss" in line.source_name else "black"
        assert win._side_of_line(line) == want


def test_ambiguous_filename_is_left_unassigned(tmp_path, monkeypatch):
    folder = tmp_path / "rep"
    folder.mkdir()
    (folder / "Repertoire.pgn").write_text(WHITE_PGN, encoding="utf-8")
    win = _win(tmp_path, monkeypatch)
    from opening_trainer.pgn_loader import load_pgn_folder
    win.lines = load_pgn_folder(folder)
    assert win._auto_fill_sides_by_filename() == 0     # nicht raten
    assert all(win._side_of_line(l) is None for l in win.lines)
