"""Import PGN into repertoire trees — preserving variations and comments.

Unlike ``pgn_loader`` (which keeps only ``mainline_moves``), this traverses the
full python-chess game tree via ``node.variations``, so every branch becomes a
tree branch (``variations[0]`` stays the main line) and ``node.comment`` is kept.
"""
from __future__ import annotations

from pathlib import Path

import chess.pgn

from opening_trainer.pgn_loader import _build_name, _read_games_from_text
from opening_trainer.repertoire_tree import RepertoireTree


def _mainline_san(game: chess.pgn.Game) -> list[str]:
    board = game.board()
    sans: list[str] = []
    for move in game.mainline_moves():
        sans.append(board.san(move))
        board.push(move)
    return sans


def _add_variations(tree: RepertoireTree, pgn_node: chess.pgn.GameNode, tree_node_id: str) -> None:
    for variation in pgn_node.variations:        # [0] = Hauptlinie, dann Nebenvarianten
        move = variation.move
        if move is None:
            continue
        child = tree.add_child(tree_node_id, move.uci(), comment=(variation.comment or "").strip())
        _add_variations(tree, variation, child.id)


def tree_from_game(game: chess.pgn.Game, side: str) -> RepertoireTree:
    headers = {str(k): str(v) for k, v in game.headers.items()}
    name = _build_name(headers, _mainline_san(game), None)
    start_fen = headers.get("FEN") or None
    tree = RepertoireTree.new(name=name, side=side, start_fen=start_fen)
    tree.headers = headers
    _add_variations(tree, game, tree.root_id)
    return tree


def import_pgn_text(pgn_text: str, side: str = "none") -> list[RepertoireTree]:
    """Ein Baum pro Spiel im PGN-Text (Varianten erhalten)."""
    return [tree_from_game(game, side) for game in _read_games_from_text(pgn_text)]


def import_pgn_file(path: str | Path, side: str = "none") -> list[RepertoireTree]:
    p = Path(path)
    return import_pgn_text(p.read_text(encoding="utf-8-sig"), side=side)
