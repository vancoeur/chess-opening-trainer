"""Stockfish integration for the repertoire check.

Finds the Stockfish executable on the machine and evaluates positions. The
*judgement* logic (blunder/inaccuracy) is kept separate in
``opening_trainer/engine_review.py`` and is testable there without an engine.
"""
from __future__ import annotations

import os
import shutil
import stat
from pathlib import Path

import chess
import chess.engine

from opening_trainer.engine_review import MoveIssue, classify_loss, judge_deviation
from qt_app.paths import bundled_stockfish

# Übliche Orte, an denen Stockfish liegt (Homebrew, manuelle Installation).
_CANDIDATES = [
    "/opt/homebrew/bin/stockfish",
    "/usr/local/bin/stockfish",
    "/usr/bin/stockfish",
    "/opt/local/bin/stockfish",
]


def _ensure_executable(path: Path) -> None:
    """Stellt sicher, dass die Datei ausführbar ist (das Verpacken kann das
    Ausführbar-Bit verlieren)."""
    try:
        mode = path.stat().st_mode
        path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except OSError:
        pass


def find_stockfish() -> Path | None:
    """Sucht die Stockfish-Programmdatei.

    Zuerst die mit der App ausgelieferte Datei (damit es auch ohne Homebrew
    läuft), dann eine System-Installation. Gibt ``None`` zurück, wenn keine
    gefunden wird.
    """
    bundled = bundled_stockfish()
    if bundled is not None:
        _ensure_executable(bundled)
        return bundled
    found = shutil.which("stockfish")
    if found:
        return Path(found)
    for cand in _CANDIDATES:
        if Path(cand).exists():
            return Path(cand)
    return None


# Mate-Bewertungen auf eine große Zahl abbilden, damit sie als Centibauern rechnen.
_MATE_CP = 10000


def _cp(score: chess.engine.PovScore, side: chess.Color) -> int:
    return score.pov(side).score(mate_score=_MATE_CP)


def judge_user_move(
    engine: chess.engine.SimpleEngine,
    fen_before: str,
    expected_san: str,
    played_uci: str,
    limit: chess.engine.Limit,
) -> dict | None:
    """Beurteilt einen vom Repertoire abweichenden Zug beim Üben.

    Vergleicht die Stellung nach dem gespielten Zug mit der nach dem
    Repertoire-Zug (beide aus Sicht des Ziehenden) und stuft ein:
    gleichwertig / ungenau / fehler. Gibt ``None`` zurück, wenn die Züge
    nicht deutbar sind.
    """
    board = chess.Board(fen_before)
    side = board.turn
    try:
        expected_move = board.parse_san(expected_san)
        played_move = chess.Move.from_uci(played_uci)
    except (ValueError, chess.InvalidMoveError):
        return None
    if expected_move not in board.legal_moves or played_move not in board.legal_moves:
        return None

    def eval_after(move: chess.Move) -> int:
        b = board.copy()
        b.push(move)
        return _cp(engine.analyse(b, limit)["score"], side)

    expected_cp = eval_after(expected_move)
    played_cp = eval_after(played_move)
    loss = expected_cp - played_cp
    return {
        "category": judge_deviation(loss, played_cp),
        "loss_cp": loss,
        "eval_after_cp": played_cp,
        "expected_san": expected_san,
    }


def review_line(
    engine: chess.engine.SimpleEngine,
    moves_uci: list[str],
    side: chess.Color,
    limit: chess.engine.Limit,
) -> list[MoveIssue]:
    """Prüft EINE Linie und meldet verdächtige Züge *der eigenen Seite*.

    Für jeden Halbzug, in dem ``side`` am Zug ist, vergleicht die Funktion den
    gespielten Zug mit Stockfishs Lieblingszug. Reicht der Unterschied an
    ``classify_loss`` als Patzer/Ungenauigkeit durch, landet er in der Liste.
    """
    issues: list[MoveIssue] = []
    board = chess.Board()
    for ply, uci in enumerate(moves_uci):
        try:
            move = chess.Move.from_uci(uci)
        except ValueError:
            break
        if move not in board.legal_moves:
            break  # defekte Linie — nicht weiter prüfen
        if board.turn == side:
            best_info = engine.analyse(board, limit)
            best_move = best_info["pv"][0]
            best_cp = _cp(best_info["score"], side)
            played_info = engine.analyse(board, limit, root_moves=[move])
            played_cp = _cp(played_info["score"], side)
            loss = best_cp - played_cp
            severity = classify_loss(loss, played_cp)
            if severity and move != best_move:
                issues.append(
                    MoveIssue(
                        ply=ply,
                        move_number=board.fullmove_number,
                        san=board.san(move),
                        best_san=board.san(best_move),
                        loss_cp=loss,
                        eval_after_cp=played_cp,
                        severity=severity,
                    )
                )
        board.push(move)
    return issues
