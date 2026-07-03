"""Phase 5.1 — Sitzungs-Abschluss-Kärtchen.

Wenn die »Heute fällig«-Runde leer läuft, zeigt die Drill-Seite statt einer
nüchternen Statuszeile ein Kärtchen: wie viel auf Anhieb/mit Hilfe/neu gelernt,
eine ehrliche Vorschau und zwei Knöpfe ([Weiter/Schwächen üben] · [Zurück zum
Start]). Zähler pro Runde korrekt.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import chess  # noqa: E402
from PySide6 import QtWidgets  # noqa: E402

from opening_trainer.repertoire_tree import RepertoireTree, BLACK  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _win(tmp_path, monkeypatch):
    import qt_app.main_window as mw
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    return mw.MainWindow()


def _caro_black(win):
    """Ein Schwarz-Repertoire mit EINER eigenen Stellung: nach 1.e4 spielt …c6."""
    tr = RepertoireTree.new("Caro", BLACK)
    nid = tr.add_child(tr.root_id, "e2e4").id
    tr.add_child(nid, "c7c6")
    win.tree_store.add(tr)
    return tr


def test_correct_answer_counts_as_passed_and_shows_card(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _caro_black(win)
    win._drill_learn_new = False                 # direkt abfragen, nicht erst zeigen
    win._start_due_session()
    assert win._due_total == 1
    win._tree_drill_on_move(chess.C7, chess.C6)  # richtiger Zug …c6
    assert win._due_passed == 1 and win._due_wobbled == 0
    assert not win._due_queue                     # Runde leer
    assert (not win.drill_summary.isHidden())          # Kärtchen sichtbar
    assert win.tree_drill_board.isHidden()   # Brett tritt zurück
    assert "1" in win.drill_summary_stats.text()


def test_answer_with_help_counts_as_wobbled(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _caro_black(win)
    win._drill_learn_new = False
    win._start_due_session()
    win._tree_drill_on_move(chess.E7, chess.E5)  # falsch (nicht vorbereitet)
    assert win._due_queue                          # Stellung bleibt
    win._tree_drill_on_move(chess.C7, chess.C6)  # dann richtig
    assert win._due_passed == 0 and win._due_wobbled == 1
    assert (not win.drill_summary.isHidden())


def test_learn_mode_counts_as_learned(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _caro_black(win)
    win._drill_learn_new = True                   # neue Stellung erst zeigen
    win._start_due_session()
    assert win._drill_learn_active                 # Lern-Modus aktiv (neue Stellung)
    win._drill_mark_learned()                      # »Verstanden, weiter«
    assert win._due_learned == 1
    assert (not win.drill_summary.isHidden())
    assert "gelernt" in win.drill_summary_stats.text() or "learn" in win.drill_summary_stats.text().lower()


def test_new_session_hides_the_card(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    tr = _caro_black(win)
    win._drill_learn_new = False
    win._start_due_session()
    win._tree_drill_on_move(chess.C7, chess.C6)
    assert not win.drill_summary.isHidden()        # Kärtchen steht
    win._start_tree_drill(tr)                      # neuer Drill mit Inhalt
    assert win.drill_summary.isHidden()            # Kärtchen weg
    assert not win.tree_drill_board.isHidden()     # Brett wieder da


def test_card_home_button_goes_to_dashboard(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _caro_black(win)
    win._drill_learn_new = False
    win._start_due_session()
    win._tree_drill_on_move(chess.C7, chess.C6)
    win.drill_summary_home.click()
    assert win.stack.currentIndex() == 12          # Startseite/Dashboard


def test_counters_reset_between_sessions(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _caro_black(win)
    win._drill_learn_new = False
    win._start_due_session()
    win._tree_drill_on_move(chess.C7, chess.C6)
    assert win._due_passed == 1
    win._start_due_session()                       # frische Runde -> Zähler 0
    assert win._due_passed == 0 and win._due_wobbled == 0 and win._due_learned == 0
