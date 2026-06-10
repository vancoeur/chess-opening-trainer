from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from opening_trainer.repertoire import LineKey, Repertoire, RepertoireCategory


class RepertoireStore:
    """Speichert Repertoire-Kategorien als lokales JSON."""

    def __init__(self, repertoire: Repertoire | None = None) -> None:
        self.repertoire = repertoire or Repertoire()

    def to_dict(self) -> dict:
        categories = []
        for category in self.repertoire.categories:
            entry: dict[str, Any] = {
                "name": category.name,
                "line_keys": [
                    {
                        "source_name": key.source_name,
                        "line_name": key.line_name,
                    }
                    for key in category.line_keys
                ],
            }
            if category.side:
                entry["side"] = category.side
            categories.append(entry)
        return {"categories": categories}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RepertoireStore":
        categories: list[RepertoireCategory] = []

        for raw_category in data.get("categories", []):
            line_keys = [
                LineKey(
                    source_name=str(raw_key["source_name"]),
                    line_name=str(raw_key["line_name"]),
                )
                for raw_key in raw_category.get("line_keys", [])
            ]
            categories.append(
                RepertoireCategory(
                    name=str(raw_category["name"]),
                    line_keys=line_keys,
                    side=str(raw_category.get("side", "")),
                )
            )

        return cls(Repertoire(categories=categories))

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: str | Path) -> "RepertoireStore":
        p = Path(path)
        if not p.exists():
            return cls()

        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return cls()
            return cls.from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError):
            return cls()
