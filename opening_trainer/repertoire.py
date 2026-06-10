from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


# Seite, der eine thematische Gruppe zugeordnet ist. Eine Gruppe gehört zu
# genau einer Seite oder (noch) zu keiner.
SIDE_NONE = ""
SIDE_WHITE = "white"
SIDE_BLACK = "black"
VALID_SIDES = (SIDE_NONE, SIDE_WHITE, SIDE_BLACK)


@dataclass(frozen=True)
class LineKey:
    source_name: str
    line_name: str

    @classmethod
    def from_line(cls, line) -> "LineKey":
        return cls(source_name=line.source_name, line_name=line.name)


@dataclass
class RepertoireCategory:
    name: str
    line_keys: list[LineKey] = field(default_factory=list)
    side: str = SIDE_NONE

    def contains(self, line) -> bool:
        return LineKey.from_line(line) in self.line_keys

    def add_line(self, line) -> bool:
        key = LineKey.from_line(line)
        if key in self.line_keys:
            return False

        self.line_keys.append(key)
        return True

    def remove_line(self, line) -> bool:
        key = LineKey.from_line(line)
        if key not in self.line_keys:
            return False

        self.line_keys.remove(key)
        return True


@dataclass
class Repertoire:
    categories: list[RepertoireCategory] = field(default_factory=list)

    def category(self, name: str) -> RepertoireCategory | None:
        return next((category for category in self.categories if category.name == name), None)

    def category_names(self) -> list[str]:
        return [category.name for category in self.categories]

    def lines_for_category(self, name: str, lines: Iterable) -> list:
        category = self.category(name)
        if category is None:
            return []

        return [line for line in lines if category.contains(line)]

    def rename_category(self, old_name: str, new_name: str) -> bool:
        category = self.category(old_name)
        if category is None or self.category(new_name) is not None:
            return False

        category.name = new_name
        return True

    def delete_category(self, name: str) -> bool:
        category = self.category(name)
        if category is None:
            return False

        self.categories.remove(category)
        return True

    def add_line_to_category(self, name: str, line) -> bool:
        category = self.category(name)
        if category is None:
            return False

        return category.add_line(line)

    def remove_line_from_category(self, name: str, line) -> bool:
        category = self.category(name)
        if category is None:
            return False

        return category.remove_line(line)

    def set_category_side(self, name: str, side: str) -> bool:
        """Ordnet eine Gruppe einer Seite zu (Weiß/Schwarz) oder hebt die
        Zuordnung auf (SIDE_NONE). Gibt False bei unbekannter Gruppe oder
        ungültiger Seite zurück."""
        if side not in VALID_SIDES:
            return False

        category = self.category(name)
        if category is None:
            return False

        category.side = side
        return True

    def categories_for_side(self, side: str) -> list[RepertoireCategory]:
        return [category for category in self.categories if category.side == side]

    def category_summaries_for_side(self, side: str) -> list[tuple[str, int]]:
        """(Gruppenname, Anzahl zugeordneter Varianten) je Gruppe einer Seite,
        in vorhandener Reihenfolge. Für die Repertoire-Anzeige."""
        return [
            (category.name, len(category.line_keys))
            for category in self.categories
            if category.side == side
        ]

    def lines_for_side(self, side: str, lines: Iterable) -> list:
        """Alle Linien des Repertoires einer Seite: Vereinigung der Linien
        aller Gruppen dieser Seite, dedupliziert, in der Reihenfolge von
        ``lines``. Eine leere Seite ergibt eine leere Liste."""
        if side not in (SIDE_WHITE, SIDE_BLACK):
            return []

        relevant = self.categories_for_side(side)
        return [line for line in lines if any(category.contains(line) for category in relevant)]
