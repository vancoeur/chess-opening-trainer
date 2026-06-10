"""Pure parsing of the Lichess opening-explorer response (no network).

The HTTP request itself is done by the Qt UI (QNetworkAccessManager). Here the
already-loaded JSON structure is only turned into handy objects — so this part
stays testable without internet.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExplorerMove:
    san: str
    uci: str
    white: int   # Partien, die Weiß gewann
    draws: int
    black: int

    @property
    def total(self) -> int:
        return self.white + self.draws + self.black


@dataclass
class ExplorerResult:
    white: int
    draws: int
    black: int
    opening_name: str | None = None
    moves: list[ExplorerMove] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.white + self.draws + self.black


def percent(part: int, whole: int) -> int:
    """Gerundeter Prozentanteil; 0, wenn ``whole`` 0 ist."""
    if whole <= 0:
        return 0
    return round(100 * part / whole)


def _as_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def parse_explorer_response(data: dict) -> ExplorerResult:
    """Übersetzt die JSON-Antwort des Lichess-Explorers in ein ExplorerResult."""
    moves = []
    for m in (data.get("moves") or []):
        moves.append(
            ExplorerMove(
                san=str(m.get("san", "")),
                uci=str(m.get("uci", "")),
                white=_as_int(m.get("white", 0)),
                draws=_as_int(m.get("draws", 0)),
                black=_as_int(m.get("black", 0)),
            )
        )
    opening = data.get("opening")
    opening_name = opening.get("name") if isinstance(opening, dict) else None
    return ExplorerResult(
        white=_as_int(data.get("white", 0)),
        draws=_as_int(data.get("draws", 0)),
        black=_as_int(data.get("black", 0)),
        opening_name=opening_name,
        moves=moves,
    )
