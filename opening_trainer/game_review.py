"""Pure comparison of played games against one's own repertoire.

For each game it finds the first point where the player made a *different* move
than their repertoire prescribes in that position. Engine-/UI-/network-free and
therefore testable. Reading the PGN (headers, main line) is done by the UI.

Position key = ``board.epd()`` (pieces, side to move, castling, en passant —
without move counters), so transpositions yield the same key.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import chess


@dataclass
class Deviation:
    ply: int                  # 0-basierter Halbzug, an dem abgewichen wurde
    move_number: int          # menschliche Zugnummer
    played_san: str           # was gespielt wurde
    expected_sans: list[str]  # was das Repertoire hier vorsieht


@dataclass
class GameReview:
    status: str                       # "deviated" | "followed" | "out_of_book"
    deviation: Deviation | None = None
    booked_plies: int = 0             # wie viele eigene Züge im Repertoire lagen


def build_repertoire_book(lines_moves: list[list[str]], side: chess.Color) -> dict[str, set[str]]:
    """Baut aus den Repertoire-Linien einer Seite ein Buch:
    Stellungs-Schlüssel (vor einem eigenen Zug) -> Menge der vorgesehenen Züge (SAN)."""
    book: dict[str, set[str]] = defaultdict(set)
    for moves in lines_moves:
        board = chess.Board()
        for uci in moves:
            try:
                move = chess.Move.from_uci(uci)
            except ValueError:
                break
            if move not in board.legal_moves:
                break
            if board.turn == side:
                book[board.epd()].add(board.san(move))
            board.push(move)
    return dict(book)


def review_game(moves_uci: list[str], book: dict[str, set[str]], side: chess.Color) -> GameReview:
    """Prüft eine Partie gegen das Repertoire-Buch der gespielten Seite."""
    board = chess.Board()
    booked = 0
    for ply, uci in enumerate(moves_uci):
        try:
            move = chess.Move.from_uci(uci)
        except ValueError:
            break
        if move not in board.legal_moves:
            break
        if board.turn == side:
            key = board.epd()
            booked_moves = book.get(key)
            if booked_moves is None:
                # Eigene Stellung, aber nicht im Repertoire abgedeckt.
                if booked == 0:
                    return GameReview("out_of_book", None, 0)
                return GameReview("followed", None, booked)
            played = board.san(move)
            if played not in booked_moves:
                return GameReview(
                    "deviated",
                    Deviation(ply, board.fullmove_number, played, sorted(booked_moves)),
                    booked,
                )
            booked += 1
        board.push(move)
    return GameReview("followed", None, booked)
