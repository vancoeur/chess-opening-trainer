"""UX-Bündel 5: Partie-Hinweise ohne zugeordnetes Repertoire.

(Die Eval-Leisten- und Lösungs-Tests der alten Seite 0 sind mit dem Cutover
entfallen.)"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _win(tmp_path, monkeypatch, lang="en"):
    import qt_app.main_window as mw
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    win = mw.MainWindow()
    from qt_app import i18n
    i18n.set_language(lang)
    return win


def test_game_review_warns_without_assigned_repertoire(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch, lang="en")
    win.lines = []                                       # nichts zugeordnet
    win._open_game_review()
    assert "assign some openings" in win.games_status.text().lower()
