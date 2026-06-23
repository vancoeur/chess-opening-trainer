"""Sprachwechsel wirkt SOFORT (ohne Neustart): Oberfläche wird neu aufgebaut."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _win(tmp_path, monkeypatch):
    import qt_app.main_window as mw
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    return mw.MainWindow()


def test_language_switch_is_live(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)

    win._set_language("de")
    assert win.lib_title.text() == "Deine Eröffnungen"     # deutsch

    win._set_language("en")                                 # live umschalten
    assert win.lib_title.text() == "Your openings"          # sofort englisch
    assert win.stack.count() == 12                          # Oberfläche intakt
    from qt_app import i18n
    assert i18n.language() == "en"

    win._set_language("de")                                 # und wieder zurück
    assert win.lib_title.text() == "Deine Eröffnungen"


def test_switch_keeps_current_page(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    win._set_language("de")
    win.stack.setCurrentIndex(1)        # Bibliothek
    win._set_language("en")
    assert win.stack.currentIndex() == 1   # gleiche Seite nach dem Umschalten
