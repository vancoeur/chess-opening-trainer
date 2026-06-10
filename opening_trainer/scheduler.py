from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, timedelta


DEFAULT_EASE = 2.5
MIN_EASE = 1.3


@dataclass(frozen=True)
class Card:
    """Lern-Zustand einer Karte (hier: einer Variante) für Spaced Repetition.

    ``due`` leer bedeutet: noch nie terminiert (neue Karte). Reine Daten – die
    Terminierung übernimmt ``review``; das aktuelle Datum wird stets von außen
    übergeben (testbar, kein verstecktes „heute").
    """

    interval_days: int = 0
    ease: float = DEFAULT_EASE
    due: str = ""
    reps: int = 0
    last_reviewed: str = ""


def new_card() -> Card:
    return Card()


def is_new(card: Card) -> bool:
    return not card.due


def is_due(card: Card, today: date) -> bool:
    """Ist die Karte fällig? Neue (noch nie terminierte) Karten gelten nicht als
    fällig – sie werden über das Tageslimit für Neues eingeführt."""
    if not card.due:
        return False
    return date.fromisoformat(card.due) <= today


def review(card: Card, passed: bool, today: date) -> Card:
    """Terminiert eine Karte nach der Wiederholung neu.

    bestanden:      reps 0 -> 1 Tag, reps 1 -> 3 Tage, danach Intervall * ease.
    nicht bestanden: zurück auf kurz (heute wieder fällig), Leichtigkeit sinkt.
    """
    if passed:
        if card.reps == 0:
            interval = 1
        elif card.reps == 1:
            interval = 3
        else:
            interval = max(1, round(card.interval_days * card.ease))
        ease = card.ease
        reps = card.reps + 1
    else:
        interval = 0
        ease = max(MIN_EASE, round(card.ease - 0.2, 2))
        reps = 0

    due = (today + timedelta(days=interval)).isoformat()
    return replace(
        card,
        interval_days=interval,
        ease=ease,
        due=due,
        reps=reps,
        last_reviewed=today.isoformat(),
    )
