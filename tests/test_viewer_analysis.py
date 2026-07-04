"""G1-Regression: Stockfish-Analyse-Ergebnisse gehören zu GENAU der Partie, für die
sie gestartet wurden — nicht zu einer, zu der der Nutzer inzwischen gewechselt hat.
Offscreen gegen die echte MainWindow (ohne echtes Stockfish)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import chess  # noqa: E402
from PySide6 import QtWidgets  # noqa: E402

from opening_trainer.engine_review import MoveIssue  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _win(tmp_path, monkeypatch):
    import qt_app.main_window as mw
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    return mw.MainWindow()


def _payload(moves):
    return {"moves": list(moves), "color": chess.WHITE, "review": None,
            "opp": "Gegner", "result": "1-0"}


def _issue(ply):
    return MoveIssue(ply=ply, move_number=ply // 2 + 1, san="Bb5", best_san="Bc4",
                     loss_cp=120, eval_after_cp=-60, severity="patzer")


def test_stale_analysis_not_applied_to_other_game(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    win._open_game_viewer(_payload(["e2e4", "e7e5", "g1f3", "b8c6", "f1b5", "a7a6"]))
    win._viewer_anal_owner = win._viewer_moves        # Analyse für Partie A gestartet
    win._open_game_viewer(_payload(["d2d4", "d7d5"]))  # Nutzer wechselt zu Partie B (kürzer)
    win._on_viewer_analysis([_issue(4)])               # A's Ergebnis trifft verspätet ein
    assert win._viewer_issues == {}                    # NICHT auf Partie B angewendet
    assert win.viewer_blunder_btn.isHidden()           # keine falschen Patzer-Markierungen


def test_fresh_analysis_is_applied(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    win._open_game_viewer(_payload(["e2e4", "e7e5", "g1f3", "b8c6"]))
    win._viewer_anal_owner = win._viewer_moves         # Analyse für die AKTUELLE Partie
    win._on_viewer_analysis([_issue(2)])
    assert 2 in win._viewer_issues                     # auf die aktuelle Partie angewendet
