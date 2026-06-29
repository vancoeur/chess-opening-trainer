"""Eröffnungs-Erkennung aus der Zugfolge (für Bäume mit generischen Namen)."""
import chess

from opening_trainer.opening_id import identify_opening, identify_opening_name


def _u(sans):
    b = chess.Board()
    out = []
    for s in sans:
        m = b.parse_san(s)
        out.append(m.uci())
        b.push(m)
    return out


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


def test_sicilian_variants_collapse_to_one_family():
    # Najdorf, Alapin, Drache … fangen alle mit 1.e4 c5 an -> EIN »Sizilianisch«
    assert identify_opening(["e2e4", "c7c5", "g1f3", "d7d6", "d2d4"]) == "Sizilianisch"
    assert identify_opening(["e2e4", "c7c5", "c2c3"]) == "Sizilianisch"           # Alapin
    assert identify_opening(["e2e4", "c7c5", "g1f3", "g8f6"]) == "Sizilianisch"


def test_d4_systems_by_setup():
    # London = Lf4-Aufbau, Torre = Lg5-Aufbau (zugordnungs-unabhängig, ohne frühes c4)
    assert identify_opening(["d2d4", "d7d5", "g1f3", "g8f6", "c1f4"]) == "London-System"
    assert identify_opening(["d2d4", "g8f6", "g1f3", "g7g6", "c1f4"]) == "London-System"
    assert identify_opening(["d2d4", "g8f6", "g1f3", "e7e6", "c1g5"]) == "Torre-Angriff"


def test_setup_rule_does_not_hijack_c4_openings():
    # QGD/Grünfeld (mit c4) dürfen NICHT als London/Torre gelten
    assert identify_opening(["d2d4", "d7d5", "c2c4", "e7e6"]) == "Damengambit Abgelehnt"
    assert identify_opening(["d2d4", "g8f6", "c2c4", "g7g6", "b1c3", "d7d5"]) == "Grünfeld-Verteidigung"


def test_eco_database_covers_openings_the_mini_table_lacks():
    # Diese erkennt NUR die ECO-Datenbank (nicht die kuratierte Mini-Tabelle):
    assert identify_opening(["e2e4", "e7e5", "b1c3"]) == "Wiener Partie"
    assert identify_opening(["e2e4", "e7e5", "g1f3", "b8c6", "d2d4", "e5d4", "f3d4"]) == "Schottische Partie"
    assert identify_opening(["d2d4", "d7d5", "c2c4", "c7c6"]) == "Slawische Verteidigung"


def test_unknown_returns_none():
    assert identify_opening([]) is None
    assert identify_opening(["a2a3", "a7a6"]) is None


# --- voller ECO-Eröffnungsname (Schritt 1) -------------------------------

def test_eco_name_gives_specific_variation():
    # spezifischer Varianten-Name (Doppelpunkt), nicht nur die Familie
    assert identify_opening_name(_u(["e4", "c6", "d4", "d5", "e5"])).startswith(
        "Caro-Kann Defense: Advance")
    assert identify_opening_name(
        _u(["e4", "c6", "d4", "d5", "exd5", "cxd5", "c4", "Nf6", "Nc3"])
    ) == "Caro-Kann Defense: Panov Attack"
    assert "Najdorf" in identify_opening_name(
        _u(["e4", "c5", "Nf3", "d6", "d4", "cxd4", "Nxd4", "Nf6", "Nc3", "a6"]))


def test_eco_name_prefers_named_over_bare_family():
    # Eine reine Familie (ohne Doppelpunkt) wird nur als Rückfall genommen.
    name = identify_opening_name(_u(["e4", "c6"]))
    assert name == "Caro-Kann Defense"          # nackte Familie, kein »:«-Name vorhanden


def test_eco_name_empty_returns_none():
    assert identify_opening_name([]) is None
