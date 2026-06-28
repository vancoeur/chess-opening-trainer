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
    low = win.home_forecast.text().lower()
    assert "heute" in low or "today" in low


def _black_caro(win):
    """Repertoire mit einer eigenen Schwarz-Stellung (nach 1.e4: …c6)."""
    from opening_trainer.repertoire_tree import RepertoireTree
    tr = RepertoireTree.new("Caro", "black")
    nid = tr.add_child(tr.root_id, "e2e4").id
    tr.add_child(nid, "c7c6")
    win.tree_store.add(tr)
    return tr


def test_weak_card_hidden_without_errors(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _black_caro(win)                              # Repertoire, aber keine Fehler
    win._open_home()
    assert win.home_weak.isHidden()               # nichts wacklig -> Karte weg


def test_weak_card_shows_and_drills_open_errors(tmp_path, monkeypatch):
    import chess
    win = _win(tmp_path, monkeypatch)
    _black_caro(win)
    board = chess.Board()
    board.push(chess.Move.from_uci("e2e4"))       # Schwarz am Zug, soll …c6 spielen
    win.stats_store.add_event(
        source_name="s", line_name="l", fen_before=board.fen(),
        expected_san="c6", played_san="e6", correct=False)   # offener Fehler
    win._open_home()
    assert not win.home_weak.isHidden()           # Schwächen-Karte sichtbar
    assert "1" in win.home_weak_btn.text()        # Zähler zeigt die eine Stellung

    win._start_weak_session()                     # Knopf startet die Sitzung
    assert win.stack.currentIndex() == 10         # Drill-Seite
    assert win._due_total == 1                    # genau die wacklige Stellung
