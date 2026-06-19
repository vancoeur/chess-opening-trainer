"""RepertoireTreeStore: save/load round-trip and corrupt-file tolerance."""
from opening_trainer.repertoire_tree import RepertoireTree, WHITE, BLACK
from opening_trainer.repertoire_tree_store import RepertoireTreeStore


def _tree(side, ucis, name):
    t = RepertoireTree.new(name, side)
    parent = t.root_id
    for uci in ucis:
        parent = t.add_child(parent, uci).id
    return t, parent  # leaf id


def test_save_load_round_trip(tmp_path):
    store = RepertoireTreeStore()
    t1, leaf1 = _tree(WHITE, ["d2d4", "d7d5", "c2c4"], "White d4")
    t2, _ = _tree(BLACK, ["e2e4", "c7c5"], "Sicilian")
    store.add(t1)
    store.add(t2)
    path = tmp_path / "repertoire_trees.json"
    store.save(path)

    loaded = RepertoireTreeStore.load(path)
    assert set(t.id for t in loaded.all()) == {t1.id, t2.id}
    assert {t.id: t.side for t in loaded.all()} == {t1.id: WHITE, t2.id: BLACK}
    assert loaded.get(t1.id).path_to(leaf1) == ["d2d4", "d7d5", "c2c4"]
    assert [t.id for t in loaded.by_side(WHITE)] == [t1.id]


def test_load_missing_file_returns_empty(tmp_path):
    assert RepertoireTreeStore.load(tmp_path / "nope.json").all() == []


def test_load_corrupt_file_returns_empty(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{ this is not valid json", encoding="utf-8")
    assert RepertoireTreeStore.load(path).all() == []
