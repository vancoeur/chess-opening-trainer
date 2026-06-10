from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence


def same_wrong_move_problem(left: Any, right: Any) -> bool:
    """Vergleicht zwei zusammengefasste Fehlzugprobleme.

    Ein Fehlzugproblem ist durch Stellung, erwarteten Zug und gespielten
    falschen Zug bestimmt. Die historische Häufigkeit gehört nicht zur
    Identität des Problems.
    """

    return (
        getattr(left, "fen_before", None) == getattr(right, "fen_before", None)
        and getattr(left, "expected_san", None) == getattr(right, "expected_san", None)
        and getattr(left, "played_san", None) == getattr(right, "played_san", None)
    )


def session_index_for_selected_problem(session_positions: Sequence[Any], selected_position: Any) -> int | None:
    """Findet die Sitzungsposition eines ausgewählten Fehlzugproblems.

    Die Sitzung bleibt eine Liste von Fehlzugproblemen. Ein Problem mit count=3
    zählt hier weiterhin als genau eine Sitzungsaufgabe.
    """

    for index, position in enumerate(session_positions):
        if same_wrong_move_problem(position, selected_position):
            return index

    return None

def wrong_move_history_text(error_position: Any) -> str:
    count = getattr(error_position, "wrong_count", getattr(error_position, "count", 0))
    if count == 1:
        return "früher 1× aufgetreten"
    return f"früher {count}× aufgetreten"


def loaded_session_message(index: int, total: int, history: str, correct: int, wrong: int) -> str:
    return (
        f"Fehlzugproblem {index} von {total} geladen · "
        f"{history} · Sitzung: richtig {correct} · falsch {wrong}."
    )


def solved_session_message(index: int, total: int, history: str, correct: int, wrong: int) -> str:
    if index >= total:
        return (
            f"Letztes Fehlzugproblem gelöst · {history} · "
            f"Sitzung: richtig {correct} · falsch {wrong}."
        )

    return (
        f"Fehlzugproblem {index} von {total} gelöst · "
        f"{history} · Sitzung: richtig {correct} · falsch {wrong}. "
        f"Weiter mit „Nächstes Fehlzugproblem“."
    )


def finished_session_message(total: int, correct: int, wrong: int) -> str:
    return f"Fehlzug-Sitzung abgeschlossen: {total} Fehlzugprobleme · richtig {correct} · falsch {wrong}."


def session_mode_text(mode_value: str, index: int, total: int, correct: int, wrong: int) -> str:
    """Modus-Zeile während einer laufenden Fehlzug-Sitzung.

    Zeigt den Sitzungsfortschritt dauerhaft an, unabhängig vom
    überschreibbaren Statustext.
    """
    return (
        f"Modus: {mode_value} · Fehlzugproblem {index} von {total} · "
        f"richtig {correct} · falsch {wrong}"
    )

@dataclass
class WrongMoveSession:
    """Fachlogik einer Fehlzug-Sitzung.

    Eine Sitzung besteht aus Fehlzugproblemen, nicht aus historischen
    Fehlerereignissen. Ein Problem mit count=3 bleibt daher eine einzige
    Sitzungsaufgabe.
    """

    positions: list[Any]
    index: int = 0
    correct: int = 0
    wrong: int = 0

    @property
    def total(self) -> int:
        return len(self.positions)

    @property
    def is_finished(self) -> bool:
        return self.index >= self.total

    def current_display_index(self) -> int:
        return min(self.index + 1, self.total)

    def next_problem(self) -> Any | None:
        if self.is_finished:
            return None

        problem = self.positions[self.index]
        self.index += 1
        return problem

    def mark_correct(self) -> None:
        self.correct += 1

    def mark_wrong(self) -> None:
        self.wrong += 1

