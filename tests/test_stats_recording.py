"""A1-Regression: die Statistik protokolliert den TATSÄCHLICH gespielten Fehlzug
(nicht den richtigen), und die Gesamt-Trefferquote zählt keine Züge aus gelöschten
Bäumen mehr. Offscreen gegen die echte MainWindow."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import chess  # noqa: E402
from PySide6 import QtWidgets  # noqa: E402

from opening_trainer.repertoire_tree import RepertoireTree, WHITE, BLACK  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _win(tmp_path, monkeypatch):
    import qt_app.main_window as mw
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    return mw.MainWindow()


def _tree(name, side, ucis):
    t = RepertoireTree.new(name, side)
    p = t.root_id
    for u in ucis:
        p = t.add_child(p, u).id
    return t


def test_wrong_then_correct_records_the_actual_wrong_move(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    tree = _tree("Italienisch", WHITE, ["e2e4", "e7e5", "g1f3"])
    win.tree_store.add(tree)
    win._drill_learn_new = False
    win._start_tree_drill(tree)
    tr = win._tree_trainer
    sol = tr.expected_solution()                       # erwartet: e4
    wrong = next(m for m in tr.board.legal_moves if m.uci() != sol.uci)
    wrong_san = tr.board.san(wrong)
    win._tree_drill_on_move(wrong.from_square, wrong.to_square)   # falsch spielen
    assert win._tree_drill_wrong is True
    e = sol.uci
    win._tree_drill_on_move(chess.parse_square(e[:2]), chess.parse_square(e[2:4]))  # dann richtig
    ev = win.stats_store.events[-1]
    assert ev.correct is False
    assert ev.expected_san == sol.san
    assert ev.played_san == wrong_san                  # der ECHTE Fehlzug, nicht der richtige
    assert ev.played_san != ev.expected_san


def test_overall_accuracy_drops_deleted_tree_events(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    tree = _tree("Caro", BLACK, ["e2e4", "c7c6", "d2d4", "d7d5"])
    win.tree_store.add(tree)
    b = chess.Board(); b.push(chess.Move.from_uci("e2e4"))
    win.stats_store.add_event(source_name="", line_name="Caro", fen_before=b.fen(),
                              expected_san="c6", played_san="c6", correct=True)
    win._refresh_stats()
    assert win.stats_empty.isHidden()                  # gültige Daten -> Leer-Hinweis aus
    win.tree_store.remove(tree.id)                     # Baum weg -> Event ist verwaist
    win._refresh_stats()
    assert not win.stats_empty.isHidden()              # verwaiste Züge zählen nicht mehr -> leer
