"""PGN import preserves variations, comments and FEN-starts (vs. mainline-only loader)."""
from pathlib import Path

from opening_trainer.pgn_tree_import import import_pgn_text, import_pgn_file
from opening_trainer.pgn_loader import load_pgn_file

SAMPLE = Path(__file__).resolve().parent.parent / "assets" / "sample" / "sample_openings.pgn"

PGN_WITH_VARIATION = """[Event "Test"]

1. e4 e5 2. Nf3 {develops} (2. Bc4 {Italian} Bc5) 2... Nc6 *
"""

PGN_FEN = """[Event "Endgame"]
[SetUp "1"]
[FEN "4k3/8/8/8/8/8/4P3/4K3 w - - 0 1"]

1. e4 *
"""


def _child_by_uci(tree, node_id, uci):
    return tree.child_with_move(node_id, uci)


def test_variation_becomes_a_branch_with_two_children():
    trees = import_pgn_text(PGN_WITH_VARIATION, side="white")
    assert len(trees) == 1
    t = trees[0]
    e4 = _child_by_uci(t, t.root_id, "e2e4")
    e5 = _child_by_uci(t, e4.id, "e7e5")
    children = t.children_of(e5.id)
    assert len(children) == 2                       # Hauptlinie + Variante
    assert children[0].move_uci == "g1f3"           # variations[0] bleibt Hauptlinie
    assert children[1].move_uci == "f1c4"


def test_comments_are_preserved():
    t = import_pgn_text(PGN_WITH_VARIATION, side="white")[0]
    e4 = _child_by_uci(t, t.root_id, "e2e4")
    e5 = _child_by_uci(t, e4.id, "e7e5")
    nf3 = _child_by_uci(t, e5.id, "g1f3")
    bc4 = _child_by_uci(t, e5.id, "f1c4")
    assert nf3.comment == "develops"
    assert bc4.comment == "Italian"


def test_fen_start_is_honored():
    t = import_pgn_text(PGN_FEN, side="white")[0]
    assert t.start_fen == "4k3/8/8/8/8/8/4P3/4K3 w - - 0 1"
    assert t.children_of(t.root_id)[0].move_uci == "e2e4"


def test_sample_imports_without_mainline_loss():
    trees = import_pgn_file(SAMPLE, side="none")
    lines = load_pgn_file(SAMPLE)
    assert len(trees) == len(lines) == 3
    for tree, line in zip(trees, lines):
        # main line = always follow children_ids[0]
        main, node = [], tree.root
        while node.children_ids:
            node = tree.nodes[node.children_ids[0]]
            main.append(node.move_uci)
        assert main == line.moves_uci
