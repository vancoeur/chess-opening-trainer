"""Spaced-repetition schedule keyed by POSITION (epd) instead of by line.

Same ``Card`` and ``scheduler.review`` SM-2 logic as ``schedule_store`` — only
the key changes from ``(source, line)`` to ``board.epd()``. Because transposed
positions share one epd, they share one card: drilling a position in any line
updates the same schedule entry. ``due_positions`` mirrors ``due_lines``.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from opening_trainer.scheduler import Card, is_due, is_new, new_card


class PositionScheduleStore:
    def __init__(self) -> None:
        self.cards: dict[str, Card] = {}

    def card_for(self, epd: str) -> Card:
        return self.cards.get(epd, new_card())

    def set_card(self, epd: str, card: Card) -> None:
        self.cards[epd] = card

    def due_positions(self, book, today: date, new_limit: int = 10) -> list[str]:
        """Heute fällige Stellungen (EPDs): zuerst fällige (überfälligste zuerst),
        dann eine begrenzte Zahl neuer. ``book`` ist ein iterierbares von EPDs
        (z. B. ``position_book.build_position_book(...)``)."""
        reviews: list[tuple[str, str]] = []
        news: list[str] = []
        for epd in book:
            card = self.card_for(epd)
            if is_new(card):
                news.append(epd)
            elif is_due(card, today):
                reviews.append((card.due, epd))
        reviews.sort(key=lambda item: item[0])
        ordered = [epd for _, epd in reviews]
        ordered.extend(news[: max(0, new_limit)])
        return ordered

    def to_dict(self) -> dict:
        return {
            "cards": [
                {
                    "epd": epd,
                    "interval_days": card.interval_days,
                    "ease": card.ease,
                    "due": card.due,
                    "reps": card.reps,
                    "last_reviewed": card.last_reviewed,
                }
                for epd, card in self.cards.items()
            ]
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PositionScheduleStore":
        store = cls()
        for raw in data.get("cards", []):
            store.cards[str(raw["epd"])] = Card(
                interval_days=int(raw.get("interval_days", 0)),
                ease=float(raw.get("ease", 2.5)),
                due=str(raw.get("due", "")),
                reps=int(raw.get("reps", 0)),
                last_reviewed=str(raw.get("last_reviewed", "")),
            )
        return store

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "PositionScheduleStore":
        p = Path(path)
        if not p.exists():
            return cls()
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return cls()
            return cls.from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return cls()
