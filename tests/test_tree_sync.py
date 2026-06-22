"""Slice A: Laden hält Auto-Bäume + Positions-Karten in Sync (idempotent, additiv)."""
from datetime import date, timedelta

import chess

from opening_trainer.opening_sides import OpeningSides
from opening_trainer.schedule_store import ScheduleStore
from opening_trainer.position_schedule_store import PositionScheduleStore
from opening_trainer.repertoire_tree_store import RepertoireTreeStore
from opening_trainer.repertoire_tree import RepertoireTree
from opening_trainer.scheduler import Card
from opening_trainer.tree_session import due_drill_items
from opening_trainer import tree_sync

TODAY = date(2026, 6, 20)

PGN_BLACK = """[Event "x"]
[ChapterName "Skandinavisch"]

1. e4 d5 2. exd5 Qxd5 3. Nc3 Qa5 *
"""


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def _stores():
    return RepertoireTreeStore(), PositionScheduleStore()


def test_dominant_side_from_source():
    sides = OpeningSides()
    sides.set_side("Schwarz.pgn", "A", "black")
    sides.set_side("Schwarz.pgn", "B", "black")
    sides.set_side("Schwarz.pgn", "C", "white")     # Ausreißer
    assert tree_sync.dominant_side(sides, "Schwarz.pgn") == "black"
    assert tree_sync.dominant_side(sides, "Unbekannt.pgn") == "none"


def test_sync_builds_marked_trees_and_is_idempotent(tmp_path):
    f = _write(tmp_path, "Schwarz Skandi.pgn", PGN_BLACK)
    sides = OpeningSides(); sides.set_side("Schwarz Skandi.pgn", "Skandinavisch", "black")
    schedule = ScheduleStore()
    ts, ps = _stores()

    r1 = tree_sync.sync_auto_trees([f], sides, schedule, ts, ps)
    assert r1.trees == 1
    tree = ts.all()[0]
    assert tree.headers.get("_auto") == "1" and tree.side == "black"

    # zweiter Sync derselben Quelle -> KEINE Dubletten
    r2 = tree_sync.sync_auto_trees([f], sides, schedule, ts, ps)
    assert r2.trees == 1 and len(ts.all()) == 1


def test_sync_makes_due_session_nonempty(tmp_path):
    f = _write(tmp_path, "Schwarz Skandi.pgn", PGN_BLACK)
    sides = OpeningSides(); sides.set_side("Schwarz Skandi.pgn", "Skandinavisch", "black")
    schedule = ScheduleStore()
    # eine terminierte (überfällige) lineare Karte -> seedet die Schwarz-Stellungen
    schedule.set_card("Schwarz Skandi.pgn", "Skandinavisch",
                      Card(due=(TODAY - timedelta(days=2)).isoformat(), reps=3, interval_days=4))
    ts, ps = _stores()
    report = tree_sync.sync_auto_trees([f], sides, schedule, ts, ps)
    assert report.positions_seeded > 0
    items = due_drill_items(ts.by_side("black"), chess.BLACK, ps, TODAY)
    assert len(items) > 0                              # ⌘D ist nicht mehr leer (Fund #2)


def test_seeding_does_not_overwrite_active_progress(tmp_path):
    f = _write(tmp_path, "Schwarz Skandi.pgn", PGN_BLACK)
    sides = OpeningSides(); sides.set_side("Schwarz Skandi.pgn", "Skandinavisch", "black")
    schedule = ScheduleStore()
    schedule.set_card("Schwarz Skandi.pgn", "Skandinavisch",
                      Card(due=(TODAY - timedelta(days=2)).isoformat(), reps=1, interval_days=1))
    ts, ps = _stores()
    # aktive Karte auf der ersten Schwarz-Stellung (nach 1.e4): viele reps
    b = chess.Board(); b.push_uci("e2e4")
    epd = b.epd()
    ps.cards[epd] = Card(due="2030-01-01", reps=9, interval_days=99)
    tree_sync.sync_auto_trees([f], sides, schedule, ts, ps)
    assert ps.cards[epd].reps == 9                    # NICHT von der linearen Karte überschrieben


def test_editor_tree_survives_legacy_subtree_pruned(tmp_path):
    f = _write(tmp_path, "Schwarz Skandi.pgn", PGN_BLACK)
    sides = OpeningSides(); sides.set_side("Schwarz Skandi.pgn", "Skandinavisch", "black")
    schedule = ScheduleStore()
    ts, ps = _stores()

    # (a) Alt-Migrationsbaum: dieselbe Hauptlinie, KEINE Marke -> wird vom Auto-Baum geschluckt
    legacy = RepertoireTree.new("Skandinavisch alt", "black")
    nid = legacy.root_id
    for u in ["e2e4", "d7d5", "e4d5", "d8d5", "b1c3", "d5a5"]:
        nid = legacy.add_child(nid, u).id
    ts.add(legacy)
    # (b) Editor-Baum mit EIGENER Linie -> kein Teilbaum -> bleibt
    editor = RepertoireTree.new("Mein Caro", "black")
    nid = editor.root_id
    for u in ["e2e4", "c7c6", "d2d4", "d7d5"]:
        nid = editor.add_child(nid, u).id
    ts.add(editor)

    tree_sync.sync_auto_trees([f], sides, schedule, ts, ps)

    names = {t.name for t in ts.all()}
    assert "Skandinavisch alt" not in names           # Alt-Dublette entfernt
    assert "Mein Caro" in names                        # Editor-Baum erhalten
    assert any(t.headers.get("_auto") == "1" for t in ts.all())
