from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_SEP = "\t"


class LineNotes:
    """Speichert je Eröffnung (Quelle + Name) einen freien Merktext.

    Persönliche Notizen („typischer Plan: …", „Vorsicht auf f7"), lokal
    gespeichert. Leere/nur-Leerzeichen-Notizen werden entfernt statt gespeichert.
    Rein und testbar — kein UI-Bezug.
    """

    def __init__(self) -> None:
        self.notes: dict[str, str] = {}

    @staticmethod
    def _key(source_name: str, line_name: str) -> str:
        return f"{source_name}{_SEP}{line_name}"

    def note_of(self, source_name: str, line_name: str) -> str:
        """Notiztext oder leerer String, wenn keine Notiz existiert."""
        return self.notes.get(self._key(source_name, line_name), "")

    def has_note(self, source_name: str, line_name: str) -> bool:
        return bool(self.note_of(source_name, line_name))

    def set_note(self, source_name: str, line_name: str, text: str) -> None:
        """Setzt die Notiz; leerer/whitespace-Text löscht sie."""
        key = self._key(source_name, line_name)
        cleaned = (text or "").strip()
        if cleaned:
            self.notes[key] = cleaned
        else:
            self.notes.pop(key, None)

    def to_dict(self) -> dict:
        out = []
        for key, note in self.notes.items():
            source_name, line_name = key.split(_SEP, 1)
            out.append({"source_name": source_name, "line_name": line_name, "note": note})
        return {"notes": out}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LineNotes":
        store = cls()
        for raw in data.get("notes", []):
            text = str(raw.get("note", "")).strip()
            if text:
                store.notes[cls._key(str(raw["source_name"]), str(raw["line_name"]))] = text
        return store

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "LineNotes":
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
