"""Erkennt die Eröffnung aus der Zugfolge (UCI) und ordnet sie einer **deutschen
Familie** zu — damit Bäume aus PGNs mit uneinheitlichen/nichtssagenden
Kapitelnamen trotzdem sauber und reload-stabil gruppiert werden.

Vorgehen (robust, near-vollständig):
1. Weiß-AUFBAU-Systeme nach 1.d4 (London = Lf4, Torre = Lg5) — am Läufer erkannt,
   zugordnungs-unabhängig (ECO würde sie in »Damengambit/Indisch« einschmelzen).
2. Längster passender Zug-Präfix in der gemeinfreien **ECO-Datenbank**
   (lichess-org/chess-openings, CC0; gebündelt als data/eco_openings.tsv) → ECO-Code
   → deutsche Familie über ein Bereichs-Mapping (B20–B99 → »Sizilianisch« usw.).
3. Rückfall: kleine kuratierte Tabelle (falls die Datenbank fehlt/nicht greift).

Keine Netz-/Laufzeitabhängigkeit; die Datendatei wird mitgeliefert.
"""
from __future__ import annotations

import os
import sys

# --- kuratierte Mini-Tabelle (Rückfall) ----------------------------------
_OPENINGS: list[tuple[list[str], str]] = [
    (["e2e4", "c7c6"], "Caro-Kann"),
    (["e2e4", "c7c5"], "Sizilianisch"),
    (["e2e4", "e7e6"], "Französisch"),
    (["e2e4", "d7d5"], "Skandinavisch"),
    (["e2e4", "d7d6"], "Pirc-Verteidigung"),
    (["e2e4", "g7g6"], "Moderne Verteidigung"),
    (["e2e4", "g8f6"], "Aljechin-Verteidigung"),
    (["e2e4", "e7e5"], "Offene Spiele"),
    (["d2d4", "d7d5"], "Damengambit"),
    (["d2d4", "f7f5"], "Holländisch"),
    (["d2d4", "g8f6"], "Indische Verteidigung"),
    (["c2c4"], "Englische Eröffnung"),
    (["g1f3"], "Réti-Eröffnung"),
    (["g2g3"], "Königsfianchetto"),
    (["b2b3"], "Larsen-Eröffnung"),
    (["f2f4"], "Bird-Eröffnung"),
]


def _eco_to_family(eco: str) -> str | None:
    """ECO-Code (z. B. »B90«) → deutsche Eröffnungs-Familie (Bereichs-Mapping)."""
    if not eco or len(eco) < 3:
        return None
    L = eco[0]
    try:
        n = int(eco[1:3])
    except ValueError:
        return None
    if L == "A":
        if 2 <= n <= 3: return "Bird-Eröffnung"
        if 4 <= n <= 9: return "Réti-Eröffnung"
        if 10 <= n <= 39: return "Englische Eröffnung"
        if 56 <= n <= 56: return "Benoni"
        if 57 <= n <= 59: return "Benko-Gambit"
        if 60 <= n <= 79: return "Benoni"
        if 80 <= n <= 99: return "Holländisch"
        if 40 <= n <= 55: return "Indische Verteidigung"
        return None
    if L == "B":
        if n == 1: return "Skandinavisch"
        if 2 <= n <= 5: return "Aljechin-Verteidigung"
        if n == 6: return "Moderne Verteidigung"
        if 7 <= n <= 9: return "Pirc-Verteidigung"
        if 10 <= n <= 19: return "Caro-Kann"
        if 20 <= n <= 99: return "Sizilianisch"
        return None
    if L == "C":
        if 0 <= n <= 19: return "Französisch"
        if 23 <= n <= 29: return "Wiener Partie"
        if 30 <= n <= 39: return "Königsgambit"
        if n == 41: return "Philidor-Verteidigung"
        if 42 <= n <= 43: return "Russische Verteidigung (Petrow)"
        if n == 45: return "Schottische Partie"
        if 46 <= n <= 49: return "Vier-Springer"
        if 50 <= n <= 59: return "Italienisch"
        if 60 <= n <= 99: return "Ruy López"
        return None
    if L == "D":
        if 10 <= n <= 19: return "Slawische Verteidigung"
        if 20 <= n <= 29: return "Damengambit Angenommen"
        if 43 <= n <= 49: return "Semi-Slawisch"
        if 70 <= n <= 99: return "Grünfeld-Verteidigung"
        if 30 <= n <= 69: return "Damengambit Abgelehnt"
        if 0 <= n <= 9: return "Damengambit"
        return None
    if L == "E":
        if 0 <= n <= 9: return "Katalanisch"
        if 10 <= n <= 19: return "Damenindisch"
        if 20 <= n <= 59: return "Nimzo-Indisch"
        if 60 <= n <= 99: return "Königsindisch"
        return None
    return None


# --- ECO-Datenbank: uci-Tuple -> (ECO-Code, Name) (lazy geladen, gecacht) ---
_ECO: dict[tuple, tuple[str, str]] | None = None

# Standardtiefe für die Namens-Erkennung: ein Kapitel wird über die ersten ~20
# Halbzüge seiner Hauptlinie identifiziert (tiefe Sub-Sub-Varianten zählen nicht).
ECO_NAME_MAXPLY = 20


def _data_file() -> str | None:
    base = getattr(sys, "_MEIPASS", None)
    cands = []
    if base:
        cands.append(os.path.join(base, "opening_trainer", "data", "eco_openings.tsv"))
    cands.append(os.path.join(os.path.dirname(__file__), "data", "eco_openings.tsv"))
    for p in cands:
        if os.path.exists(p):
            return p
    return None


def _eco_table() -> dict[tuple, tuple[str, str]]:
    global _ECO
    if _ECO is None:
        _ECO = {}
        path = _data_file()
        if path:
            try:
                with open(path, encoding="utf-8") as fh:
                    for ln in fh:
                        parts = ln.rstrip("\n").split("\t")
                        if len(parts) >= 3:                 # eco, name, uci
                            eco, name, uci = parts[0], parts[1], parts[2]
                        elif len(parts) == 2:               # alt: eco, uci (ohne Name)
                            eco, name, uci = parts[0], "", parts[1]
                        else:
                            continue
                        uci = uci.strip()
                        if uci:
                            _ECO[tuple(uci.split())] = (eco, name)
            except OSError:
                pass
    return _ECO


def identify_opening(moves_uci) -> str | None:
    """Deutsche Eröffnungs-Familie für eine Zugfolge, sonst ``None``."""
    if not moves_uci:
        return None
    moves = list(moves_uci)
    # 1) Weiß-Aufbausysteme nach 1.d4 ohne frühes c4 (am Läufer erkannt).
    if moves[:1] == ["d2d4"] and "c2c4" not in moves[:6]:
        head = moves[:6]
        if "c1f4" in head:
            return "London-System"
        if "c1g5" in head and "g1f3" in head:
            return "Torre-Angriff"
    # 2) ECO-Datenbank: längster passender Zug-Präfix -> Code -> Familie.
    table = _eco_table()
    if table:
        for k in range(len(moves), 0, -1):
            entry = table.get(tuple(moves[:k]))
            if entry:
                fam = _eco_to_family(entry[0])
                if fam:
                    return fam
                break
    # 3) Rückfall: kuratierte Mini-Tabelle.
    best_name, best_len = None, 0
    for seq, name in _OPENINGS:
        n = len(seq)
        if n > best_len and n <= len(moves) and moves[:n] == seq:
            best_name, best_len = name, n
    return best_name


def identify_opening_name(moves_uci, maxply: int = ECO_NAME_MAXPLY) -> str | None:
    """Voller **ECO-Eröffnungsname** für eine Zugfolge (z. B. »Caro-Kann Defense:
    Advance Variation«), sonst ``None``.

    Genommen wird der TIEFSTE benannte ECO-Eintrag innerhalb der ersten
    ``maxply`` Halbzüge — bevorzugt einer mit echtem Varianten-Namen
    (Doppelpunkt), damit eine Linie ihren spezifischen Namen bekommt und nicht
    nur die nackte Familie. Reine Funktion (Datenbank wird gecacht)."""
    if not moves_uci:
        return None
    moves = list(moves_uci)[:maxply]
    table = _eco_table()
    if not table:
        return None
    fallback = None
    for k in range(len(moves), 0, -1):
        entry = table.get(tuple(moves[:k]))
        if not entry:
            continue
        name = entry[1].strip()
        if not name:
            continue
        if ":" in name:                 # echter Varianten-Name -> sofort nehmen
            return name
        if fallback is None:            # nackte Familie -> nur als Rückfall merken
            fallback = name
    return fallback
