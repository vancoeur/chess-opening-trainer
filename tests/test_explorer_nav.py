"""Explorer-Navigation: »Zug zurück« bis Zug 1, »Neu ab Grundstellung« setzt
zuverlässig auf die Startstellung zurück (auch aus tiefer Stellung)."""
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
    win = mw.MainWindow()
    monkeypatch.setattr(win, "_explorer_fetch", lambda *a, **k: None)  # kein Netz
    return win


def test_undo_steps_back_to_move_one(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    win._open_explorer()                       # ohne Training -> Grundstellung
    win._explorer_board.push_uci("e2e4")
    win._explorer_board.push_uci("c7c6")
    win._explorer_update_nav()
    assert win.explorer_undo_btn.isEnabled()
    win._explorer_undo()
    assert len(win._explorer_board.move_stack) == 1
    win._explorer_undo()
    assert len(win._explorer_board.move_stack) == 0          # bis Zug 1
    assert not win.explorer_undo_btn.isEnabled()


def test_reset_returns_to_start_from_deep_position(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    win._open_explorer()
    # tiefe Stellung simulieren (wie aus dem Training geöffnet)
    for u in ["e2e4", "c7c6", "d2d4", "d7d5", "b1c3", "d5e4", "c3e4", "c8f5"]:
        win._explorer_board.push_uci(u)
    win._explorer_seed_plies = len(win._explorer_board.move_stack)
    win._explorer_reset()
    assert win._explorer_board.fen() == chess.Board().fen()  # zurück auf Zug 1
    assert win._explorer_seed_plies == 0
    assert not win.explorer_undo_btn.isEnabled()
