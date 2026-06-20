"""A daily 'due positions' session across the whole tree repertoire.

Maps each of the trained side's positions (epd) to one place in the trees where it
occurs, then asks the per-position schedule which are due today. Transpositions
share one epd → one card, so the same position isn't reviewed twice in a day.
Pure (no UI); the UI starts a ``PositionTrainer`` at each returned (tree, node).
"""
from __future__ import annotations

from opening_trainer.position_book import _start_board, _legal_move, _SIDE_NAME


def build_user_position_index(trees, side) -> dict[str, tuple]:
    """epd -> (tree, node_id) für die erste eigene Stellung (Nutzer am Zug, mit
    vorgesehenem Zug), die diese EPD erreicht. Nur Bäume der passenden Seite."""
    index: dict[str, tuple] = {}
    want = _SIDE_NAME.get(side)
    for tree in trees:
        if tree.side != want:
            continue
        _walk(tree, tree.root, _start_board(tree), side, index)
    return index


def _walk(tree, node, board, side, index) -> None:
    children = tree.children_of(node.id)
    if board.turn == side and children:
        index.setdefault(board.epd(), (tree, node.id))   # erste Fundstelle gewinnt
    for child in children:
        move = _legal_move(board, child.move_uci)
        if move is None:
            continue
        board.push(move)
        _walk(tree, child, board, side, index)
        board.pop()


def due_drill_items(trees, side, schedule, today, new_limit: int = 10) -> list[tuple]:
    """Heute fällige eigene Stellungen als (tree, node_id), in Lernplan-Reihenfolge
    (überfälligste zuerst, dann begrenzt neue)."""
    index = build_user_position_index(trees, side)
    due_epds = schedule.due_positions(list(index.keys()), today, new_limit=new_limit)
    return [index[epd] for epd in due_epds]
