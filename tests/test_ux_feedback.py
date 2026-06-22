"""UX-Bündel 5: Eval-Leiste ohne Stockfish ausgeblendet, Lösungs-/Partie-Hinweise."""
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

SAMPLE = Path(__file__).resolve().parent.parent / "assets" / "sample" / "sample_openings.pgn"


def _win(tmp_path, monkeypatch, lang="en"):
    import qt_app.main_window as mw
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    win = mw.MainWindow()
    from qt_app import i18n
    i18n.set_language(lang)
    return win


def test_eval_bar_hidden_without_stockfish(tmp_path, monkeypatch):
    import qt_app.main_window as mw
    import qt_app.engine as eng
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    monkeypatch.setattr(eng, "find_stockfish", lambda: None)
    win = mw.MainWindow()
    assert win._stockfish_available is False
    assert win.eval_bar.isHidden()                       # kein leerer grauer Streifen
    assert not win._eval_bar_action.isEnabled()          # Menüpunkt deaktiviert


def test_eval_bar_available_with_stockfish(tmp_path, monkeypatch):
    import qt_app.main_window as mw
    import qt_app.engine as eng
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    monkeypatch.setattr(eng, "find_stockfish", lambda: Path("/usr/bin/true"))
    win = mw.MainWindow()
    assert win._stockfish_available is True
    assert win._eval_bar_action.isEnabled()
    assert win.eval_bar.toolTip() != ""                  # erklärt, was die Leiste ist


def test_solution_tells_user_to_replay(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch, lang="en")
    from opening_trainer.pgn_loader import load_pgn_file
    win.lines = load_pgn_file(SAMPLE)
    win._auto_fill_sides_by_filename()
    win._refill_queue(); win._start_next()
    win._show_solution()
    assert "play it yourself" in win.status.text().lower()


def test_game_review_warns_without_assigned_repertoire(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch, lang="en")
    win.lines = []                                       # nichts zugeordnet
    win._open_game_review()
    assert "assign some openings" in win.games_status.text().lower()
