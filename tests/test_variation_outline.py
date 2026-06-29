"""Namens-orientierte Baum-Übersicht: gruppiert den verschmolzenen Baum nach
benannten Varianten, je Gruppe ein verschachtelter Zug-Teilbaum. Reine Logik."""
import chess

from opening_trainer.repertoire_tree import RepertoireTree, BLACK
from opening_trainer.tree_session import variation_outline


def _black(name, ucis):
    t = RepertoireTree.new(name, BLACK)
    p = t.root_id
    for u in ucis:
        p = t.add_child(p, u).id
    return t


# Klassisch: 1.e4 c6 2.d4 d5 3.Sc3 dxe4 4.Sxe4 Lf5
KLASS = ["e2e4", "c7c6", "d2d4", "d7d5", "b1c3", "d5e4", "c3e4", "c8f5"]
# Vorstoß: 1.e4 c6 2.d4 d5 3.e5 Lf5
VORST = ["e2e4", "c7c6", "d2d4", "d7d5", "e4e5", "c8f5"]


def test_two_named_groups_in_tree_order():
    out = variation_outline([_black("Klassisch", KLASS),
                             _black("Vorstoß", VORST)], chess.BLACK)
    assert [g["name"] for g in out] == ["Klassisch", "Vorstoß"]
    assert all(g["lines"] == 1 for g in out)


def test_shared_trunk_appears_under_each_group_as_single_chain():
    out = variation_outline([_black("Klassisch", KLASS),
                             _black("Vorstoß", VORST)], chess.BLACK)
    klass = out[0]
    # Oberste Ebene = ein Knoten (gemeinsamer Stamm 1.e4), keine Verzweigung hier.
    assert len(klass["nodes"]) == 1
    assert klass["nodes"][0]["label"] == "1.e4"
    # Tiefe Kette bis zum Blatt …Bf5; Vorschau enthält den Unterscheidungszug.
    assert "3.Nc3" in klass["preview"]
    assert "3.e5" in out[1]["preview"]


def test_gap_leaf_is_flagged_and_counted():
    # Linie endet mit Weißzug (3.Sf3), Schwarz am Zug ohne Antwort -> Lücke.
    gap_line = ["e2e4", "c7c6", "d2d4", "d7d5", "g1f3"]
    out = variation_outline([_black("Lücke", gap_line)], chess.BLACK)
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
    assert leaf["label"] == "3.Nf3"          # Weißzug am Linienende


def test_group_with_two_lines_branches_and_marks_preview_cut():
    # Zwei »Klassisch«-Linien, die sich nach 4.Sxe4 trennen (…Lf5 / …Sf6).
    a = _black("Klassisch", KLASS)                              # …Lf5
    b = _black("Klassisch", KLASS[:-1] + ["g8f6"])              # …Sf6
    out = variation_outline([a, b], chess.BLACK)
    assert len(out) == 1
    g = out[0]
    assert g["lines"] == 2
    assert g["preview"].endswith("…")        # gemeinsame Vorhut gekürzt

    # Irgendwo im Baum verzweigt es in zwei Kinder (Lf5 / Sf6).
    def max_children(nodes):
        m = len(nodes)
        for n in nodes:
            m = max(m, max_children(n["children"]))
        return m
    assert max_children(g["nodes"]) >= 2


def test_user_move_flag_matches_side():
    out = variation_outline([_black("Klassisch", KLASS)], chess.BLACK)
    # Erster Knoten ist 1.e4 (Weiß) -> kein eigener Zug für Schwarz.
    first = out[0]["nodes"][0]
    assert first["is_user_move"] is False
    assert first["children"][0]["label"] == "1…c6"
    assert first["children"][0]["is_user_move"] is True
