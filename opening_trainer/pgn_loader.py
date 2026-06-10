from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any

import chess.pgn
import logging

logging.getLogger("chess.pgn").disabled = True


@dataclass(frozen=True)
class OpeningLine:
    """Eine trainierbare PGN-Variante."""

    name: str
    headers: dict[str, str]
    moves_uci: list[str]
    moves_san: list[str]
    source_name: str = ""


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _first_moves_name(moves_san: list[str], max_plies: int = 8) -> str:
    if not moves_san:
        return "Variante ohne Züge"

    parts: list[str] = []
    move_no = 1
    for index, san in enumerate(moves_san[:max_plies]):
        if index % 2 == 0:
            parts.append(f"{move_no}.{san}")
        else:
            parts.append(san)
            move_no += 1
    return " ".join(parts)


def _build_name(headers: dict[str, str], moves_san: list[str], common_event: str | None) -> str:
    chapter = _clean(headers.get("ChapterName"))
    if chapter:
        return chapter

    event = _clean(headers.get("Event"))
    if event and event != common_event:
        return event

    eco = _clean(headers.get("ECO"))
    opening = _clean(headers.get("Opening"))
    variation = _clean(headers.get("Variation"))

    if eco and opening and variation:
        return f"{eco} · {opening}: {variation}"
    if opening and variation:
        return f"{opening}: {variation}"
    if eco and opening:
        return f"{eco} · {opening}"
    if opening:
        return opening

    white = _clean(headers.get("White"))
    black = _clean(headers.get("Black"))
    if white and black and white != "?" and black != "?":
        return f"{white} – {black}"

    return _first_moves_name(moves_san)


def _read_games_from_text(pgn_text: str) -> list[chess.pgn.Game]:
    games: list[chess.pgn.Game] = []
    stream = StringIO(pgn_text)

    while True:
        game = chess.pgn.read_game(stream)
        if game is None:
            break
        games.append(game)

    return games


def load_pgn_text(pgn_text: str, source_name: str = "") -> list[OpeningLine]:
    """Liest PGN-Text und erzeugt trainierbare Varianten."""

    games = _read_games_from_text(pgn_text)
    if not games:
        return []

    events = [_clean(game.headers.get("Event")) for game in games]
    non_empty_events = [event for event in events if event]
    common_event = non_empty_events[0] if non_empty_events and all(e == non_empty_events[0] for e in non_empty_events) else None

    lines: list[OpeningLine] = []

    for game in games:
        board = game.board()
        moves_uci: list[str] = []
        moves_san: list[str] = []

        for move in game.mainline_moves():
            san = board.san(move)
            moves_san.append(san)
            moves_uci.append(move.uci())
            board.push(move)

        headers = {str(k): str(v) for k, v in game.headers.items()}
        name = _build_name(headers, moves_san, common_event)

        lines.append(
            OpeningLine(
                name=name,
                headers=headers,
                moves_uci=moves_uci,
                moves_san=moves_san,
                source_name=source_name,
            )
        )

    return lines


def load_pgn_file(path: str | Path) -> list[OpeningLine]:
    p = Path(path)
    text = p.read_text(encoding="utf-8-sig")
    return load_pgn_text(text, source_name=p.name)


def load_pgn_folder(path: str | Path) -> list[OpeningLine]:
    """Liest alle .pgn-Dateien eines Ordners und gibt eine gemeinsame Variantenliste zurück.

    Die Dateien werden alphabetisch sortiert geladen, damit die Reihenfolge stabil bleibt.
    Unterordner werden in Version 1.0 noch nicht durchsucht.
    """

    folder = Path(path)
    if not folder.is_dir():
        raise NotADirectoryError(f"Kein Ordner: {folder}")

    lines: list[OpeningLine] = []

    for pgn_file in sorted(folder.glob("*.pgn")):
        file_lines = load_pgn_file(pgn_file)
        lines.extend(file_lines)

    return lines
