"""Migration v2: lines+old data -> trees + per-position schedule (preserve months)."""
import chess

from opening_trainer.pgn_loader import OpeningLine
from opening_trainer.opening_sides import OpeningSides
from opening_trainer.schedule_store import ScheduleStore
from opening_trainer.line_notes import LineNotes
from opening_trainer.scheduler import Card
from opening_trainer.migration_v2 import (
    migrate_data, run_migration, tree_from_line, stronger_card,
)

SRC = "r.pgn"


def _line(name, ucis):
    return OpeningLine(name=name, headers={"ChapterName": name}, moves_uci=ucis, moves_san=[], source_name=SRC)


def _epd(ucis):
    b = chess.Board()
    for u in ucis:
        b.push(chess.Move.from_uci(u))
    return b.epd()


def test_sides_and_notes_map_to_trees():
    lines = [_line("A", ["e2e4", "e7e5"]), _line("B", ["d2d4"])]
    sides = OpeningSides()
    sides.set_side(SRC, "A", "white")
    sides.set_side(SRC, "B", "black")
    notes = LineNotes()
    notes.set_note(SRC, "A", "Plan: kingside")

    ts, _ps, rep = migrate_data(lines, sides, ScheduleStore(), notes)
    ta = next(t for t in ts.all() if t.name == "A")
    tb = next(t for t in ts.all() if t.name == "B")
    assert ta.side == "white" and tb.side == "black"
    assert ta.root.comment == "Plan: kingside"
    assert rep.trees == 2 and rep.sided_trees == 2 and rep.notes_migrated == 1


def test_schedule_seeds_every_own_position_of_the_line():
    line = _line("A", ["e2e4", "e7e5", "g1f3"])  # weiße Stellungen: Start + nach e4 e5
    sides = OpeningSides()
    sides.set_side(SRC, "A", "white")
    sched = ScheduleStore()
    sched.set_card(SRC, "A", Card(interval_days=5, ease=2.5, due="2026-06-20", reps=3))

    _ts, ps, rep = migrate_data([line], sides, sched, LineNotes())
    assert rep.positions_seeded == 2
    assert ps.card_for(_epd([])).reps == 3                 # Startstellung trägt die Linien-Karte
    assert ps.card_for(_epd(["e2e4", "e7e5"])).reps == 3


def test_new_unscheduled_line_seeds_no_cards():
    line = _line("A", ["e2e4"])
    sides = OpeningSides()
    sides.set_side(SRC, "A", "white")
    _ts, ps, rep = migrate_data([line], sides, ScheduleStore(), LineNotes())  # keine Karte = neu
    assert rep.positions_seeded == 0 and ps.cards == {}


def test_transposition_keeps_the_stronger_card():
    a = _line("A", ["d2d4", "g8f6", "c2c4", "e7e6", "b1c3"])
    b = _line("B", ["c2c4", "e7e6", "d2d4", "g8f6", "g1f3"])
    sides = OpeningSides()
    sides.set_side(SRC, "A", "white")
    sides.set_side(SRC, "B", "white")
    sched = ScheduleStore()
    sched.set_card(SRC, "A", Card(interval_days=10, ease=2.5, due="2026-06-01", reps=5))  # stärker
    sched.set_card(SRC, "B", Card(interval_days=1, ease=2.5, due="2026-06-02", reps=1))   # schwächer

    _ts, ps, rep = migrate_data([a, b], sides, sched, LineNotes())
    shared = _epd(["d2d4", "g8f6", "c2c4", "e7e6"])
    assert ps.card_for(shared).reps == 5                   # stärkere Karte gewinnt
    assert rep.collisions >= 1


def test_stronger_card_rules():
    assert stronger_card(Card(reps=3, due="2026-06-10"), Card(reps=1, due="2026-06-01")).reps == 3
    earlier = Card(reps=2, due="2026-06-01")
    assert stronger_card(Card(reps=2, due="2026-06-05"), earlier) is earlier
    scheduled = Card(reps=1, due="2026-06-01")
    assert stronger_card(Card(), scheduled) is scheduled   # neue Karte (leer) ist schwächer


def test_run_migration_writes_files_backup_and_is_idempotent(tmp_path):
    OpeningSides_ = OpeningSides()
    OpeningSides_.set_side(SRC, "A", "white")
    OpeningSides_.save(tmp_path / "opening_sides.json")
    sched = ScheduleStore()
    sched.set_card(SRC, "A", Card(interval_days=3, ease=2.5, due="2026-06-20", reps=2))
    sched.save(tmp_path / "schedule.json")
    LineNotes().save(tmp_path / "line_notes.json")

    lines = [_line("A", ["e2e4", "e7e5"])]
    rep = run_migration(tmp_path, lines)
    assert not rep.skipped
    assert (tmp_path / "repertoire_trees.json").exists()
    assert (tmp_path / "position_schedule.json").exists()
    assert (tmp_path / "opening_sides.json.backup-pre-trees").exists()
    assert (tmp_path / ".migrated_to_trees").exists()

    rep2 = run_migration(tmp_path, lines)                   # zweiter Lauf: übersprungen
    assert rep2.skipped


def test_dry_run_writes_nothing(tmp_path):
    rep = run_migration(tmp_path, [_line("A", ["e2e4"])], dry_run=True)
    assert rep.trees == 1
    assert not (tmp_path / "repertoire_trees.json").exists()
    assert not (tmp_path / ".migrated_to_trees").exists()
