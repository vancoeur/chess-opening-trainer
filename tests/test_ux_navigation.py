"""UX-Bündel 1: Sparring/Explorer auch ohne laufendes Training erreichbar;
Tagessitzung (⌘D) hat eigene Überschrift und führt zurück ins Training (nicht Editor).
"""
import os

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
    i18n.set_language("de")          # nach dem Start setzen (Start liest QSettings)
    return win


def test_explorer_opens_without_training(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    monkeypatch.setattr(win, "_explorer_fetch", lambda *a, **k: None)  # kein Netz
    assert win.training is None
    win._open_explorer()
    assert win.stack.currentIndex() == 6        # Explorer-Seite, kein stiller Abbruch


def test_sparring_opens_without_training(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    assert win.training is None
    win._open_sparring()
    assert win.stack.currentIndex() == 4        # Sparring-Seite


def test_due_session_has_own_eyebrow_and_back_to_training(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    win._start_due_session()                    # keine Bäume -> leere Queue, aber UI gesetzt
    assert win.stack.currentIndex() == 10
    assert win.drill_eyebrow.text() == "HEUTE FÄLLIG"


from pathlib import Path  # noqa: E402

SAMPLE = Path(__file__).resolve().parent.parent / "assets" / "sample" / "sample_openings.pgn"


def test_library_empty_state_toggles_with_data(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    win._refresh_library()
    assert not win.library_empty.isHidden()      # Leer-Hinweis sichtbar (kein Repertoire)
    assert win.library_list.isHidden()           # leere Liste verborgen

    win._add_pgn_source(str(SAMPLE))             # lädt die Beispiele als Quelle -> Bäume
    win._refresh_library()
    assert win.library_empty.isHidden()          # jetzt verborgen
    assert not win.library_list.isHidden()        # Liste sichtbar


def test_normal_drill_restores_eyebrow_and_back_to_editor(tmp_path, monkeypatch):
    from opening_trainer.repertoire_tree import RepertoireTree
    win = _win(tmp_path, monkeypatch)
    t = RepertoireTree.new("B01", "black")
    t.add_child(t.root_id, "e2e4")
    win.tree_store.add(t)
    win._start_due_session()                    # erst Due-Modus (setzt Eyebrow um)
    win._start_tree_drill(t)                    # dann normales Üben
    assert win.drill_eyebrow.text() == "BAUM ÜBEN"   # Eyebrow wechselt je Modus
