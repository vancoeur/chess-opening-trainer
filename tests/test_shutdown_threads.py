"""Hintergrund-Threads werden bei JEDEM Beende-Weg sauber gestoppt.

Regression: Beim Programmende (⌘Q / app.quit() / Interpreter-Shutdown) wurde
closeEvent nicht immer aufgerufen; ein noch laufender Worker-QThread löste dann
im Destruktor Qts qFatal/abort() aus (SIGABRT). Jetzt hängt das Stoppen an
QApplication.aboutToQuit und ist idempotent gegen mehrfaches Aufrufen.
"""
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _win(tmp_path, monkeypatch):
    import qt_app.main_window as mw
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    return mw.MainWindow()


def test_eval_thread_is_stopped(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    win._ensure_eval_worker()
    th = win._eval_bar_thread
    assert th is not None and th.isRunning()

    win._stop_all_threads()
    assert win._eval_bar_thread is None
    assert not th.isRunning()                 # Thread wirklich beendet


def test_stop_all_threads_is_idempotent(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    win._ensure_eval_worker()
    win._stop_all_threads()
    # Zweiter Aufruf (z. B. closeEvent nach aboutToQuit) darf nicht crashen.
    win._stop_all_threads()
    assert win._threads_stopped is True


def test_close_event_stops_threads(tmp_path, monkeypatch):
    from PySide6 import QtGui
    win = _win(tmp_path, monkeypatch)
    win._ensure_eval_worker()
    th = win._eval_bar_thread
    win.closeEvent(QtGui.QCloseEvent())
    assert not th.isRunning()


def test_about_to_quit_is_connected(tmp_path, monkeypatch):
    """Der zentrale Beende-Pfad: aboutToQuit muss das Stoppen auslösen."""
    win = _win(tmp_path, monkeypatch)
    win._ensure_eval_worker()
    th = win._eval_bar_thread
    # aboutToQuit von Hand feuern (ohne die ganze App zu beenden)
    _app.aboutToQuit.emit()
    assert win._threads_stopped is True
    assert not th.isRunning()
