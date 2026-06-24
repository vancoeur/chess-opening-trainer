"""Cutover Scheibe 4: Stellung/Linie -> Baum auflösen.

``locate_position`` (EPD -> (tree, node)) und ``tree_for_moves`` (Linie -> Baum)
lenken die alten linearen „Diese Linie üben"-Sprünge auf den Baum-Drill um.
Kein Qt.
"""
import chess

from opening_trainer.repertoire_tree import RepertoireTree, WHITE, BLACK
from opening_trainer.tree_session import (
    build_user_position_index, locate_position, tree_for_moves,
)


def _white(name, ucis):
    t = RepertoireTree.new(name, WHITE)
    p = t.root_id
    for u in ucis:
        p = t.add_child(p, u).id
    return t


def _black(name, ucis):
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


def test_locate_position_hits_and_misses():
    t = _white("ital", ["e2e4", "e7e5", "g1f3"])
    index = build_user_position_index([t], chess.WHITE)
    hit = locate_position(index, _epd(["e2e4", "e7e5"]))
    assert hit is not None and hit[0] is t
    assert locate_position(index, _epd(["d2d4"])) is None


def test_tree_for_moves_white_line():
    # Beide Weiß-Bäume teilen die Startstellung -> Auflösung muss über den
    # Baum-Pfad gehen, nicht über die (geteilte) erste Stellung.
    a = _white("ital", ["e2e4", "e7e5", "g1f3"])
    b = _white("queens", ["d2d4", "d7d5", "c2c4"])
    assert tree_for_moves([a, b], ["e2e4", "e7e5", "g1f3"], chess.WHITE) is a
    assert tree_for_moves([a, b], ["d2d4", "d7d5", "c2c4"], chess.WHITE) is b


def test_tree_for_moves_black_line():
    caro = _black("caro", ["e2e4", "c7c6", "d2d4", "d7d5"])
    assert tree_for_moves([caro], ["e2e4", "c7c6", "d2d4", "d7d5"], chess.BLACK) is caro
    assert tree_for_moves([caro], ["e2e4", "c7c6", "d2d4", "d7d5"], chess.WHITE) is None


def test_tree_for_moves_unknown_returns_none():
    t = _white("ital", ["e2e4", "e7e5", "g1f3"])
    assert tree_for_moves([t], ["g1f3", "g8f6"], chess.WHITE) is None
    assert tree_for_moves([t], [], chess.WHITE) is None
