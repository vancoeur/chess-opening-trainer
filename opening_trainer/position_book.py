"""Derived runtime index over repertoire trees: position key -> prescribed moves.

The tree (``repertoire_tree``) is the source of truth; this book answers the
per-position training question — "in THIS position (my turn), what is my
repertoire move?" — in O(1). The position key is ``board.epd()`` (pieces, side
to move, castling, en passant; no move counters), exactly like
``game_review.build_repertoire_book``. Identical positions reached from different
trees or branches — transpositions — therefore MERGE into one entry. This is the
foundation of per-position (Chessable-style) training.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import chess

from opening_trainer.repertoire_tree import RepertoireTree, WHITE, BLACK

_SIDE_NAME = {chess.WHITE: WHITE, chess.BLACK: BLACK}


def position_key(board: chess.Board) -> str:
    """Transpositions-sicherer Stellungs-Schlüssel."""
    return board.epd()


@dataclass
class PositionEntry:
    epd: str
    side_to_move: bool                                         # chess.WHITE / chess.BLACK
    moves: dict[str, str] = field(default_factory=dict)        # uci -> san (vorgesehene eigene Züge)
    node_ids: dict[str, set[str]] = field(default_factory=dict)  # uci -> {Knoten-ID, ...} (auch über Bäume hinweg)


def _start_board(tree: RepertoireTree) -> chess.Board:
    return chess.Board(tree.start_fen) if tree.start_fen else chess.Board()


def build_position_book(trees: list[RepertoireTree], side: chess.Color) -> dict[str, PositionEntry]:
    """Baut das Stellungs-Buch der trainierten Seite aus ihren Bäumen.

    Nur Bäume genau dieser Seite zählen. An jeder Stellung, in der die trainierte
    Seite am Zug ist, werden die Kinder (= ihre vorgesehenen Züge) eingetragen.
    Gleiche EPDs verschmelzen automatisch zu einem Eintrag.
    """
    book: dict[str, PositionEntry] = {}
    want = _SIDE_NAME.get(side)
    for tree in trees:
        if tree.side != want:
            continue
        _walk(tree, tree.root, _start_board(tree), side, book)
    return book


def build_san_book(trees: list[RepertoireTree], side: chess.Color) -> dict[str, set[str]]:
    """Wie ``game_review.build_repertoire_book``, aber aus den Repertoire-Bäumen
    statt aus linearen Hauptlinien: varianten-bewusst und transpositions-
    verschmelzend. Stellungs-EPD -> Menge der vorgesehenen eigenen Züge (SAN).

    Direkt als ``book`` für ``game_review.review_game`` verwendbar. Dadurch wird
    eine korrekt gespielte Nebenvariante nicht mehr als Abweichung gemeldet."""
    return {
        epd: set(entry.moves.values())
        for epd, entry in build_position_book(trees, side).items()
    }


def _legal_move(board: chess.Board, move_uci: str | None) -> chess.Move | None:
    if not move_uci:
        return None
    try:
        move = chess.Move.from_uci(move_uci)
    except ValueError:
        return None
    return move if move in board.legal_moves else None


def _walk(tree, node, board: chess.Board, side: chess.Color, book: dict) -> None:
    children = tree.children_of(node.id)
    if board.turn == side and children:
        epd = board.epd()
        entry = book.get(epd)
        if entry is None:
            entry = PositionEntry(epd, side)
            book[epd] = entry
        for child in children:
            move = _legal_move(board, child.move_uci)
            if move is None:
                continue
            entry.moves[child.move_uci] = board.san(move)
            entry.node_ids.setdefault(child.move_uci, set()).add(child.id)
    for child in children:
        move = _legal_move(board, child.move_uci)
        if move is None:
            continue
        board.push(move)
        _walk(tree, child, board, side, book)
        board.pop()
