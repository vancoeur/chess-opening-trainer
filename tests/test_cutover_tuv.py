"""Cutover Scheibe 3: Repertoire-Prüfung über Baum-Varianten.

``tree_session.tree_check_paths`` liefert die Wurzel-zu-Blatt-Pfade (vollständige
Varianten) als (name, moves_uci, tree) — Grundlage dafür, dass die Prüfung auch
Nebenvarianten und nicht nur lineare Hauptlinien abdeckt. Kein Qt.
"""
import chess

from opening_trainer.repertoire_tree import RepertoireTree, WHITE, BLACK
from opening_trainer.tree_session import tree_check_paths


def _tree_with_variation():
    # 1.e4 e5 2.Nf3 / 2.Bc4  -> zwei Varianten.
    t = RepertoireTree.new("open", WHITE)
    t.add_child(t.root_id, "e2e4")
    e4 = t.children_of(t.root_id)[0]
    t.add_child(e4.id, "e7e5")
    e5 = t.children_of(e4.id)[0]
    t.add_child(e5.id, "g1f3")
    t.add_child(e5.id, "f1c4")
    return t


def test_each_leaf_is_one_variation():
    t = _tree_with_variation()
    paths = tree_check_paths([t], chess.WHITE)
    assert len(paths) == 2
    move_seqs = sorted(tuple(m) for _, m, _ in paths)
    assert move_seqs == sorted([
        ("e2e4", "e7e5", "g1f3"),
        ("e2e4", "e7e5", "f1c4"),
    ])
    # mehrere Varianten -> Name nummeriert; tree wird mitgegeben
    assert all(p[0].startswith("open") for p in paths)
    assert all(p[2] is t for p in paths)


def test_single_mainline_keeps_plain_name():
    t = RepertoireTree.new("main", WHITE)
    p = t.root_id
    for u in ["e2e4", "e7e5", "g1f3"]:
        p = t.add_child(p, u).id
    paths = tree_check_paths([t], chess.WHITE)
    assert len(paths) == 1
    assert paths[0][0] == "main"                 # nicht nummeriert
    assert paths[0][1] == ["e2e4", "e7e5", "g1f3"]


def test_side_filter_and_empty_tree():
    t = _tree_with_variation()
    assert tree_check_paths([t], chess.BLACK) == []          # falsche Seite
    empty = RepertoireTree.new("leer", WHITE)
    assert tree_check_paths([empty], chess.WHITE) == []      # nur Wurzel -> keine Pfade


def test_black_tree_paths():
    t = RepertoireTree.new("caro", BLACK)
    p = t.root_id
    for u in ["e2e4", "c7c6", "d2d4", "d7d5"]:
        p = t.add_child(p, u).id
    paths = tree_check_paths([t], chess.BLACK)
    assert len(paths) == 1
    assert paths[0][1] == ["e2e4", "c7c6", "d2d4", "d7d5"]
