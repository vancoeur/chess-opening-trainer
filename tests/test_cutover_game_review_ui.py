"""Cutover Scheibe 2 — UI: die Partie-Auswertung gleicht jetzt gegen das
varianten-bewusste Baum-Buch ab. Eine in einer Nebenvariante des Repertoires
gespielte Partie gilt als »gefolgt«, nicht mehr als »abgewichen«.
Offscreen gegen die echte ``MainWindow``.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets, QtCore  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

# Repertoire mit Variante: nach 1.e4 e5 sind 2.Nf3 UND 2.Bc4 vorgesehen.
REP_PGN = """[Event "x"]
[White "Rep"]

1. e4 e5 2. Nf3 (2. Bc4 Bc5) 2... Nc6 *
"""

# Eigene Partie: als »Me« die Variante 2.Bc4 gespielt.
GAME_PGN = """[Event "g"]
[White "Me"]
[Black "Opp"]
[Result "1-0"]

1. e4 e5 2. Bc4 Bc5 1-0
"""


def _win(tmp_path, monkeypatch):
    import qt_app.main_window as mw
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    return mw.MainWindow()


def test_variation_game_is_followed_not_deviated(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    rep = tmp_path / "Weiss Repertoire.pgn"
    rep.write_text(REP_PGN, encoding="utf-8")
    win._add_pgn_source(str(rep))
    win._auto_fill_sides_by_filename()
    assert win.tree_store.by_side("white"), "Weiß-Baum sollte angelegt sein"

    win._player_name = "Me"
    games = tmp_path / "games.pgn"
    games.write_text(GAME_PGN, encoding="utf-8")
    win._load_games_from_path(str(games), interactive=False)

    statuses = [
        win.games_list.item(i).data(QtCore.Qt.UserRole)["status"]
        for i in range(win.games_list.count())
    ]
    assert "followed" in statuses
    assert "deviated" not in statuses
