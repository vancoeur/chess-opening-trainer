"""Härtungs-Runde 6 (Red-Team 2026-11-16):

1. Lernplan: mehrfaches Üben am selben Tag bläht das Intervall nicht mehr auf.
2. Schwächen: werden pro STELLUNG abgebaut — egal mit welchem erlaubten Zug und
   über welche Zugfolge.
3. Beschädigte Speicherdateien lassen die App nicht mehr abstürzen.
"""
import json
import os
from datetime import date

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import chess  # noqa: E402

from opening_trainer import tree_session as ts  # noqa: E402
from opening_trainer.pgn_tree_import import import_pgn_text  # noqa: E402
from opening_trainer.position_schedule_store import PositionScheduleStore  # noqa: E402
from opening_trainer.scheduler import (  # noqa: E402
    Card, days_until_due, is_due, review, review_if_due)
from opening_trainer.settings_store import SettingsStore  # noqa: E402
from opening_trainer.stats_store import StatsStore  # noqa: E402

TODAY = date(2026, 11, 16)


# --- 1) Lernplan ---------------------------------------------------------

def test_repeated_correct_answers_same_day_do_not_inflate_interval():
    card = Card()
    for _ in range(6):
        card = review_if_due(card, True, TODAY)
    assert card.interval_days == 1            # vorher: 125 Tage nach 6 Durchläufen
    assert card.due == "2026-11-17"
    assert card.reps == 1


def test_due_card_still_advances_normally():
    card = review_if_due(Card(), True, TODAY)                    # neu -> 1 Tag
    card = review_if_due(card, True, date(2026, 11, 17))         # fällig -> 3 Tage
    assert card.interval_days == 3
    card = review_if_due(card, True, date(2026, 11, 25))         # überfällig -> wächst
    assert card.interval_days == 8


def test_mistake_on_not_due_card_still_resets():
    card = review(review(Card(), True, TODAY), True, TODAY)      # 3 Tage, nicht fällig
    failed = review_if_due(card, False, TODAY)
    assert failed.interval_days == 0 and failed.reps == 0
    assert is_due(failed, TODAY)
    # danach am selben Tag sauber: wieder ganz normal einplanen (Karte ist fällig)
    assert review_if_due(failed, True, TODAY).interval_days == 1


def test_days_until_due():
    assert days_until_due(Card(due="2026-11-19"), TODAY) == 3
    assert days_until_due(Card(due="2026-11-01"), TODAY) == 0
    assert days_until_due(Card(due="kaputt"), TODAY) == 0


# --- 2) Schwächen --------------------------------------------------------

def _fen(*sans):
    b = chess.Board()
    for s in sans:
        b.push_san(s)
    return b.fen()


def test_weakness_clears_with_the_other_prescribed_move():
    tree = import_pgn_text("1. e4 e5 2. Nf3 (2. Bc4 Nf6) 2... Nc6 *", side="white")[0]
    stats = StatsStore()
    fen = _fen("e4", "e5")
    stats.add_event(source_name="", line_name=tree.name, fen_before=fen,
                    expected_san="Nf3", played_san="d4", correct=False)
    assert len(ts.weak_position_fens([tree], [], stats)) == 1
    stats.add_event(source_name="", line_name=tree.name, fen_before=fen,
                    expected_san="Bc4", played_san="Bc4", correct=True)
    assert ts.weak_position_fens([tree], [], stats) == []


def test_weakness_clears_via_transposition_with_other_move_counters():
    tree = import_pgn_text("1. d4 Nf6 2. c4 e6 3. Nc3 *", side="white")[0]
    a = _fen("d4", "Nf6", "c4", "e6")
    b = _fen("c4", "e6", "d4", "Nf6")
    assert a != b                                   # gleiche Stellung, andere Zähler
    stats = StatsStore()
    stats.add_event(source_name="", line_name="x", fen_before=a,
                    expected_san="Nc3", played_san="Nf3", correct=False)
    stats.add_event(source_name="", line_name="x", fen_before=b,
                    expected_san="Nc3", played_san="Nc3", correct=True)
    assert ts.weak_position_fens([tree], [], stats) == []


def test_weakness_stays_open_until_solved_and_counts_per_position():
    tree = import_pgn_text("1. e4 e5 2. Nf3 Nc6 *", side="white")[0]
    stats = StatsStore()
    fen = _fen("e4", "e5")
    for _ in range(2):
        stats.add_event(source_name="", line_name=tree.name, fen_before=fen,
                        expected_san="Nf3", played_san="d4", correct=False)
    probs = ts.open_error_positions([tree], chess.WHITE, stats)
    assert len(probs) == 1 and probs[0]["count"] == 2 and probs[0]["expected_san"] == "Nf3"
    stats.add_event(source_name="", line_name=tree.name, fen_before=fen,
                    expected_san="Nf3", played_san="Nf3", correct=True)
    assert ts.open_error_positions([tree], chess.WHITE, stats)[0]["count"] == 1


# --- 3) beschädigte Dateien ----------------------------------------------

def test_stats_load_survives_wrong_shapes_and_keeps_a_copy(tmp_path):
    for content in ("[]", "5", '{"events": null}', '{"events":[{"timest'):
        f = tmp_path / "training_stats.json"
        f.write_text(content)
        assert StatsStore.load(f).events == []
        assert (tmp_path / "training_stats.json.defekt").read_text() == content


def test_stats_load_skips_only_the_broken_event(tmp_path):
    good = {"timestamp": "t", "source_name": "", "line_name": "x",
            "fen_before": chess.STARTING_FEN, "expected_san": "e4",
            "played_san": "e4", "correct": True}
    f = tmp_path / "training_stats.json"
    f.write_text(json.dumps({"events": [{"timestamp": "x"}, "quatsch", good]}))
    store = StatsStore.load(f)
    assert len(store.events) == 1 and store.events[0].line_name == "x"
    assert not (tmp_path / "training_stats.json.defekt").exists()


def test_settings_load_survives_wrong_shape(tmp_path):
    f = tmp_path / "settings.json"
    for content in ("[]", "5", '{"pgn_sources": 7}'):
        f.write_text(content)
        assert SettingsStore.load(f).settings.pgn_sources == ()


def test_broken_due_date_counts_as_due_instead_of_crashing():
    tree = import_pgn_text("1. e4 e5 2. Nf3 *", side="white")[0]
    start = chess.Board().epd()
    sched = PositionScheduleStore.from_dict(
        {"cards": [{"epd": start, "due": "kaputt", "reps": 1}]})
    assert is_due(sched.card_for(start), TODAY) is True
    assert start in sched.due_positions([start], TODAY)
    assert ts.due_forecast([tree], chess.WHITE, sched, TODAY)["today"] == 1
    assert ts.due_breakdown([tree], chess.WHITE, sched, TODAY)[0]["due"] == 1
    # die nächste Wiederholung heilt die Karte
    healed = review_if_due(sched.card_for(start), True, TODAY)
    assert date.fromisoformat(healed.due) > TODAY


# --- Oberfläche: Frei durchspielen 4× am selben Tag ----------------------

def test_free_play_repeats_do_not_push_positions_weeks_away(tmp_path, monkeypatch):
    from PySide6 import QtWidgets
    import qt_app.main_window as mw
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    win = mw.MainWindow()
    tree = import_pgn_text("1. e4 c6 2. d4 d5 3. Nc3 dxe4 *", side="black")[0]
    win.tree_store.add(tree)
    board = chess.Board()
    board.push_san("e4")
    epd = board.epd()
    for _ in range(4):
        win._start_tree_drill(tree)
        for san in ("c6", "d5", "dxe4"):
            m = win._tree_trainer.board.parse_san(san)
            win._tree_drill_on_move(m.from_square, m.to_square)
    card = win.position_schedule.card_for(epd)
    assert card.interval_days == 1                       # vorher: 20 Tage
    assert "1" in win.tree_drill_feedback.text()         # Rückmeldung nennt den echten Abstand
