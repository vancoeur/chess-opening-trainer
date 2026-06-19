"""Per-position trainer: walk, auto-replies, accept-any, wrong, jump, integration."""
from datetime import date

import chess

from opening_trainer.repertoire_tree import RepertoireTree, WHITE, BLACK
from opening_trainer.position_training import PositionTrainer
from opening_trainer.position_schedule_store import PositionScheduleStore
from opening_trainer.position_book import build_position_book
from opening_trainer.scheduler import review, is_new
from opening_trainer.stats_store import StatsStore


def _tree(side, ucis, name="t"):
    t = RepertoireTree.new(name, side)
    parent = t.root_id
    for uci in ucis:
        parent = t.add_child(parent, uci).id
    return t


def test_walks_line_with_auto_opponent_replies():
    t = _tree(WHITE, ["e2e4", "e7e5", "g1f3", "b8c6", "f1b5"])
    tr = PositionTrainer(t, chess.WHITE)
    assert tr.expected_moves() == {"e2e4"}
    r = tr.play_user_move_uci("e2e4")
    assert r.kind == "correct"
    assert r.auto_reply_uci == "e7e5"            # Gegner antwortet automatisch
    assert tr.expected_moves() == {"g1f3"}
    assert tr.play_user_move_uci("g1f3").kind == "correct"
    assert tr.play_user_move_uci("f1b5").kind == "correct"
    assert tr.is_finished()


def test_wrong_move_flagged_with_expected_and_no_card():
    tr = PositionTrainer(_tree(WHITE, ["e2e4", "e7e5"]), chess.WHITE)
    r = tr.play_user_move_uci("d2d4")            # legal, aber nicht vorgesehen
    assert r.kind == "wrong"
    assert r.expected_san == "e4"
    assert tr.last_card_epd is None              # falscher Zug benotet keine Karte


def test_accept_any_prescribed_move():
    t = RepertoireTree.new("two", WHITE)
    t.add_child(t.root_id, "e2e4")
    t.add_child(t.root_id, "d2d4")
    tr = PositionTrainer(t, chess.WHITE)
    assert tr.expected_moves() == {"e2e4", "d2d4"}
    assert tr.play_user_move_uci("d2d4").kind == "correct"


def test_black_side_first_white_move_is_auto_played():
    tr = PositionTrainer(_tree(BLACK, ["e2e4", "c7c5"]), chess.BLACK)
    assert tr.last_move_uci == "e2e4"            # Gegner-Erstzug automatisch
    assert tr.expected_moves() == {"c7c5"}
    assert tr.play_user_move_uci("c7c5").kind == "correct"


def test_start_node_id_jumps_into_the_tree():
    t = _tree(WHITE, ["e2e4", "e7e5", "g1f3"])
    e4 = t.child_with_move(t.root_id, "e2e4")
    e5 = t.child_with_move(e4.id, "e7e5")
    tr = PositionTrainer(t, chess.WHITE, start_node_id=e5.id)
    assert tr.expected_moves() == {"g1f3"}


def test_card_epd_matches_book_position():
    t = _tree(WHITE, ["e2e4", "e7e5", "g1f3"])
    book = build_position_book([t], chess.WHITE)
    tr = PositionTrainer(t, chess.WHITE)
    epd0 = tr.current_epd()
    assert epd0 in book
    tr.play_user_move_uci("e2e4")
    assert tr.last_card_epd == epd0


def test_integration_grades_position_and_records_stat():
    t = _tree(WHITE, ["e2e4", "e7e5", "g1f3"])
    sched = PositionScheduleStore()
    stats = StatsStore()
    tr = PositionTrainer(t, chess.WHITE)
    today = date(2026, 6, 14)

    epd = tr.current_epd()
    fen = tr.board.fen()
    assert is_new(sched.card_for(epd))

    r = tr.play_user_move_uci("e2e4")
    assert r.kind == "correct"
    sched.set_card(tr.last_card_epd, review(sched.card_for(tr.last_card_epd), True, today))
    stats.add_event(source_name="", line_name=t.name, fen_before=fen,
                    expected_san=r.expected_san, played_san=r.played_san, correct=True)

    assert not is_new(sched.card_for(epd))               # jetzt terminiert
    assert stats.stats_for_position(epd).attempts == 1


def test_stats_for_position_ignores_move_counters():
    stats = StatsStore()
    place = "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq"
    stats.add_event(source_name="", line_name="x", fen_before=f"{place} - 0 2",
                    expected_san="Nf3", played_san="Nf3", correct=True)
    stats.add_event(source_name="", line_name="y", fen_before=f"{place} - 9 30",
                    expected_san="Nf3", played_san="Nc3", correct=False)
    s = stats.stats_for_position(f"{place} -")           # gleiche EPD trotz anderer Zähler
    assert s.attempts == 2 and s.correct == 1
