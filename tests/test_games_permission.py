"""Partien laden: macOS-Berechtigungsfehler verständlich melden (manuell) bzw.
beim automatischen Nachladen still bleiben."""
import os
import builtins

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _win(tmp_path, monkeypatch):
    import qt_app.main_window as mw
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    win = mw.MainWindow()
    from qt_app import i18n
    i18n.set_language("de")
    return win


def test_permission_error_message_vs_silent_autoload(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    win._player_name = "vancoeur"
    f = tmp_path / "lichess_games.pgn"
    f.write_text('[Event "x"]\n\n1. e4 e5 *\n', encoding="utf-8")

    real_open = builtins.open

    def fake_open(p, *a, **k):
        if str(p) == str(f):
            raise PermissionError(1, "Operation not permitted")
        return real_open(p, *a, **k)

    monkeypatch.setattr(builtins, "open", fake_open)

    # manuell -> verständliche macOS-Meldung
    win.games_status.setText("")
    win._load_games_from_path(str(f), interactive=True)
    txt = win.games_status.text()
    assert "macOS" in txt and ("Festplattenvollzugriff" in txt or "Full Disk" in txt)

    # automatisch -> KEINE Schreck-Meldung (Status bleibt unverändert)
    win.games_status.setText("HINWEIS")
    win._load_games_from_path(str(f), interactive=False)
    assert win.games_status.text() == "HINWEIS"
