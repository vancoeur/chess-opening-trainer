"""Schritt 1: reine Logik für die »Heute fällig«-Übersicht — Aufschlüsselung pro
Eröffnung, Vorschau heute/morgen/Woche, fällige Stellungen einer Eröffnung."""
from datetime import date, timedelta

import chess

from opening_trainer.repertoire_tree import RepertoireTree, BLACK
from opening_trainer.position_schedule_store import PositionScheduleStore
from opening_trainer.scheduler import Card
from opening_trainer.tree_session import (
    due_breakdown, due_forecast, due_items_for_tree, build_user_position_index,
)

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


def test_breakdown_counts_due_and_new_per_opening():
    caro = _black_tree("Caro-Kann", ["e2e4", "c7c6", "d2d4", "d7d5"])    # Schwarz nach 1.e4 und 1.e4 c6 2.d4
    skandi = _black_tree("Skandinavisch", ["e2e4", "d7d5"])              # Schwarz nach 1.e4
    sched = PositionScheduleStore()
    # eine Caro-Stellung überfällig machen
    sched.set_card(_epd(["e2e4"]), Card(due=(TODAY - timedelta(days=1)).isoformat(), reps=2, interval_days=3))

    rows = due_breakdown([caro, skandi], chess.BLACK, sched, TODAY)
    by_name = {r["name"]: r for r in rows}
    assert by_name["Caro-Kann"]["due"] == 1           # die überfällige Stellung
    assert by_name["Caro-Kann"]["new"] == 1           # die zweite Caro-Stellung ist neu
    # die meistfälligen zuerst
    assert rows[0]["name"] == "Caro-Kann"


def test_forecast_buckets_today_tomorrow_week():
    t = _black_tree("Caro-Kann", ["e2e4", "c7c6", "d2d4", "d7d5", "b1c3", "d5e4"])
    sched = PositionScheduleStore()
    sched.set_card(_epd(["e2e4"]), Card(due=TODAY.isoformat(), reps=1, interval_days=1))                       # heute
    sched.set_card(_epd(["e2e4", "c7c6", "d2d4"]), Card(due=(TODAY + timedelta(days=1)).isoformat(), reps=2))  # morgen
    sched.set_card(_epd(["e2e4", "c7c6", "d2d4", "d7d5", "b1c3"]),
                   Card(due=(TODAY + timedelta(days=4)).isoformat(), reps=2))                                  # diese Woche
    f = due_forecast([t], chess.BLACK, sched, TODAY)
    assert f["today"] == 1 and f["tomorrow"] == 1 and f["week"] == 1
    assert f["new"] == 0


def test_forecast_buckets_partition_all_positions_without_overlap():
    """Absicherung der Dashboard-Zahlen: die Eimer today/tomorrow/week/new sind
    DISJUNKT, »week« ist der Tag-3–7-Rest (NICHT kumulativ), und Stellungen, die
    erst NACH einer Woche fällig sind, zählen in KEINEN Eimer. Summe der Eimer +
    »später« == alle eigenen Stellungen."""
    line = ["e2e4", "c7c6", "d2d4", "d7d5", "b1c3", "d5e4", "c3e4", "c8f5", "e4g3", "f5g6"]
    t = _black_tree("Caro-Kann", line)          # 5 eigene Schwarz-Stellungen
    total = len(build_user_position_index([t], chess.BLACK))
    assert total == 5

    sched = PositionScheduleStore()
    sched.set_card(_epd(["e2e4"]), Card(due=TODAY.isoformat(), reps=1))                                 # heute
    sched.set_card(_epd(["e2e4", "c7c6", "d2d4"]), Card(due=(TODAY + timedelta(days=1)).isoformat(), reps=1))  # morgen
    sched.set_card(_epd(["e2e4", "c7c6", "d2d4", "d7d5", "b1c3"]),
                   Card(due=(TODAY + timedelta(days=4)).isoformat(), reps=1))                            # diese Woche (Tag 4)
    sched.set_card(_epd(["e2e4", "c7c6", "d2d4", "d7d5", "b1c3", "d5e4", "c3e4"]),
                   Card(due=(TODAY + timedelta(days=30)).isoformat(), reps=1))                           # SPÄTER (kein Eimer)
    # die 5. Stellung (nach 9.Ng3) bleibt untrainiert -> new

    f = due_forecast([t], chess.BLACK, sched, TODAY)
    assert (f["today"], f["tomorrow"], f["week"], f["new"]) == (1, 1, 1, 1)
    bucketed = f["today"] + f["tomorrow"] + f["week"] + f["new"]
    assert bucketed == 4                        # die »später«-Stellung ist in KEINEM Eimer
    assert total - bucketed == 1                # genau diese eine fehlt -> Summe + später == alle


def test_due_items_for_single_tree():
    caro = _black_tree("Caro-Kann", ["e2e4", "c7c6"])
    skandi = _black_tree("Skandinavisch", ["e2e4", "d7d5"])
    sched = PositionScheduleStore()
    items = due_items_for_tree(caro, chess.BLACK, sched, TODAY, new_limit=5)
    # nur Caro-Stellungen (Schwarz nach 1.e4) — und NICHTS aus Skandinavisch
    assert items and all(tree is caro for tree, _ in items)
