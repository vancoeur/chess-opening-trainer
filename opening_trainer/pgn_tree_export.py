"""Export repertoire trees back to PGN — preserving variations and comments.

Walks the tree depth-first; ``children_of`` yields the main line first, so it
lands in ``variations[0]`` and round-trips cleanly. NB: a fresh string per game
(``str(game)``) avoids the StringExporter accumulation pitfall.
"""
from __future__ import annotations

import chess
import chess.pgn

from opening_trainer.repertoire_tree import RepertoireTree


def _build(pgn_node: chess.pgn.GameNode, tree: RepertoireTree, tree_node) -> None:
    for child in tree.children_of(tree_node.id):
        if not child.move_uci:
            continue
        move = chess.Move.from_uci(child.move_uci)
        new_node = pgn_node.add_variation(move, comment=child.comment or "")
        _build(new_node, tree, child)


def tree_to_game(tree: RepertoireTree) -> chess.pgn.Game:
    game = chess.pgn.Game()
    if tree.start_fen:
        game.setup(chess.Board(tree.start_fen))
    for key, value in tree.headers.items():
        game.headers[key] = value
    _build(game, tree, tree.root)
    return game


def export_trees(trees: list[RepertoireTree]) -> str:
    """PGN-Text aller Bäume (ein Spiel je Baum)."""
    return "\n\n".join(str(tree_to_game(tree)) for tree in trees) + ("\n" if trees else "")
