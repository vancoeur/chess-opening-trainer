"""Der Linien-Katalog wird aus den Bäumen abgeleitet (Teil-B-Cutover): ein
Eintrag je Auto-Baum, mit Name/Quelle/Hauptpfad/Seite; Editor-Bäume bleiben außen
vor."""
from opening_trainer.repertoire_tree import RepertoireTree, WHITE, BLACK
from opening_trainer.catalog import build_catalog, CatalogEntry


def _auto_tree(name, side, ucis, source):
    t = RepertoireTree.new(name, side)
    p = t.root_id
    for u in ucis:
        p = t.add_child(p, u).id
    t.headers["_auto"] = "1"
    t.headers["_source"] = source
    return t


def test_one_entry_per_auto_tree_with_fields():
    caro = _auto_tree("Caro-Kann: Klassisch", BLACK,
                      ["e2e4", "c7c6", "d2d4", "d7d5"], "Schwarz Caro.pgn")
    entries = build_catalog([caro])
    assert len(entries) == 1
    e = entries[0]
    assert isinstance(e, CatalogEntry)
    assert e.name == "Caro-Kann: Klassisch"
    assert e.source_name == "Schwarz Caro.pgn"
    assert e.side == "black"
    assert e.moves_uci == ["e2e4", "c7c6", "d2d4", "d7d5"]   # Hauptpfad des Baums
    assert e.tree is caro
    assert not hasattr(e, "id")          # darf NICHT als Baum gelten


def test_editor_trees_are_excluded():
    auto = _auto_tree("London", WHITE, ["d2d4", "d7d5", "g1f3"], "Weiss.pgn")
    editor = RepertoireTree.new("Eigener Baum", WHITE)     # ohne _auto-Marke
    editor.add_child(editor.root_id, "e2e4")
    entries = build_catalog([auto, editor])
    names = [e.name for e in entries]
    assert names == ["London"]            # nur der Auto-Baum


def test_mainline_follows_first_child_through_branches():
    # Hauptpfad = erste Kinder; eine Variante an 2.d4 ändert den Hauptpfad nicht.
    t = RepertoireTree.new("Verzweigt", BLACK)
    p = t.add_child(t.root_id, "e2e4").id
    p = t.add_child(p, "c7c6").id
    main = t.add_child(p, "d2d4").id          # Hauptlinie
    t.add_child(p, "g1f3")                     # Variante (zweites Kind)
    t.add_child(main, "d7d5")
    t.headers["_auto"] = "1"; t.headers["_source"] = "x.pgn"
    e = build_catalog([t])[0]
    assert e.moves_uci == ["e2e4", "c7c6", "d2d4", "d7d5"]
