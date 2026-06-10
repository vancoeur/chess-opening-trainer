from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from opening_trainer.scheduler import Card, is_due, is_new, new_card


class ScheduleStore:
    """Speichert den Lernplan (Spaced Repetition) je Variante als lokales JSON.

    Schlüssel ist (Quelle, Variantenname) – identisch zur Statistik.
    """

    def __init__(self) -> None:
        self.cards: dict[tuple[str, str], Card] = {}

    def card_for(self, source_name: str, line_name: str) -> Card:
        return self.cards.get((source_name, line_name), new_card())

    def set_card(self, source_name: str, line_name: str, card: Card) -> None:
        self.cards[(source_name, line_name)] = card

    def due_lines(self, lines, today: date, new_limit: int = 10) -> list:
        """Heute zu wiederholende Linien: zuerst fällige (überfälligste zuerst),
        dann eine begrenzte Zahl neuer Linien. Nur trainierbare (mit Zügen)."""
        reviews: list[tuple[str, Any]] = []
        news: list = []
        for line in lines:
            if not getattr(line, "moves_uci", None):
                continue
            card = self.card_for(line.source_name, line.name)
            if is_new(card):
                news.append(line)
            elif is_due(card, today):
                reviews.append((card.due, line))

        reviews.sort(key=lambda item: item[0])
        ordered = [line for _, line in reviews]
        ordered.extend(news[: max(0, new_limit)])
        return ordered

    def to_dict(self) -> dict:
        return {
            "cards": [
                {
                    "source_name": source,
                    "line_name": name,
                    "interval_days": card.interval_days,
                    "ease": card.ease,
                    "due": card.due,
                    "reps": card.reps,
                    "last_reviewed": card.last_reviewed,
                }
                for (source, name), card in self.cards.items()
            ]
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScheduleStore":
        store = cls()
        for raw in data.get("cards", []):
            store.cards[(str(raw["source_name"]), str(raw["line_name"]))] = Card(
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
    def load(cls, path: str | Path) -> "ScheduleStore":
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
