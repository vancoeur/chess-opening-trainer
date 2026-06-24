"""Cutover Scheibe 1: positions-basierte Statistik/Fortschritt.

Reine Helfer in ``tree_session`` (``tree_progress_rows``, ``open_error_positions``)
plus die FEN-genaue ``stats_store.error_positions_for_epd`` — die Ablösung der
linien-basierten Fortschritts-/Fehlerzeilen. Kein Qt.
"""
import chess

from opening_trainer.repertoire_tree import RepertoireTree, WHITE, BLACK
from opening_trainer.stats_store import StatsStore
from opening_trainer.tree_session import tree_progress_rows, open_error_positions


def _white_tree(name="ital"):
    # 1.e4 e5 2.Nf3 Nc6 3.Bc4 — Weiß am Zug an drei eigenen Stellungen.
    t = RepertoireTree.new(name, WHITE)
    p = t.root_id
    for u in ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4"]:
        p = t.add_child(p, u).id
    return t


def _fen(ucis):
    b = chess.Board()
    for u in ucis:
        b.push(chess.Move.from_uci(u))
    return b.fen()


def _add(store, ucis, expected_san, played_san, correct):
    """Ein Trainingsereignis an der Stellung nach ``ucis`` (Seite am Zug)."""
    store.add_event(
        source_name="s", line_name="l", fen_before=_fen(ucis),
        expected_san=expected_san, played_san=played_san, correct=correct,
    )


# --- tree_progress_rows ---------------------------------------------------

def test_progress_row_untrained_is_all_zero():
    t = _white_tree()
    rows = tree_progress_rows([t], chess.WHITE, StatsStore())
    assert len(rows) == 1
    r = rows[0]
    assert r["name"] == "ital"
    assert r["attempts"] == 0
    assert r["accuracy"] == 0.0
    assert r["positions_total"] == 3        # nach Start, nach 1.e4 e5, nach 2.Nf3 Nc6
    assert r["positions_trained"] == 0


def test_progress_row_aggregates_positions():
    t = _white_tree()
    store = StatsStore()
    _add(store, ["e2e4", "e7e5"], "Nf3", "Nf3", True)            # Treffer
    _add(store, ["e2e4", "e7e5", "g1f3", "b8c6"], "Bc4", "Bb5", False)  # Fehler
    rows = tree_progress_rows([t], chess.WHITE, store)
    r = rows[0]
    assert r["attempts"] == 2
    assert r["accuracy"] == 0.5
    assert r["positions_trained"] == 2


def test_progress_skips_other_side_and_empty_trees():
    white = _white_tree()
    assert tree_progress_rows([white], chess.BLACK, StatsStore()) == []
    empty = RepertoireTree.new("leer", WHITE)        # nur Wurzel, keine eigene Stellung
    assert tree_progress_rows([empty], chess.WHITE, StatsStore()) == []


# --- open_error_positions -------------------------------------------------

def test_open_error_surfaces_then_clears():
    t = _white_tree()
    store = StatsStore()
    _add(store, ["e2e4", "e7e5"], "Nf3", "Bc4", False)          # offener Fehler
    probs = open_error_positions([t], chess.WHITE, store)
    assert len(probs) == 1
    p = probs[0]
    assert p["expected_san"] == "Nf3"
    assert p["expected_uci"] == "g1f3"
    assert p["played"] == "Bc4"
    assert p["name"] == "ital"
    assert p["count"] == 1

    _add(store, ["e2e4", "e7e5"], "Nf3", "Nf3", True)           # ausgebügelt
    assert open_error_positions([t], chess.WHITE, store) == []


def test_open_error_ignores_other_side():
    t = _white_tree()
    store = StatsStore()
    _add(store, ["e2e4", "e7e5"], "Nf3", "Bc4", False)
    assert open_error_positions([t], chess.BLACK, store) == []
