"""»Zurück« führt zur zuletzt besuchten Seite (Navigations-Historie)."""
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


def test_back_returns_to_previous_page(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    assert win.stack.currentIndex() == 0

    win.stack.setCurrentIndex(2)            # zur Auswertung
    assert win._nav_history == [0]
    win._go_back()
    assert win.stack.currentIndex() == 0    # zurück zum Start
    assert win._nav_history == []


def test_back_is_multi_level(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    win.stack.setCurrentIndex(1)            # Bibliothek
    win.stack.setCurrentIndex(3)            # Prüfung
    assert win._nav_history == [0, 1]
    win._go_back()
    assert win.stack.currentIndex() == 1    # zurück zur Bibliothek
    win._go_back()
    assert win.stack.currentIndex() == 0    # zurück zum Start
    win._go_back()                          # leere Historie -> Start
    assert win.stack.currentIndex() == 0


def test_back_through_due_session_is_clean(tmp_path, monkeypatch):
    from opening_trainer.repertoire_tree import RepertoireTree
    win = _win(tmp_path, monkeypatch)
    tr = RepertoireTree.new("X", "black"); tr.add_child(tr.root_id, "e2e4")
    win.tree_store.add(tr)

    win._open_due_overview()                # Start -> Übersicht (11)
    assert win.stack.currentIndex() == 11
    win._start_due_session()                # Übersicht -> Sitzung (10)
    assert win.stack.currentIndex() == 10
    win.drill_back_btn.click()              # Sitzung zurück -> Übersicht (11)
    assert win.stack.currentIndex() == 11
    win._go_back()                          # Übersicht zurück -> Start (NICHT zur Sitzung)
    assert win.stack.currentIndex() == 0


def test_home_fallback_is_overview_when_due(tmp_path, monkeypatch):
    from opening_trainer.repertoire_tree import RepertoireTree
    win = _win(tmp_path, monkeypatch)
    tr = RepertoireTree.new("X", "black")
    nid = tr.add_child(tr.root_id, "e2e4").id
    tr.add_child(nid, "c7c6")               # Schwarz-Antwort -> fällige Schwarz-Stellung
    win.tree_store.add(tr)
    assert win._due_items()                  # es gibt etwas Fälliges/Neues
    win.stack.setCurrentIndex(2)            # irgendeine Seite
    win._nav_history.clear()                # keine Historie
    win._go_back()                          # leer + fällig -> Zuhause = Übersicht (11)
    assert win.stack.currentIndex() == 11


def test_home_fallback_is_line_page_when_nothing_due(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)       # keine Bäume -> nichts fällig
    win.stack.setCurrentIndex(2)
    win._nav_history.clear()
    win._go_back()                          # leer + nichts fällig -> Linien-Seite (0)
    assert win.stack.currentIndex() == 0
