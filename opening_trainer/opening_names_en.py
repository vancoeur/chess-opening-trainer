"""Heuristic English translation of German opening names (for display).

The opening names come from the PGN files (data, in German). For English mode,
``to_english`` replaces the typical German chess terms with their English ones;
proper nouns (Najdorf, Caro-Kann, Rubinstein …) stay. This is deliberately
heuristic — but usually hits the common English name.

Terms are applied longest-first, so longer/compound forms are replaced before
their shorter parts (e.g. ``Englischer`` before ``Englische`` before
``Englisch``) — this avoids ending collisions.
"""
from __future__ import annotations

import re

_TERMS: dict[str, str] = {
    # zusammengesetzte
    "Zwei-Springer-Verteidigung": "Two Knights Defence",
    "Vier-Bauern-Angriff": "Four Pawns Attack",
    "Grünfeld-Verteidigung": "Grünfeld Defence",
    "Pirc-Verteidigung": "Pirc Defence",
    "Aljechin-Verteidigung": "Alekhine Defence",
    "Vorstossvariante": "Advance Variation",
    "Vorstoßvariante": "Advance Variation",
    "Abtauschvariante": "Exchange Variation",
    "Austauschvariante": "Exchange Variation",
    "Hauptvariante": "Main Variation",
    "Hauptlinie": "Main Line",
    "Hauptaufbau": "Main Setup",
    "Tauschangriff": "Exchange Variation",
    "Anti-Benoni-Setup": "Anti-Benoni Setup",
    "Vier-Springer": "Four Knights",
    "Zwei-Springer": "Two Knights",
    "Vier-Bauern": "Four Pawns",
    "Damen-Gambit": "Queen's Gambit",
    "Damengambit": "Queen's Gambit",
    "Königsgambit": "King's Gambit",
    "Königsindisch": "King's Indian",
    "Damenindisch": "Queen's Indian",
    "Nimzo-Indisch": "Nimzo-Indian",
    "Bogo-Indisch": "Bogo-Indian",
    "Grünfeld-Indisch": "Grünfeld",
    "Semi-Slawisch": "Semi-Slav",
    "Anti-Englisch": "Anti-English",
    "Antikatalanisch": "Anti-Catalan",
    # Eigenschaftswörter (alle Endungen; Länge sortiert sie korrekt)
    "Skandinavische": "Scandinavian", "Skandinavisch": "Scandinavian",
    "Sizilianische": "Sicilian", "Sizilianisch": "Sicilian",
    "Italienisches": "Italian", "Italienische": "Italian", "Italienisch": "Italian",
    "Französische": "French", "Französisch": "French",
    "Franzoesische": "French", "Franzoesisch": "French",
    "Spanisches": "Spanish", "Spanische": "Spanish", "Spanisch": "Spanish",
    "Russische": "Russian", "Russisch": "Russian",
    "Englisches": "English", "Englischer": "English", "Englische": "English", "Englisch": "English",
    "Holländische": "Dutch", "Holländisch": "Dutch",
    "Slawische": "Slav", "Slawisch": "Slav",
    "Katalanische": "Catalan", "Katalanisch": "Catalan",
    "Portugiesische": "Portuguese", "Portugiesisch": "Portuguese",
    "Ungarische": "Hungarian", "Ungarisch": "Hungarian",
    "Schottisches": "Scotch", "Schottische": "Scotch", "Schottisch": "Scotch",
    "Klassisches": "Classical", "Klassische": "Classical", "Klassisch": "Classical",
    "klassisches": "Classical", "klassische": "Classical", "klassisch": "Classical",
    "Geschlossenes": "Closed", "Geschlossene": "Closed", "Geschlossen": "Closed",
    "Richtung": "towards",
    "Symmetrisches": "Symmetrical", "Symmetrische": "Symmetrical", "Symmetrisch": "Symmetrical",
    "Österreichischer": "Austrian", "Österreichische": "Austrian",
    "Beschleunigte": "Accelerated",
    "Verbesserte": "Improved",
    "Moderne": "Modern",
    # Demonyme
    "Berliner": "Berlin",
    "Wiener": "Vienna",
    "Leningrader": "Leningrad",
    "Aljechin": "Alekhine",
    # Begriffe (mit Bindestrich-Variante für sauberere Namen)
    "-Verteidigung": " Defence",
    "-Variante": " Variation",
    "-Angriff": " Attack",
    "Verteidigung": "Defence",
    "Ablehnung": "Declined",
    "Abwehr": "Defence",
    "Variante": "Variation",
    "Angriff": "Attack",
    "Eröffnung": "Opening",
    "Partie": "Game",
    "Aufbau": "Setup",
    "angenommen": "Accepted", "Angenommen": "Accepted",
    "abgelehnt": "Declined", "Abgelehnt": "Declined",
    "Austausch": "Exchange", "Abtausch": "Exchange",
    "Vorstoss": "Advance", "Vorstoß": "Advance",
}

# nach Länge absteigend: längere Begriffe zuerst ersetzen
_ORDERED = sorted(_TERMS.items(), key=lambda kv: -len(kv[0]))

# kurze Wörter nur als ganzes Wort
_WORD_TERMS = [("gegen", "vs"), ("mit", "with"), ("und", "and")]


def to_english(name: str) -> str:
    """Übersetzt die deutschen Schachbegriffe in einem Eröffnungsnamen ins Englische."""
    out = name
    for de, en in _ORDERED:
        out = out.replace(de, en)
    for de, en in _WORD_TERMS:
        out = re.sub(rf"\b{re.escape(de)}\b", en, out)
    return out
