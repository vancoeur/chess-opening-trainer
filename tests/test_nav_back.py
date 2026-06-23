"""»Zurück« führt zur zuletzt besuchten Seite; ohne Historie zum Start-Hub (12)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

HOME = 12


def _win(tmp_path, monkeypatch):
    import qt_app.main_window as mw
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    return mw.MainWindow()


def test_starts_on_home_hub(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    assert win.stack.currentIndex() == HOME      # App startet auf dem Hub


def test_back_returns_to_previous_page(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)            # auf dem Hub (12)
    win.stack.setCurrentIndex(2)                 # zur Auswertung
    assert win._nav_history == [HOME]
    win._go_back()
    assert win.stack.currentIndex() == HOME      # zurück zum Hub
    assert win._nav_history == []


def test_back_is_multi_level(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)            # Hub (12)
    win.stack.setCurrentIndex(1)                 # Bibliothek
    win.stack.setCurrentIndex(3)                 # Prüfung
    assert win._nav_history == [HOME, 1]
    win._go_back()
    assert win.stack.currentIndex() == 1         # zurück zur Bibliothek
    win._go_back()
    assert win.stack.currentIndex() == HOME      # zurück zum Hub
    win._go_back()                               # leere Historie -> bleibt Hub
    assert win.stack.currentIndex() == HOME


def test_back_through_due_session_is_clean(tmp_path, monkeypatch):
    from opening_trainer.repertoire_tree import RepertoireTree
    win = _win(tmp_path, monkeypatch)
    tr = RepertoireTree.new("X", "black"); tr.add_child(tr.root_id, "e2e4")
    win.tree_store.add(tr)

    win._open_due_overview()                     # Hub -> Übersicht (11)
    assert win.stack.currentIndex() == 11
    win._start_due_session()                     # Übersicht -> Sitzung (10)
    assert win.stack.currentIndex() == 10
    win.drill_back_btn.click()                   # Sitzung zurück -> Übersicht (11)
    assert win.stack.currentIndex() == 11
    win._go_back()                               # Übersicht zurück -> Hub (NICHT zur Sitzung)
    assert win.stack.currentIndex() == HOME
