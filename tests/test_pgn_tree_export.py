"""PGN export round-trips: import -> export -> re-import is structurally equal."""
from opening_trainer.pgn_tree_import import import_pgn_text
from opening_trainer.pgn_tree_export import export_trees, tree_to_game

PGN = """[Event "Round trip"]

1. d4 d5 2. c4 e6 (2... c6 {Slav} 3. Nf3) 3. Nc3 {QGD} Nf6 *
"""


def _signature(tree, node=None):
    """Ordered (move, comment, [children]) signature — captures shape + comments."""
    node = node or tree.root
    return (
        node.move_uci,
        node.comment,
        [_signature(tree, tree.nodes[c]) for c in node.children_ids],
    )


def test_round_trip_preserves_structure_and_comments():
    trees = import_pgn_text(PGN, side="white")
    pgn_out = export_trees(trees)
    reimported = import_pgn_text(pgn_out, side="white")

    assert len(reimported) == len(trees) == 1
    assert _signature(reimported[0]) == _signature(trees[0])


def test_export_contains_variation_and_comment():
    trees = import_pgn_text(PGN, side="white")
    out = export_trees(trees)
    assert "Slav" in out and "QGD" in out      # comments survive
    assert "c6" in out                          # the variation move is present


def test_exported_game_has_headers():
    tree = import_pgn_text(PGN, side="white")[0]
    game = tree_to_game(tree)
    assert game.headers["Event"] == "Round trip"
