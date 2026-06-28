"""Cutover Scheibe 1 — UI-Verdrahtung: Fortschritt + Statistik lesen jetzt aus
dem Positionsmodell (Bäume + ``stats_for_position``), nicht mehr aus ``self.lines``.
Offscreen gegen die echte ``MainWindow``.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import chess  # noqa: E402
from PySide6 import QtWidgets, QtCore  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

PGN_BLACK = """[Event "x"]
[ChapterName "Skandinavisch"]

1. e4 d5 2. exd5 Qxd5 3. Nc3 Qa5 *
"""


def _win(tmp_path, monkeypatch):
    import qt_app.main_window as mw
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    return mw.MainWindow()


def _load_black(win, tmp_path):
    f = tmp_path / "Schwarz Repertoire.pgn"
    f.write_text(PGN_BLACK, encoding="utf-8")
    win._add_pgn_source(str(f))
    win._auto_fill_sides_by_filename()


def _fen_after(ucis):
    b = chess.Board()
    for u in ucis:
        b.push(chess.Move.from_uci(u))
    return b.fen()


def _seed(win, ucis, expected_san, played_san, correct):
    win.stats_store.add_event(
        source_name="s", line_name="l", fen_before=_fen_after(ucis),
        expected_san=expected_san, played_san=played_san, correct=correct)


def test_progress_rows_come_from_trees(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _load_black(win, tmp_path)
    # Treffer an der Schwarz-Stellung nach 1.e4 (vorgesehen: d5)
    _seed(win, ["e2e4"], "d5", "d5", True)
    win._refresh_progress()
    assert win._progress_rows, "Fortschritt sollte den Baum zeigen"
    r = win._progress_rows[0]
    assert "tree" in r and "bucket" in r and "positions_total" in r
    assert r["attempts"] >= 1
    assert r["positions_trained"] >= 1


def test_progress_row_click_starts_tree_drill(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _load_black(win, tmp_path)
    win._refresh_progress()
    tree = win._progress_rows[0]["tree"]
    item = QtWidgets.QListWidgetItem()
    item.setData(QtCore.Qt.UserRole, tree)
    win._train_from_progress(item)
    assert win.stack.currentIndex() == 10        # Baum-Drill, nicht mehr lineares Üben (0)


def test_stats_error_problems_from_positions(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _load_black(win, tmp_path)
    # offener Fehler an der Stellung nach 1.e4: vorgesehen d5, gespielt e5
    _seed(win, ["e2e4"], "d5", "e5", False)
    problems = win._collect_error_problems()
    assert len(problems) == 1
    p = problems[0]
    assert p["expected_san"] == "d5"
    assert p["expected_uci"] == "d7d5"
    assert p["played"] == "e5"
    # ausgebügelt -> verschwindet
    _seed(win, ["e2e4"], "d5", "d5", True)
    assert win._collect_error_problems() == []


# --- »Alle üben« / Schwächen-Sitzung -------------------------------------

def test_drill_all_button_hidden_without_errors(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _load_black(win, tmp_path)
    _seed(win, ["e2e4"], "d5", "d5", True)        # nur Treffer, kein Fehler
    win._refresh_stats()
    assert win.stats_drill_all.isHidden()


def test_drill_all_button_starts_weak_session(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _load_black(win, tmp_path)
    _seed(win, ["e2e4"], "d5", "e5", False)       # offener Fehler
    win._refresh_stats()
    assert not win.stats_drill_all.isHidden()
    assert "1" in win.stats_drill_all.text()
    win.stats_drill_all.click()
    assert win.stack.currentIndex() == 10         # Drill-Seite
    assert win._due_total == 1


def test_weak_session_capped_to_limit(tmp_path, monkeypatch):
    import qt_app.main_window as mw
    monkeypatch.setattr(mw, "WEAK_SESSION_LIMIT", 2)
    win = _win(tmp_path, monkeypatch)
    _load_black(win, tmp_path)
    # Drei offene Fehler an den drei Schwarz-Stellungen der Linie.
    _seed(win, ["e2e4"], "d5", "e5", False)
    _seed(win, ["e2e4", "d7d5", "e4d5"], "Qxd5", "Nf6", False)
    _seed(win, ["e2e4", "d7d5", "e4d5", "d8d5", "b1c3"], "Qa5", "Qd8", False)
    assert len(win._collect_error_problems()) == 3        # alle drei wackeln
    win._start_weak_session()
    assert win._due_total == 2                            # Runde auf 2 gedeckelt
