"""Position book: per-position prescribed moves, transposition merging, side filter."""
import chess

from opening_trainer.repertoire_tree import RepertoireTree, WHITE, BLACK
from opening_trainer.position_book import build_position_book, position_key


def _tree(side, ucis, name="t"):
    """A linear tree of the given side from a list of UCI moves."""
    t = RepertoireTree.new(name, side)
    parent = t.root_id
    for uci in ucis:
        parent = t.add_child(parent, uci).id
    return t


def _epd_after(ucis):
    b = chess.Board()
    for uci in ucis:
        b.push(chess.Move.from_uci(uci))
    return b.epd()


def test_two_prescribed_moves_at_one_position():
    t = RepertoireTree.new("two firsts", WHITE)
    t.add_child(t.root_id, "e2e4")
    t.add_child(t.root_id, "d2d4")
    book = build_position_book([t], chess.WHITE)
    start = chess.Board().epd()
    assert start in book
    assert set(book[start].moves) == {"e2e4", "d2d4"}
    assert book[start].moves["e2e4"] == "e4"


def test_transposition_merges_into_one_entry():
    # 1.d4 Nf6 2.c4 e6 (white to move)  ==  1.c4 e6 2.d4 Nf6 (white to move)
    a = _tree(WHITE, ["d2d4", "g8f6", "c2c4", "e7e6", "b1c3"], "A")
    b = _tree(WHITE, ["c2c4", "e7e6", "d2d4", "g8f6", "g1f3"], "B")
    book = build_position_book([a, b], chess.WHITE)

    key = _epd_after(["d2d4", "g8f6", "c2c4", "e7e6"])
    assert key == _epd_after(["c2c4", "e7e6", "d2d4", "g8f6"])  # truly a transposition
    assert key in book
    # Both repertoires' white moves at this shared position merged into one entry:
    assert set(book[key].moves) == {"b1c3", "g1f3"}
    assert book[key].node_ids["b1c3"]  # node id(s) recorded


def test_side_filter_excludes_other_side_trees():
    black_tree = _tree(BLACK, ["e2e4", "c7c5"], "Sicilian")  # black repertoire
    white_book = build_position_book([black_tree], chess.WHITE)
    assert white_book == {}
    black_book = build_position_book([black_tree], chess.BLACK)
    # black's prescribed move (…c5) is recorded at the position after 1.e4:
    key = _epd_after(["e2e4"])
    assert key in black_book
    assert set(black_book[key].moves) == {"c7c5"}


def test_position_key_is_epd():
    b = chess.Board()
    assert position_key(b) == b.epd()
