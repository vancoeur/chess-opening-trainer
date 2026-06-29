"""Namens-orientierte Baum-Übersicht: gruppiert die Kapitel einer Seite nach
ihrem ECO-Eröffnungsnamen (aus den ersten ~20 Halbzügen der Hauptlinie), je
Gruppe ein verschachtelter Zug-Teilbaum. Reine Logik."""
import chess

from opening_trainer.repertoire_tree import RepertoireTree, BLACK
from opening_trainer.tree_session import variation_outline


def _u(sans):
    b = chess.Board()
    out = []
    for s in sans:
        m = b.parse_san(s)
        out.append(m.uci())
        b.push(m)
    return out


def _black(name, sans):
    t = RepertoireTree.new(name, BLACK)
    p = t.root_id
    for u in _u(sans):
        p = t.add_child(p, u).id
    return t


ADV = ["e4", "c6", "d4", "d5", "e5", "Bf5", "Nf3", "e6"]
EXCH = ["e4", "c6", "d4", "d5", "exd5", "cxd5", "Bd3"]
PANOV = ["e4", "c6", "d4", "d5", "exd5", "cxd5", "c4", "Nf6", "Nc3"]


def test_groups_use_eco_names():
    out = variation_outline([_black("Kapitel A", ADV),
                             _black("Kapitel B", EXCH)], chess.BLACK)
    names = [g["name"] for g in out]
    assert any("Advance Variation" in n for n in names)
    assert any("Exchange Variation" in n for n in names)
    # NICHT die (nichtssagenden) Kapitelnamen:
    assert "Kapitel A" not in names and "Kapitel B" not in names


def test_same_eco_name_merges_chapters():
    # Zwei Panov-Kapitel, die erst tief (nach dem benannten ECO-Punkt) abzweigen
    # -> gleicher ECO-Name -> EINE Gruppe mit zwei Linien.
    a = _black("Panov 1", PANOV + ["e6", "Nf3", "Be7"])
    b = _black("Panov 2", PANOV + ["e6", "Nf3", "Bd6"])
    out = variation_outline([a, b], chess.BLACK)
    assert len(out) == 1
    assert "Panov" in out[0]["name"]
    assert out[0]["lines"] == 2


def test_gap_leaf_is_flagged_and_counted():
    # Linie endet mit Weißzug (3.Nf3), Schwarz am Zug ohne Antwort -> Lücke.
    out = variation_outline([_black("X", ["e4", "c6", "d4", "d5", "Nf3"])], chess.BLACK)
    g = out[0]
    assert g["gaps"] == 1

    def leaves(nodes):
        for n in nodes:
            if n["children"]:
                yield from leaves(n["children"])
            else:
                yield n
    leaf = list(leaves(g["nodes"]))[-1]
    assert leaf["is_gap"] is True
    assert leaf["label"] == "3.Nf3"


def test_instructional_chapters_go_to_misc_group_last():
    out = variation_outline([
        _black("Kapitel A", ADV),
        _black("Instructive Game #2 Kasparov - Ivanchuk", PANOV),
        _black("Do's and Don'ts - Middlegame Plan #1", EXCH),
    ], chess.BLACK, misc_label="Lehrmaterial")
    names = [g["name"] for g in out]
    assert "Lehrmaterial" in names
    assert names[-1] == "Lehrmaterial"             # Sammelgruppe steht am Ende
    misc = next(g for g in out if g["name"] == "Lehrmaterial")
    assert misc["lines"] == 2                       # beide Lehr-Kapitel zusammengefasst
    # die echte Variante bleibt eigenständig
    assert any("Advance Variation" in n for n in names)


def test_user_move_flag_matches_side():
    out = variation_outline([_black("X", ADV)], chess.BLACK)
    first = out[0]["nodes"][0]
    assert first["is_user_move"] is False                  # 1.e4 (Weiß)
    assert first["children"][0]["label"] == "1…c6"
    assert first["children"][0]["is_user_move"] is True
