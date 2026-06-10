from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class TrainingRun:
    """Fachlogik eines Set-Trainings: eine geordnete Variantenmenge der Reihe
    nach durchgehen.

    Rein, ohne GUI und ohne Brett. Die Sitzung weiß nur, welche Variante gerade
    dran ist und zählt richtige und falsche Antworten über das ganze Set. Sie
    ist agnostisch: woher die Varianten kommen (Gruppe oder Repertoire), ist
    nicht ihre Sache.

    Analog zu WrongMoveSession, aber über Varianten statt über Fehlzüge.
    """

    lines: list[Any]
    index: int = 0
    correct: int = 0
    wrong: int = 0

    @property
    def total(self) -> int:
        return len(self.lines)

    @property
    def is_finished(self) -> bool:
        return self.index >= self.total

    def current_line(self) -> Any | None:
        """Die gerade aktive Variante, ohne weiterzuschalten."""
        if self.is_finished:
            return None
        return self.lines[self.index]

    def current_display_index(self) -> int:
        """1-basierte Nummer der aktuellen Variante für die Anzeige."""
        return min(self.index + 1, self.total)

    def advance(self) -> Any | None:
        """Zur nächsten Variante weiterschalten und sie zurückgeben.

        Gibt None zurück, wenn das Set danach erschöpft ist.
        """
        if not self.is_finished:
            self.index += 1
        return self.current_line()

    def mark_correct(self) -> None:
        self.correct += 1

    def mark_wrong(self) -> None:
        self.wrong += 1

    def progress_text(self) -> str:
        if self.total == 0:
            return "Set leer"
        if self.is_finished:
            return f"Set abgeschlossen · {self.total} Varianten · fehlerfrei {self.correct} · mit Fehler {self.wrong}"
        return (
            f"Variante {self.current_display_index()} von {self.total} · "
            f"fehlerfrei {self.correct} · mit Fehler {self.wrong}"
        )
