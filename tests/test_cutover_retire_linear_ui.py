"""Cutover Scheibe 4 — UI: alle „üben/trainieren"-Eintrittspunkte führen jetzt
ins Positionsmodell (Baum-Drill / Tagessitzung, Stack 10), nicht mehr ins
lineare Training (Stack 0). Offscreen gegen die echte ``MainWindow``.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import chess  # noqa: E402
from PySide6 import QtWidgets, QtCore  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

REP_PGN = """[Event "x"]
[White "Rep"]

1. e4 e5 2. Nf3 Nc6 3. Bc4 *
"""


def _win(tmp_path, monkeypatch):
    import qt_app.main_window as mw
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    return mw.MainWindow()


def _load_white(win, tmp_path):
    f = tmp_path / "Weiss Repertoire.pgn"
    f.write_text(REP_PGN, encoding="utf-8")
    win._add_pgn_source(str(f))
    win._auto_fill_sides_by_filename()


def _white_line(win):
    return next(l for l in win.lines if win._side_of_line(l) == "white" and l.moves_uci)


def _fen_after(ucis):
    b = chess.Board()
    for u in ucis:
        b.push(chess.Move.from_uci(u))
    return b.fen()


def test_library_click_starts_tree_drill(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _load_white(win, tmp_path)
    item = QtWidgets.QListWidgetItem()
    item.setData(QtCore.Qt.UserRole, _white_line(win))
    win._train_from_library(item)
    assert win.stack.currentIndex() == 10


def test_train_side_starts_due_session(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _load_white(win, tmp_path)
    win._side_filter = "white"
    win._train_side()
    assert win.stack.currentIndex() == 10
    assert win._due_session is True


def test_stats_error_click_drills_position(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _load_white(win, tmp_path)
    # offener Fehler an der Weiß-Stellung nach 1.e4 e5 (vorgesehen Nf3, gespielt Bc4)
    win.stats_store.add_event(source_name="s", line_name="l",
                              fen_before=_fen_after(["e2e4", "e7e5"]),
                              expected_san="Nf3", played_san="Bc4", correct=False)
    problem = win._collect_error_problems()[0]
    item = QtWidgets.QListWidgetItem()
    item.setData(QtCore.Qt.UserRole, problem)
    win._drill_one_from_item(item)
    assert win.stack.currentIndex() == 10


def test_viewer_train_drills_position(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _load_white(win, tmp_path)
    win._viewer_drill_fen = _fen_after(["e2e4", "e7e5"])   # Stellung im Repertoire
    win._viewer_train()
    assert win.stack.currentIndex() == 10


def test_no_due_no_crash_for_side(tmp_path, monkeypatch):
    # Seite ohne Bäume -> Tagessitzung leer, kein Absturz, landet auf Drill-Seite.
    win = _win(tmp_path, monkeypatch)
    _load_white(win, tmp_path)
    win._side_filter = "black"
    win._train_side()
    assert win.stack.currentIndex() == 10
