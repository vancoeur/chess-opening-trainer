"""Opening-Explorer (M4): bei HTTP 429 eine klare »später erneut«-Meldung statt
einer kryptischen Qt-Fehlermeldung. Offscreen, ohne echtes Netz."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import chess  # noqa: E402
from PySide6 import QtWidgets, QtNetwork  # noqa: E402

import qt_app.main_window as mw  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _win(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    return mw.MainWindow()


class _FakeReply:
    def __init__(self, fen, err, http):
        self._fen, self._err, self._http = fen, err, http

    def property(self, _k):
        return self._fen

    def error(self):
        return self._err

    def errorString(self):
        return "server replied: Too Many Requests"

    def attribute(self, _a):
        return self._http

    def readAll(self):
        class _D:
            def data(self):
                return b""
        return _D()

    def deleteLater(self):
        pass


def test_explorer_shows_friendly_429(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    board = chess.Board()
    win._explorer_board = board
    reply = _FakeReply(board.fen(),
                       QtNetwork.QNetworkReply.NetworkError.UnknownServerError, 429)
    win._on_explorer_reply(reply)
    txt = win.explorer_status.text().lower()
    assert "wait" in txt or "too many" in txt        # klare Meldung
    assert "unknown" not in txt                       # nicht die rohe Qt-Meldung
