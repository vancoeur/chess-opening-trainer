"""Erkennt die Eröffnung aus der Zugfolge (UCI) — damit Bäume aus PGNs mit
nichtssagenden Kapitelnamen (»Chapter #24«) trotzdem einen echten Namen
bekommen. Reine, kuratierte Tabelle der gängigen Eröffnungen; längster
passender Zug-Präfix gewinnt. Keine Abhängigkeiten, offline.

Bewusst kompakt (deckt das übliche Repertoire ab, nicht jede ECO-Nebenlinie).
Eine vollständige ECO-Datenbank ließe sich später als Datendatei nachrüsten.
"""
from __future__ import annotations

# (Zug-Präfix in UCI) -> Name. Reihenfolge egal; der längste Treffer gewinnt.
_OPENINGS: list[tuple[list[str], str]] = [
    # --- 1.e4 ---
    (["e2e4", "c7c6"], "Caro-Kann"),
    (["e2e4", "c7c5"], "Sizilianisch"),
    (["e2e4", "e7e6"], "Französisch"),
    (["e2e4", "d7d5"], "Skandinavisch"),
    (["e2e4", "d7d6"], "Pirc-Verteidigung"),
    (["e2e4", "g7g6"], "Moderne Verteidigung"),
    (["e2e4", "g8f6"], "Aljechin-Verteidigung"),
    (["e2e4", "e7e5"], "Offene Spiele"),
    (["e2e4", "e7e5", "g1f3", "g8f6"], "Russische Verteidigung (Petrow)"),
    (["e2e4", "e7e5", "f2f4"], "Königsgambit"),
    (["e2e4", "e7e5", "b1c3"], "Wiener Partie"),
    (["e2e4", "e7e5", "g1f3", "b8c6", "f1b5"], "Ruy López"),
    (["e2e4", "e7e5", "g1f3", "b8c6", "f1c4"], "Italienisch"),
    (["e2e4", "e7e5", "g1f3", "b8c6", "d2d4"], "Schottische Partie"),
    (["e2e4", "e7e5", "g1f3", "b8c6", "b1c3"], "Vier-Springer"),
    # --- 1.d4 ---
    (["d2d4", "d7d5"], "Damengambit"),
    (["d2d4", "d7d5", "c2c4", "c7c6"], "Slawische Verteidigung"),
    (["d2d4", "d7d5", "c2c4", "e7e6"], "Damengambit Abgelehnt"),
    (["d2d4", "d7d5", "c2c4", "d5c4"], "Damengambit Angenommen"),
    (["d2d4", "d7d5", "c2c4", "e7e6", "b1c3", "g8f6", "g1f3", "c7c6"], "Semi-Slawisch"),
    (["d2d4", "f7f5"], "Holländisch"),
    (["d2d4", "g8f6"], "Indische Verteidigung"),
    (["d2d4", "g8f6", "c2c4", "e7e6", "b1c3", "f8b4"], "Nimzo-Indisch"),
    (["d2d4", "g8f6", "c2c4", "e7e6", "g1f3", "f8b4"], "Bogo-Indisch"),
    (["d2d4", "g8f6", "c2c4", "e7e6", "g1f3", "b7b6"], "Damenindisch"),
    (["d2d4", "g8f6", "c2c4", "e7e6", "g2g3"], "Katalanisch"),
    (["d2d4", "g8f6", "c2c4", "g7g6", "b1c3", "d7d5"], "Grünfeld-Verteidigung"),
    (["d2d4", "g8f6", "c2c4", "g7g6", "b1c3", "f8g7"], "Königsindisch"),
    (["d2d4", "g8f6", "c2c4", "e7e5"], "Budapester Gambit"),
    (["d2d4", "g8f6", "c2c4", "c7c5", "d4d5", "b7b5"], "Benko-Gambit"),
    (["d2d4", "g8f6", "c2c4", "c7c5", "d4d5", "e7e6"], "Benoni"),
    # --- andere erste Züge ---
    (["c2c4"], "Englische Eröffnung"),
    (["g1f3"], "Réti-Eröffnung"),
    (["g2g3"], "Königsfianchetto"),
    (["b2b3"], "Larsen-Eröffnung"),
    (["f2f4"], "Bird-Eröffnung"),
]


def identify_opening(moves_uci) -> str | None:
    """Name der Eröffnung für eine Zugfolge, sonst ``None``.

    Zuerst Weiß-AUFBAU-Systeme nach 1.d4 (London/Torre — definiert durch den
    Läuferzug, nicht durch eine feste Zugfolge), dann längster passender Präfix.
    """
    if not moves_uci:
        return None
    moves = list(moves_uci)
    # 1.d4-Aufbausysteme ohne frühes c4 (zugordnungs-unabhängig am Läufer erkannt).
    if moves[:1] == ["d2d4"] and "c2c4" not in moves[:6]:
        head = moves[:6]
        if "c1f4" in head:
            return "London-System"
        if "c1g5" in head and "g1f3" in head:
            return "Torre-Angriff"
    best_name = None
    best_len = 0
    for seq, name in _OPENINGS:
        n = len(seq)
        if n > best_len and n <= len(moves) and moves[:n] == seq:
            best_name, best_len = name, n
    return best_name
