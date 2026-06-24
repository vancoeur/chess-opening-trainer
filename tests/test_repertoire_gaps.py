"""Lücken-Erkennung: Linien-Enden, an denen die trainierte Seite am Zug ist
(keine eigene Antwort hinterlegt). Reine Logik."""
import chess

from opening_trainer.repertoire_tree import RepertoireTree, WHITE, BLACK
from opening_trainer.tree_session import repertoire_gaps


def _black(name, ucis):
    t = RepertoireTree.new(name, BLACK)
    p = t.root_id
    for u in ucis:
        p = t.add_child(p, u).id
    return t


def test_line_ending_on_opponent_move_is_a_gap():
    # 1.e4 c6 2.d4 — Linie endet nach Weiß' Zug, Schwarz am Zug, keine Antwort.
    t = _black("caro", ["e2e4", "c7c6", "d2d4"])
    gaps = repertoire_gaps([t], chess.BLACK)
    assert len(gaps) == 1
    assert gaps[0]["tree"] is t
    assert gaps[0]["line"].endswith("d4")


def test_line_ending_on_own_move_is_not_a_gap():
    # endet nach Schwarz' Zug (…d5) -> Weiß am Zug, keine Lücke für Schwarz.
    t = _black("caro", ["e2e4", "c7c6", "d2d4", "d7d5"])
    assert repertoire_gaps([t], chess.BLACK) == []


def test_branch_with_one_missing_reply():
    # nach 1.e4 c6 2.d4 d5 verzweigt Weiß: 3.Nc3 (mit Antwort) und 3.e5 (ohne).
    t = _black("caro", ["e2e4", "c7c6", "d2d4", "d7d5"])
    d5 = t.children_of(t.children_of(t.children_of(t.children_of(t.root_id)[0].id)[0].id)[0].id)[0]
    nc3 = t.add_child(d5.id, "b1c3")
    t.add_child(nc3.id, "d5e4")          # Antwort auf 3.Nc3 vorhanden
    t.add_child(d5.id, "e4e5")           # 3.e5 ohne Antwort -> Lücke
    gaps = repertoire_gaps([t], chess.BLACK)
    lines = [g["line"] for g in gaps]
    assert any(l.endswith("e5") for l in lines)       # die e5-Lücke ist dabei
    assert not any(l.endswith("Nc3") for l in lines)  # Nc3 ist gedeckt


def test_side_filter():
    t = _black("caro", ["e2e4", "c7c6", "d2d4"])
    assert repertoire_gaps([t], chess.WHITE) == []
