"""Schritt 2: nach jeder richtigen Antwort wird die nächste Fälligkeit sichtbar."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import chess  # noqa: E402
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
    from qt_app import i18n
    i18n.set_language("en")
    return win


def test_next_review_shown_after_correct(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    f = tmp_path / "Schwarz Skandi.pgn"
    f.write_text(PGN_BLACK, encoding="utf-8")
    win._add_pgn_source(str(f))
    win._auto_fill_sides_by_filename()
    win._drill_learn_new = False                 # Abfrage-Pfad testen (nicht Learn-Modus)
    win._start_due_session()

    tr = win._tree_trainer
    assert tr is not None and tr.is_user_turn()
    sol = tr.expected_solution()                 # der korrekte eigene Zug
    mv = chess.Move.from_uci(sol.uci)
    win._tree_drill_on_move(mv.from_square, mv.to_square)

    # neue Karte (erstmals korrekt) -> Intervall 1 Tag
    assert "next review in 1 day" in win.tree_drill_feedback.text().lower()
