"""Partien-Auswertung (UI): nach Spielernamen-Änderung neu auswerten (A2).
Offscreen gegen die echte MainWindow; schreibt keine echten QSettings."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import chess  # noqa: E402
from PySide6 import QtWidgets  # noqa: E402

from opening_trainer.repertoire_tree import RepertoireTree, WHITE  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _win(tmp_path, monkeypatch):
    import qt_app.main_window as mw
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    win = mw.MainWindow()
    monkeypatch.setattr(win._eval_settings, "setValue", lambda *a, **k: None)  # echte QSettings schonen
    return win


def _white_tree(name, ucis):
    t = RepertoireTree.new(name, WHITE)
    p = t.root_id
    for u in ucis:
        p = t.add_child(p, u).id
    return t


def test_changing_player_name_rereviews_games(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    win.tree_store.add(_white_tree("Italienisch", ["e2e4", "e7e5", "g1f3"]))
    pgn = ('[Event "x"]\n[White "alice"]\n[Black "bob"]\n[Result "1-0"]\n\n'
           '1. e4 e5 2. Nf3 *\n')
    p = tmp_path / "games.pgn"
    p.write_text(pgn, encoding="utf-8")

    captured = []
    monkeypatch.setattr(win, "_render_game_reviews", lambda results: captured.append(results))

    win._player_name = "nobody"
    win._load_games_from_path(str(p), interactive=False)
    assert captured[-1][0]["status"] == "unknown"          # »nobody« -> nicht erkannt

    # Spielernamen auf »alice« ändern -> soll AUTOMATISCH neu auswerten
    monkeypatch.setattr(QtWidgets.QInputDialog, "getText",
                        staticmethod(lambda *a, **k: ("alice", True)))
    win._set_player_name()
    assert captured[-1][0]["status"] != "unknown"          # jetzt als Weiß erkannt
    assert captured[-1][0]["color"] == chess.WHITE


def test_corrupt_games_pgn_warns(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    win._player_name = "alice"
    # zweiter Zug 'Zz9' ist unlesbar -> python-chess kürzt die Partie + füllt errors
    pgn = ('[Event "x"]\n[White "alice"]\n[Black "bob"]\n[Result "*"]\n\n'
           '1. e4 e5 2. Zz9 *\n')
    p = tmp_path / "bad.pgn"
    p.write_text(pgn, encoding="utf-8")
    win._load_games_from_path(str(p), interactive=False)
    assert "⚠" in win.games_status.text()              # ⚠-Warnung erscheint
