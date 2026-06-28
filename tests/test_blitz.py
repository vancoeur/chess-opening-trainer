"""Blitz-Auffrischung: reiner Vorrat-Helfer ``blitz_pool`` (alle eigenen
Stellungen beider Seiten als (tree, node_id, color)). Kein Qt, keine Zeit."""
import chess

from opening_trainer.repertoire_tree import RepertoireTree, WHITE, BLACK
from opening_trainer.tree_session import blitz_pool


def _white(name="ital"):
    # 1.e4 e5 2.Nf3 Nc6 3.Bc4 — Weiß an drei eigenen Stellungen am Zug.
    t = RepertoireTree.new(name, WHITE)
    p = t.root_id
    for u in ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4"]:
        p = t.add_child(p, u).id
    return t


def _black(name="caro"):
    # 1.e4 c6 2.d4 d5 — Schwarz an zwei eigenen Stellungen am Zug.
    t = RepertoireTree.new(name, BLACK)
    p = t.root_id
    for u in ["e2e4", "c7c6", "d2d4", "d7d5"]:
        p = t.add_child(p, u).id
    return t


def test_blitz_pool_empty_without_trees():
    assert blitz_pool([], []) == []


def test_blitz_pool_collects_both_sides_with_color():
    pool = blitz_pool([_white()], [_black()])
    # 3 Weiß-Stellungen + 2 Schwarz-Stellungen.
    assert len(pool) == 5
    colors = {color for (_t, _n, color) in pool}
    assert colors == {chess.WHITE, chess.BLACK}
    # Form: (tree, node_id, color)
    tree, node_id, color = pool[0]
    assert hasattr(tree, "name") and isinstance(node_id, str)
    assert color in (chess.WHITE, chess.BLACK)


def test_blitz_pool_white_first_then_black():
    pool = blitz_pool([_white()], [_black()])
    colors = [color for (_t, _n, color) in pool]
    assert colors == [chess.WHITE, chess.WHITE, chess.WHITE, chess.BLACK, chess.BLACK]


def test_blitz_pool_dedupes_per_position():
    # Zwei Weiß-Bäume mit identischem Anfang -> gemeinsame EPDs nur einmal.
    pool = blitz_pool([_white("a"), _white("b")], [])
    # Beide Bäume haben dieselben 3 eigenen Stellungen (gleiche Zugfolge):
    # build_user_position_index dedupliziert pro EPD über beide Bäume.
    assert len(pool) == 3
