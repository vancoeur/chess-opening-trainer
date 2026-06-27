"""Linien-Katalog: leitet die »Eröffnungen«-Liste (früher ``self.lines``, separat
aus PGN geladen) aus den Repertoire-Bäumen ab — so sind die Bäume die EINZIGE
Quelle, kein paralleler PGN-Katalog mehr.

Jeder Auto-Baum (aus einer PGN-Quelle erzeugt, Marke ``headers["_auto"]=="1"``)
liefert genau einen Katalog-Eintrag: Name, Quelle, Hauptpfad-Züge und Seite —
dieselben Felder, die die Bibliothek/Partien-Auswertung/Seiten-Zuordnung früher von
einer ``OpeningLine`` gelesen haben. Editor-eigene Bäume (ohne Marke) haben kein
Linien-Pendant und bleiben außen vor (die Bibliothek zeigt sie als eigene Sektion).

Reines Modul (kein Qt), testbar.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from opening_trainer.tree_session import tree_mainline_uci

AUTO = "_auto"


@dataclass
class CatalogEntry:
    """Eine Eröffnung im Katalog — abgeleitet aus einem Auto-Baum. Bewusst OHNE
    ``id``-Feld, damit die Oberfläche sie von einem Baum unterscheidet."""

    name: str
    source_name: str
    moves_uci: list = field(default_factory=list)
    side: str = "none"           # "white" | "black" | "none"
    tree: object = None          # Rück-Verweis auf den Quell-Baum (Training/Notizen)


def build_catalog(trees) -> list:
    """Einen Katalog-Eintrag je Auto-Baum. Reihenfolge wie ``trees``."""
    entries: list = []
    for tree in trees:
        if tree.headers.get(AUTO) != "1":
            continue
        entries.append(
            CatalogEntry(
                name=tree.name,
                source_name=tree.headers.get("_source", ""),
                moves_uci=tree_mainline_uci(tree),
                side=tree.side,
                tree=tree,
            )
        )
    return entries
