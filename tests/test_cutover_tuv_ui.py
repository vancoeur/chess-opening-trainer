"""Cutover Scheibe 3 — UI: die Repertoire-Prüfung bildet Prüf-Jobs aus den
Baum-Varianten (nicht aus self.lines), und ein Klick auf einen Fund startet den
Baum-Drill. Offscreen gegen die echte ``MainWindow`` (ohne Stockfish-Lauf).
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import chess  # noqa: E402
from PySide6 import QtWidgets, QtCore  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

# Weiß-Repertoire mit Variante: nach 1.e4 e5 zwei vorgesehene Züge.
REP_PGN = """[Event "x"]
[White "Rep"]

1. e4 e5 2. Nf3 (2. Bc4 Bc5) 2... Nc6 *
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


def test_tuv_jobs_come_from_tree_variations(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _load_white(win, tmp_path)
    jobs = win._tuv_jobs()
    assert len(jobs) == 2                         # zwei Varianten, nicht eine Hauptlinie
    holder, color = jobs[0]
    assert color == chess.WHITE
    assert holder.tree.id in win.tree_store.trees
    assert holder.moves_uci                       # vollständiger Pfad


def test_tuv_click_starts_tree_drill(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _load_white(win, tmp_path)
    holder = win._tuv_jobs()[0][0]
    item = QtWidgets.QListWidgetItem()
    item.setData(QtCore.Qt.UserRole, holder)
    win._train_from_tuv(item)
    assert win.stack.currentIndex() == 10         # Baum-Drill, nicht lineares Üben (0)


def test_tuv_jobs_empty_without_assigned_side(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    f = tmp_path / "Repertoire.pgn"               # Name ohne Farb-Hinweis -> keine Seite
    f.write_text(REP_PGN, encoding="utf-8")
    win._add_pgn_source(str(f))
    assert win._tuv_jobs() == []
