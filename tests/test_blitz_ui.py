"""Blitz-Sprint — UI-Verdrahtung gegen die echte MainWindow (offscreen).
Ohne echtes Warten: der Zeit-Tick/-Ablauf wird direkt aufgerufen. Geprüft wird
vor allem: Punkte zählen, Lernplan + Statistik bleiben UNBERÜHRT, Zeitablauf
sperrt das Brett, Seitenwechsel stoppt die Uhr."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import chess  # noqa: E402
from PySide6 import QtWidgets  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _win(tmp_path, monkeypatch):
    import qt_app.main_window as mw
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    return mw.MainWindow()


def _black_caro(win):
    """1.e4 c6 2.d4 d5 — zwei eigene Schwarz-Stellungen."""
    from opening_trainer.repertoire_tree import RepertoireTree
    tr = RepertoireTree.new("Caro", "black")
    p = tr.root_id
    for u in ["e2e4", "c7c6", "d2d4", "d7d5"]:
        p = tr.add_child(p, u).id
    win.tree_store.add(tr)
    return tr


def _play_correct(win):
    """Spielt den vorgesehenen Zug der aktuell gezeigten Blitz-Stellung."""
    tr = win._tree_trainer
    sol = tr.expected_solution()
    m = chess.Move.from_uci(sol.uci)
    win._tree_drill_on_move(m.from_square, m.to_square)


def test_blitz_start_sets_up_session(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _black_caro(win)
    win._start_blitz_session()
    assert win._blitz is True
    assert win.stack.currentIndex() == 10
    assert not win.blitz_bar.isHidden()
    assert win._blitz_score == 0
    assert win._tree_trainer is not None          # eine Stellung steht bereit
    assert "0" in win.blitz_score_label.text()
    win._blitz_stop()                             # Timer wieder anhalten


def test_blitz_correct_scores_without_touching_schedule(tmp_path, monkeypatch):
    from opening_trainer.scheduler import is_new
    win = _win(tmp_path, monkeypatch)
    _black_caro(win)
    win._start_blitz_session()
    epd = win._tree_trainer.board.epd()
    _play_correct(win)
    assert win._blitz_score == 1                  # Treffer gezählt
    # Lernplan unberührt: die Karte ist weiterhin »neu«.
    assert is_new(win.position_schedule.card_for(epd))
    # Statistik unberührt: kein Ereignis geschrieben.
    assert win.stats_store.events == []
    win._blitz_stop()


def test_blitz_timeout_locks_board(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _black_caro(win)
    win._start_blitz_session()
    win._blitz_remaining = 1
    win._blitz_tick()                             # 1 -> 0 -> Ablauf
    assert win._blitz_over is True
    low = win.tree_drill_status.text().lower()
    assert "zeit" in low or "time" in low
    # Nach Ablauf werden Züge ignoriert (kein Absturz, kein Punkt).
    before = win._blitz_score
    win._tree_drill_on_move(chess.E7, chess.E5)
    assert win._blitz_score == before


def test_blitz_pool_refills_when_empty(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _black_caro(win)
    win._start_blitz_session()
    win._due_queue = []                           # Vorrat künstlich leeren
    win._blitz_present_current()                  # muss neu mischen, nicht abbrechen
    assert win._tree_trainer is not None
    assert len(win._due_queue) >= 1
    win._blitz_stop()


def test_show_solution_marks_board_after_timeout(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _black_caro(win)
    win._start_blitz_session()
    win._blitz_remaining = 1
    win._blitz_tick()                             # Zeit abgelaufen
    assert win._blitz_over is True
    assert win._tree_trainer is not None          # Trainer bleibt für »Lösung zeigen«
    win._tree_drill_solution()                    # Knopf »Lösung zeigen«
    assert win.tree_drill_board.solution_squares is not None   # Zug ist farbig markiert
    win._blitz_stop()


def test_idea_text_has_no_raw_markup(tmp_path, monkeypatch):
    from opening_trainer.repertoire_tree import RepertoireTree
    win = _win(tmp_path, monkeypatch)
    tr = RepertoireTree.new("Caro", "black")
    n1 = tr.add_child(tr.root_id, "e2e4").id
    # Schwarz-Zug mit Lichess-Pfeil-Markup als Kommentar:
    tr.add_child(n1, "c7c6", comment="[%csl Ga5][%cal Gc6a5]")
    win.tree_store.add(tr)
    win._start_blitz_session()
    # Es muss die Caro-Stellung sein (nur eine eigene Stellung im Baum).
    txt = win.tree_drill_note.text()
    assert "[%" not in txt                        # kein roher Code mehr
    win._blitz_stop()


def test_leaving_page_stops_blitz(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _black_caro(win)
    win._start_blitz_session()
    assert win._blitz_timer.isActive()
    win._open_home()                              # Seitenwechsel -> Blitz beenden
    assert win._blitz is False
    assert not win._blitz_timer.isActive()
    assert win.home_blitz.isHidden() is False     # Blitz-Karte auf der Startseite sichtbar
