"""Red-team hardening: untrusted text (PGN opening/player names) must be shown
as plain text, never interpreted as HTML/rich text."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets, QtCore  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_plain_label_uses_plaintext_format():
    from qt_app.main_window import MainWindow

    evil = "<a href='http://evil'>Sizilianisch</a> <b>HACKED</b>"
    lbl = MainWindow._plain_label(evil)
    assert lbl.textFormat() == QtCore.Qt.TextFormat.PlainText
    # Der Inhalt bleibt wörtlich erhalten (wird nicht als Markup interpretiert).
    assert lbl.text() == evil
