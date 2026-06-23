"""Start-Hub: Tagesaktion bei vorhandenem Repertoire, sonst Beispiel-Hinweis."""
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


def test_new_user_sees_sample_prompt(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)            # kein Repertoire
    win._open_home()
    assert win.stack.currentIndex() == 12
    assert not win.home_sample_btn.isHidden()    # Beispiel-Knopf sichtbar
    assert win.home_due_btn.isHidden()           # keine Tagesaktion


def test_with_repertoire_shows_train_button(tmp_path, monkeypatch):
    from opening_trainer.repertoire_tree import RepertoireTree
    win = _win(tmp_path, monkeypatch)
    tr = RepertoireTree.new("X", "black")
    nid = tr.add_child(tr.root_id, "e2e4").id
    tr.add_child(nid, "c7c6")                     # fällige Schwarz-Stellung
    win.tree_store.add(tr)
    win._open_home()
    assert not win.home_due_btn.isHidden()        # Tagesaktion sichtbar
    assert win.home_due_btn.isEnabled()           # und aktiv (etwas fällig/neu)
    assert win.home_sample_btn.isHidden()         # kein Beispiel-Hinweis
    assert "Today" in win.home_forecast.text() or "Heute" in win.home_forecast.text()
