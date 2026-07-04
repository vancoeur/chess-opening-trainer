"""A5-Regression: PGN-Import/Export erhalten Zug-Symbole (NAGs) und den Kapitel-
Intro-Kommentar (vor dem 1. Zug); NAGs überleben auch Speichern/Laden."""
from opening_trainer.pgn_tree_import import import_pgn_text
from opening_trainer.pgn_tree_export import export_trees
from opening_trainer.repertoire_tree import RepertoireTree


def test_nag_and_root_comment_roundtrip():
    pgn = "{ Kapitel-Intro } 1. e4 $1 { guter Zug } e5 2. Nf3 *\n"
    trees = import_pgn_text(pgn, side="white")
    t = trees[0]
    assert t.root.comment == "Kapitel-Intro"                 # Intro übernommen
    e4 = t.child_with_move(t.root_id, "e2e4")
    assert 1 in e4.nags                                      # $1 (=!) erhalten

    out = export_trees(trees)
    assert "$1" in out and "Kapitel-Intro" in out            # beides zurückgeschrieben

    t2 = import_pgn_text(out, side="white")[0]               # Re-Import
    assert t2.root.comment == "Kapitel-Intro"
    assert 1 in t2.child_with_move(t2.root_id, "e2e4").nags


def test_nags_persist_through_dict():
    t = RepertoireTree.new("X", "white")
    t.add_child(t.root_id, "e2e4", nags=[1, 3])
    t2 = RepertoireTree.from_dict(t.to_dict())
    assert t2.child_with_move(t2.root_id, "e2e4").nags == [1, 3]


def test_no_nags_stay_absent():
    # Ohne NAGs bleibt das Feld leer und bläht die JSON nicht auf.
    t = RepertoireTree.new("X", "white")
    t.add_child(t.root_id, "e2e4")
    d = t.to_dict()
    move_node = next(n for n in d["nodes"] if n.get("move_uci") == "e2e4")
    assert "nags" not in move_node
