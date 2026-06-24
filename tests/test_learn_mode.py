"""Übe-Ansicht: Linien-Kontext + Learn-Modus (neue Stellungen erst zeigen).
Offscreen gegen die echte MainWindow.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

PGN_BLACK = """[Event "x"]
[ChapterName "Skandinavisch"]

1. e4 d5 2. exd5 Qxd5 3. Nc3 Qa5 *
"""


def _win(tmp_path, monkeypatch):
    import qt_app.main_window as mw
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    win = mw.MainWindow()
    f = tmp_path / "Schwarz Skandi.pgn"
    f.write_text(PGN_BLACK, encoding="utf-8")
    win._add_pgn_source(str(f))
    win._auto_fill_sides_by_filename()
    return win


def test_line_context_shows_moves(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    win._drill_learn_new = False
    win._start_due_session()
    # Linien-Kontext zeigt die Züge bis zur aktuellen Stellung
    txt = win.tree_drill_line.text()
    assert "e4" in txt and "?" in txt


def test_learn_mode_shows_solution_then_advances(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    win._drill_learn_new = True
    win._start_due_session()
    # neue Stellung -> Learn-Modus: »Verstanden«-Knopf sichtbar, Lösung im Status
    assert win._drill_learn_active is True
    assert not win.drill_learned_btn.isHidden()
    assert "move here is" in win.tree_drill_status.text().lower()
    # Brett-Eingabe wird im Learn-Modus ignoriert (kein Benoten/Absturz)
    win._tree_drill_on_move(0, 0)
    # »Verstanden« plant die Karte ein und geht weiter
    epd = win._tree_trainer.board.epd()
    win._drill_mark_learned()
    from opening_trainer.scheduler import is_new
    assert not is_new(win.position_schedule.card_for(epd))   # nicht mehr „neu"


def test_learn_toggle_off_quizzes_new(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    win._drill_learn_new = True
    win._start_due_session()
    assert win._drill_learn_active is True
    win.drill_learn_check.setChecked(False)        # Learn aus -> abfragen
    assert win._drill_learn_active is False
    assert win.drill_learned_btn.isHidden()
