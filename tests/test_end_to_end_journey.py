"""End-zu-Ende: fährt die ECHTE MainWindow durch die komplette Nutzer-Reise —
Ordner laden → Repertoire-Baum → eine Sitzung spielen (richtig + falsch) →
eine geladene Eröffnung bearbeiten (Kommentar + Löschen) und den Sync überstehen →
Persistenz-Round-Trip. Selbst-enthaltenes synthetisches Repertoire (kein Netz,
kein Stockfish); schreibt nur in einen Wegwerf-Datenordner."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import chess  # noqa: E402
from PySide6 import QtWidgets  # noqa: E402

from opening_trainer.tree_session import variation_outline  # noqa: E402
from opening_trainer.position_training import PositionTrainer  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

FILES = {
    "Weiss - Italienisch.pgn":
        '[Event "x"]\n[ChapterName "Italienisch"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 *\n',
    "Schwarz - Caro-Kann.pgn":
        '[Event "x"]\n[ChapterName "Caro-Kann"]\n\n1. e4 c6 2. d4 d5 3. Nc3 dxe4 *\n',
    "Schwarz - Skandinavisch.pgn":       # teilt die 1.e4-Grundstellung mit Caro (Schwarz am Zug)
        '[Event "x"]\n[ChapterName "Skandinavisch"]\n\n1. e4 d5 2. exd5 Qxd5 3. Nc3 Qa5 *\n',
}


def _win(tmp_path, monkeypatch):
    import qt_app.main_window as mw
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    # keine Modals im Headless
    monkeypatch.setattr(QtWidgets.QMessageBox, "information", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QtWidgets.QMessageBox, "warning", staticmethod(lambda *a, **k: None))
    folder = tmp_path / "rep"
    folder.mkdir()
    for name, text in FILES.items():
        (folder / name).write_text(text, encoding="utf-8")
    win = mw.MainWindow()
    win._add_pgn_source(str(folder))
    win._auto_fill_sides_by_filename()
    return win, mw


def test_full_journey_loads_trains_edits_and_persists(tmp_path, monkeypatch):
    win, mw = _win(tmp_path, monkeypatch)

    # 1) geladen, Seiten erkannt
    trees = win.tree_store.all()
    assert len(win._catalog()) == 3
    assert {t.side for t in trees} == {"white", "black"}
    assert all(t.side in ("white", "black") for t in trees)     # keine 'none' übrig

    # 2) Repertoire-Baum: jede Variante beider Seiten löst an Stellung 1 sauber auf
    #    (geteilte Grundstellung darf NICHT die falsche Eröffnung liefern)
    win._open_repertoire_tree()
    for idx, side_name, color in ((0, "white", chess.WHITE), (1, "black", chess.BLACK)):
        win.reptree_side_combo.setCurrentIndex(idx)
        groups = variation_outline(win.tree_store.by_side(side_name), color)
        assert groups
        for g in groups:
            items = win._reptree_group_user_items(g)
            if items:
                tr, nid, col = items[0]
                assert PositionTrainer(tr, col, start_node_id=nid,
                                       auto_opponent=True).expected_solution() is not None

    # 3) eine Sitzung wirklich spielen: richtiger Zug wird benotet, falscher erkannt
    win._drill_learn_new = False
    ital = next(t for t in win.tree_store.all() if t.name == "Italienisch")
    win._start_tree_drill(ital)
    tr = win._tree_trainer
    sol = tr.expected_solution()
    assert sol is not None and sol.san == "e4"
    epd0 = tr.board.epd()
    u = sol.uci
    win._tree_drill_on_move(chess.parse_square(u[:2]), chess.parse_square(u[2:4]))
    assert epd0 in win.position_schedule.cards                  # richtig -> eingeplant
    tr = win._tree_trainer
    if not tr.is_finished() and tr.is_user_turn():
        wrong = next(m.uci() for m in tr.board.legal_moves
                     if m.uci() != tr.expected_solution().uci)
        win._tree_drill_wrong = False
        win._tree_drill_on_move(chess.parse_square(wrong[:2]), chess.parse_square(wrong[2:4]))
        assert win._tree_drill_wrong is True                    # falsch -> als falsch erkannt

    # 4) E1: eine geladene Eröffnung bearbeiten (Kommentar + Löschen) -> übersteht Sync
    auto = next(t for t in win.tree_store.all()
                if t.headers.get("_auto") == "1" and len(t.nodes) > 4)
    name = auto.name
    auto.headers.pop("_auto", None)
    auto.headers["_edited"] = "1"
    auto.headers["_from_source"] = auto.headers.pop("_source", None)
    auto.nodes[auto.children_of(auto.root_id)[0].id].comment = "MEINE NOTIZ"
    deep = next(gk[0] for k in auto.children_of(auto.root_id)
                if (gk := auto.children_of(k.id)))
    auto.delete_subtree(deep.id)
    n_after = len(auto.nodes)
    win.tree_store.save(win.trees_path)
    win._sync_auto_trees()                                      # App-Neustart
    same = [t for t in win.tree_store.all() if t.name == name]
    assert len(same) == 1                                       # keine Dublette
    assert any(getattr(n, "comment", "") == "MEINE NOTIZ" for n in same[0].nodes.values())
    assert len(same[0].nodes) == n_after                        # gelöschter Zug bleibt weg

    # 5) Persistenz-Round-Trip: zweite App auf denselben Daten lädt dasselbe
    win.tree_store.save(win.trees_path)
    win.position_schedule.save(win.position_schedule_path)
    n_trees = len(win.tree_store.all())
    win2 = mw.MainWindow()
    assert len(win2.tree_store.all()) == n_trees
