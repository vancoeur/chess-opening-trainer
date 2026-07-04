"""E2/E3-Regression: Speichern ist atomar (ein abgebrochener Schreibvorgang lässt die
alte Datei unversehrt) und strukturell kaputte Bäume werden beim Laden übersprungen
statt klaglos zu laden und später abzustürzen."""
import json

import pytest

from opening_trainer.atomic_io import atomic_write_text
from opening_trainer.repertoire_tree import RepertoireTree
from opening_trainer.repertoire_tree_store import RepertoireTreeStore


def test_atomic_write_leaves_original_on_failure(tmp_path, monkeypatch):
    p = tmp_path / "data.json"
    p.write_text('{"gut": 1}', encoding="utf-8")

    # os.replace mittendrin scheitern lassen (simuliert Absturz vor dem Austausch)
    import opening_trainer.atomic_io as aio

    def boom(src, dst):
        raise OSError("Schreibfehler")

    monkeypatch.setattr(aio.os, "replace", boom)
    with pytest.raises(OSError):
        atomic_write_text(p, '{"kaputt": true}')

    assert json.loads(p.read_text(encoding="utf-8")) == {"gut": 1}   # Original unversehrt
    # keine liegengebliebene Temp-Datei
    assert list(tmp_path.glob("*.tmp")) == []


def test_atomic_write_roundtrips(tmp_path):
    p = tmp_path / "sub" / "data.json"        # Ordner wird angelegt
    atomic_write_text(p, '{"a": 2}')
    assert json.loads(p.read_text(encoding="utf-8")) == {"a": 2}


def test_store_skips_structurally_broken_tree(tmp_path):
    good = RepertoireTree.new("Gut", "white")
    good.add_child(good.root_id, "e2e4")
    store = RepertoireTreeStore()
    store.add(good)
    data = store.to_dict()
    # ein zweiter Baum mit fehlender Wurzel (root_id zeigt ins Leere)
    data["trees"].append({
        "id": "broken", "name": "Kaputt", "side": "white",
        "root_id": "does-not-exist", "nodes": [], "headers": {},
    })
    loaded = RepertoireTreeStore.from_dict(data)
    names = {t.name for t in loaded.all()}
    assert "Gut" in names and "Kaputt" not in names      # guter Baum bleibt, kaputter fällt weg
    # der geladene gute Baum ist benutzbar (kein späterer KeyError)
    tree = loaded.all()[0]
    assert tree.root is not None and len(tree.children_of(tree.root_id)) == 1


def test_broken_tree_from_dict_raises():
    with pytest.raises(ValueError):
        RepertoireTree.from_dict({
            "id": "x", "name": "X", "side": "white",
            "root_id": "missing", "nodes": [], "headers": {},
        })
