from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Seiten-Werte
WHITE = "white"
BLACK = "black"
NONE = "none"
_VALID = {WHITE, BLACK, NONE}

_SEP = "\t"

# Schlüsselwörter im Dateinamen, aus denen sich die Spielerfarbe ableiten lässt.
_WHITE_HINTS = ("weiss", "weiß", "white")
_BLACK_HINTS = ("schwarz", "black")


def side_from_name(name: str) -> str | None:
    """Rät die Spielerfarbe (Repertoire-Seite) aus einem Datei-/Quellnamen.

    Gibt WHITE oder BLACK zurück, wenn der Name EINDEUTIG auf eine Farbe deutet
    (z. B. »Weiss London.pgn« → WHITE, »Schwarz Pirc.pgn« → BLACK). Bei keinem
    oder mehrdeutigem Treffer (beide Farben im Namen) → None, damit nie heimlich
    falsch geraten wird."""
    low = str(name).lower()
    has_white = any(h in low for h in _WHITE_HINTS)
    has_black = any(h in low for h in _BLACK_HINTS)
    if has_white and not has_black:
        return WHITE
    if has_black and not has_white:
        return BLACK
    return None


class OpeningSides:
    """Speichert je Eröffnung (Quelle + Name) die Repertoire-Seite direkt:
    Weiß, Schwarz oder bewusst keine. Einfaches Pro-Eröffnung-Modell für die
    Qt-App. Rein und testbar.
    """

    def __init__(self) -> None:
        self.sides: dict[str, str] = {}

    @staticmethod
    def _key(source_name: str, line_name: str) -> str:
        return f"{source_name}{_SEP}{line_name}"

    def side_of(self, source_name: str, line_name: str) -> str | None:
        """Zugeordnete Seite oder None, wenn keine Zuordnung existiert.
        Eine bewusste „keine" wird als NONE gespeichert und auch so zurückgegeben."""
        return self.sides.get(self._key(source_name, line_name))

    def set_side(self, source_name: str, line_name: str, side: str) -> None:
        if side not in _VALID:
            raise ValueError(f"ungültige Seite: {side!r}")
        self.sides[self._key(source_name, line_name)] = side

    def to_dict(self) -> dict:
        out = []
        for key, side in self.sides.items():
            source_name, line_name = key.split(_SEP, 1)
            out.append({"source_name": source_name, "line_name": line_name, "side": side})
        return {"sides": out}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OpeningSides":
        store = cls()
        for raw in data.get("sides", []):
            side = str(raw.get("side", ""))
            if side in _VALID:
                store.sides[cls._key(str(raw["source_name"]), str(raw["line_name"]))] = side
        return store

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "OpeningSides":
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
