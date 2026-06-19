"""Position-keyed schedule store: due ordering, persistence, transposition sharing."""
from datetime import date, timedelta

import chess

from opening_trainer.position_schedule_store import PositionScheduleStore
from opening_trainer.scheduler import Card, review, is_new
from opening_trainer.repertoire_tree import RepertoireTree, WHITE
from opening_trainer.position_book import build_position_book

TODAY = date(2026, 6, 14)


def _tree(ucis):
    t = RepertoireTree.new("t", WHITE)
    p = t.root_id
    for u in ucis:
        p = t.add_child(p, u).id
    return t


def test_new_positions_limited_by_new_limit():
    store = PositionScheduleStore()
    due = store.due_positions(["a", "b", "c"], TODAY, new_limit=2)
    assert len(due) == 2                       # alle neu -> auf 2 begrenzt


def test_reviews_overdue_first_then_new():
    store = PositionScheduleStore()
    store.set_card("late", Card(due=(TODAY - timedelta(days=5)).isoformat(), reps=2, interval_days=5))
    store.set_card("soon", Card(due=TODAY.isoformat(), reps=1, interval_days=1))
    due = store.due_positions(["soon", "late", "fresh"], TODAY, new_limit=10)
    assert due[:2] == ["late", "soon"]         # überfälligste zuerst
    assert "fresh" in due[2:]                  # neue danach


def test_save_load_round_trip(tmp_path):
    store = PositionScheduleStore()
    store.set_card("rnbq w KQkq -", Card(interval_days=3, ease=2.4, due="2026-06-20", reps=2))
    path = tmp_path / "position_schedule.json"
    store.save(path)
    loaded = PositionScheduleStore.load(path)
    assert loaded.card_for("rnbq w KQkq -").reps == 2
    assert loaded.card_for("rnbq w KQkq -").ease == 2.4


def test_corrupt_file_tolerated(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("not json", encoding="utf-8")
    assert PositionScheduleStore.load(path).cards == {}


def test_transposition_is_one_shared_card():
    a = _tree(["d2d4", "g8f6", "c2c4", "e7e6", "b1c3"])
    b = _tree(["c2c4", "e7e6", "d2d4", "g8f6", "g1f3"])
    book = build_position_book([a, b], chess.WHITE)

    board = chess.Board()
    for u in ["d2d4", "g8f6", "c2c4", "e7e6"]:
        board.push(chess.Move.from_uci(u))
    shared = board.epd()
    assert shared in book                                  # genau einmal (verschmolzen)

    store = PositionScheduleStore()
    store.set_card(shared, review(store.card_for(shared), True, TODAY))
    # Eine Karte deckt die gemeinsame Stellung in BEIDEN Linien ab:
    assert not is_new(store.card_for(shared))
