"""Eröffnungs-Erkennung aus der Zugfolge (für Bäume mit generischen Namen)."""
from opening_trainer.opening_id import identify_opening


def test_recognizes_common_openings():
    assert identify_opening(["e2e4", "c7c6", "d2d4", "d7d5"]) == "Caro-Kann"
    assert identify_opening(["e2e4", "c7c5"]) == "Sizilianisch"
    assert identify_opening(["e2e4", "e7e6"]) == "Französisch"
    assert identify_opening(["c2c4", "e7e5"]) == "Englische Eröffnung"


def test_longest_prefix_wins():
    # 1.e4 e5 allein -> Offene Spiele; mit 3.Lb5 -> Ruy López (spezifischer)
    assert identify_opening(["e2e4", "e7e5"]) == "Offene Spiele"
    assert identify_opening(["e2e4", "e7e5", "g1f3", "b8c6", "f1b5", "a7a6"]) == "Ruy López"
    assert identify_opening(["e2e4", "e7e5", "g1f3", "b8c6", "f1c4"]) == "Italienisch"


def test_d4_indian_systems():
    assert identify_opening(["d2d4", "g8f6", "c2c4", "g7g6", "b1c3", "d7d5"]) == "Grünfeld-Verteidigung"
    assert identify_opening(["d2d4", "g8f6", "c2c4", "g7g6", "b1c3", "f8g7"]) == "Königsindisch"
    assert identify_opening(["d2d4", "g8f6", "c2c4", "e7e6", "b1c3", "f8b4"]) == "Nimzo-Indisch"
    # nur 1.d4 Sf6 -> grob „Indische Verteidigung"
    assert identify_opening(["d2d4", "g8f6"]) == "Indische Verteidigung"


def test_unknown_returns_none():
    assert identify_opening([]) is None
    assert identify_opening(["a2a3", "a7a6"]) is None
