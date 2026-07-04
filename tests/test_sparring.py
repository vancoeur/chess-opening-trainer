"""Sparring / Play-Stockfish (M2): kein Dauerhang nach Engine-Fehler, kein
Hintergrund-Zug nach Seitenwechsel. Offscreen, ohne echte Stockfish-Binärdatei."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import chess  # noqa: E402
from PySide6 import QtWidgets  # noqa: E402

import qt_app.main_window as mw  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _win(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    return mw.MainWindow()


def test_worker_emits_failed_when_engine_broken():
    """SP1: eine bereits »kaputte« Engine gibt bei play() nicht still auf, sondern
    meldet failed — sonst bliebe das Brett ewig auf »denkt …«."""
    w = mw._SparringWorker()
    w._broken = True                     # Engine ist ausgefallen
    fired = []
    w.failed.connect(lambda msg: fired.append(msg))
    w.play(chess.Board().fen(), 5, 50)
    assert fired                         # failed wurde ausgelöst (UI kann sich erholen)


def test_engine_reply_ignored_after_leaving_sparring(tmp_path, monkeypatch):
    """SP2: verlässt der Nutzer die Sparring-Seite, darf eine eintreffende Engine-
    Antwort das Brett NICHT im Hintergrund weiterspielen."""
    win = _win(tmp_path, monkeypatch)
    win._open_sparring()                 # richtet _spar_board ein, Seite 4
    win.stack.setCurrentIndex(12)        # Nutzer wechselt weg (Start-Hub)
    win._spar_thinking = True
    fen_before = win._spar_board.fen()
    win._on_spar_played(fen_before, "e2e4", 0, 0, 0)   # verspätete Engine-Antwort
    assert win._spar_board.fen() == fen_before         # Brett NICHT verändert
    assert win._spar_thinking is False                 # Zustand sauber zurückgesetzt
