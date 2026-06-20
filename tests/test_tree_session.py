"""Daily due-position session across the whole tree repertoire."""
from datetime import date, timedelta

import chess

from opening_trainer.repertoire_tree import RepertoireTree, WHITE, BLACK
from opening_trainer.position_schedule_store import PositionScheduleStore
from opening_trainer.scheduler import Card, review
from opening_trainer.tree_session import build_user_position_index, due_drill_items

TODAY = date(2026, 6, 20)


def _black_tree(name, ucis):
    t = RepertoireTree.new(name, BLACK)
    p = t.root_id
    for u in ucis:
        p = t.add_child(p, u).id
    return t


def _epd(ucis):
    b = chess.Board()
    for u in ucis:
        b.push(chess.Move.from_uci(u))
    return b.epd()


def test_index_maps_user_positions_to_tree_and_node():
    t = _black_tree("caro", ["e2e4", "c7c6", "d2d4", "d7d5"])
    index = build_user_position_index([t], chess.BLACK)
    # Eigene (Schwarz-)Stellungen: nach 1.e4 und nach 1.e4 c6 2.d4
    assert _epd(["e2e4"]) in index
    assert _epd(["e2e4", "c7c6", "d2d4"]) in index
    tree, node_id = index[_epd(["e2e4"])]
    assert tree is t and node_id in t.nodes


def test_only_matching_side_trees_count():
    white = RepertoireTree.new("w", WHITE)
    white.add_child(white.root_id, "e2e4")
    assert build_user_position_index([white], chess.BLACK) == {}


def test_due_items_are_due_first_then_limited_new():
    a = _black_tree("A", ["e2e4", "c7c6"])               # Schwarz-Stellung nach 1.e4
    b = _black_tree("B", ["d2d4", "d7d5"])               # Schwarz-Stellung nach 1.d4
    sched = PositionScheduleStore()
    # mache die Stellung aus Baum A überfällig:
    epd_a = _epd(["e2e4"])
    sched.set_card(epd_a, Card(due=(TODAY - timedelta(days=3)).isoformat(), reps=2, interval_days=3))
    items = due_drill_items([a, b], chess.BLACK, sched, TODAY, new_limit=5)
    trees = [tr.name for tr, _ in items]
    assert trees[0] == "A"            # fällige zuerst
    assert "B" in trees              # B ist neu -> kommt als neue dazu


def test_new_limit_caps_new_positions():
    trees = [_black_tree(f"T{i}", ["e2e4", "c7c6", "g1f3", "d7d5"]) for i in range(3)]
    # alle Stellungen neu; jeder Baum hat 2 eigene Stellungen, aber viele teilen Transpositionen
    sched = PositionScheduleStore()
    items = due_drill_items(trees, chess.BLACK, sched, TODAY, new_limit=1)
    assert len(items) == 1            # auf 1 neue begrenzt
