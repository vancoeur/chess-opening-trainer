"""Pure repertoire-tree operations: add/delete/promote, path, id stability, round-trip."""
import pytest

from opening_trainer.repertoire_tree import RepertoireTree, RepertoireNode, WHITE


def _linear(tree, ucis):
    """Append a linear sequence of UCI moves from the root; return the leaf node."""
    parent = tree.root_id
    node = tree.root
    for uci in ucis:
        node = tree.add_child(parent, uci)
        parent = node.id
    return node


def test_new_tree_has_only_root():
    t = RepertoireTree.new("Test", WHITE)
    assert t.side == WHITE
    assert t.root.move_uci is None
    assert t.root.parent_id is None
    assert list(t.iter_nodes()) == [t.root]


def test_add_child_dedupes_same_move():
    t = RepertoireTree.new()
    a = t.add_child(t.root_id, "e2e4")
    b = t.add_child(t.root_id, "e2e4")        # gleicher Zug -> selber Knoten
    assert a.id == b.id
    assert t.root.children_ids == [a.id]
    c = t.add_child(t.root_id, "d2d4")        # anderer Zug -> neuer Knoten
    assert c.id != a.id
    assert t.root.children_ids == [a.id, c.id]


def test_path_to_returns_moves_from_root():
    t = RepertoireTree.new()
    leaf = _linear(t, ["e2e4", "e7e5", "g1f3"])
    assert t.path_to(leaf.id) == ["e2e4", "e7e5", "g1f3"]
    assert t.path_to(t.root_id) == []


def test_promote_moves_node_to_main_line():
    t = RepertoireTree.new()
    main = t.add_child(t.root_id, "e2e4")
    side = t.add_child(t.root_id, "d2d4")
    assert t.root.children_ids == [main.id, side.id]
    t.promote(side.id)
    assert t.root.children_ids == [side.id, main.id]


def test_delete_subtree_removes_node_and_descendants():
    t = RepertoireTree.new()
    main = t.add_child(t.root_id, "e2e4")
    var = t.add_child(t.root_id, "d2d4")
    deep = t.add_child(var.id, "d7d5")
    assert deep.id in t.nodes
    t.delete_subtree(var.id)
    assert var.id not in t.nodes
    assert deep.id not in t.nodes
    assert t.root.children_ids == [main.id]


def test_cannot_delete_root():
    t = RepertoireTree.new()
    with pytest.raises(ValueError):
        t.delete_subtree(t.root_id)


def test_node_ids_are_stable_across_edits():
    t = RepertoireTree.new()
    a = t.add_child(t.root_id, "e2e4")
    b = t.add_child(t.root_id, "d2d4")
    a_id = a.id
    t.promote(b.id)                  # reorder
    t.add_child(a.id, "e7e5")        # add elsewhere
    assert a.id == a_id              # id survived structural edits
    assert t.nodes[a_id] is a


def test_round_trip_to_dict_from_dict():
    t = RepertoireTree.new("My White", WHITE)
    leaf = _linear(t, ["d2d4", "d7d5", "c2c4"])
    t.nodes[leaf.id].comment = "Damengambit"
    t.headers = {"ECO": "D06"}
    restored = RepertoireTree.from_dict(t.to_dict())
    assert restored.id == t.id
    assert restored.name == t.name
    assert restored.side == t.side
    assert restored.root_id == t.root_id
    assert restored.headers == {"ECO": "D06"}
    assert set(restored.nodes) == set(t.nodes)
    assert restored.path_to(leaf.id) == ["d2d4", "d7d5", "c2c4"]
    assert restored.nodes[leaf.id].comment == "Damengambit"
