"""Repertoire-Baum-Übersicht: viele getrennte Linien -> ein verzweigter Baum,
plus flache, eingerückte Zeilen für die Anzeige. Reine Logik, kein Qt.
"""
import chess

from opening_trainer.repertoire_tree import RepertoireTree, WHITE, BLACK
from opening_trainer.tree_session import merge_side_trees, overview_rows, merge_stats


def _black(name, ucis):
    t = RepertoireTree.new(name, BLACK)
    p = t.root_id
    for u in ucis:
        p = t.add_child(p, u).id
    return t


def test_merge_shares_prefix_and_branches():
    # Zwei Caro-artige Linien: gemeinsamer Stamm 1.e4 c6 2.d4 d5, dann Weiß 3.e5 / 3.Sc3
    a = _black("Advance", ["e2e4", "c7c6", "d2d4", "d7d5", "e4e5", "c8f5"])
    b = _black("Klassisch", ["e2e4", "c7c6", "d2d4", "d7d5", "b1c3", "d5e4"])
    m = merge_side_trees([a, b], chess.BLACK)
    # Stamm bis 2...d5 ist EIN Pfad
    node = m.root
    for u in ["e2e4", "c7c6", "d2d4", "d7d5"]:
        kids = m.children_of(node.id)
        assert len(kids) == 1
        node = kids[0]
        assert node.move_uci == u
    # an 2...d5 verzweigt Weiß: e4e5 und b1c3
    branch = {c.move_uci for c in m.children_of(node.id)}
    assert branch == {"e4e5", "b1c3"}


def test_merge_filters_other_side():
    white = RepertoireTree.new("w", WHITE)
    white.add_child(white.root_id, "e2e4")
    m = merge_side_trees([white], chess.BLACK)      # falsche Seite -> leerer Baum
    assert m.children_of(m.root_id) == []


def test_overview_rows_depth_and_labels():
    a = _black("Advance", ["e2e4", "c7c6", "d2d4", "d7d5", "e4e5", "c8f5"])
    b = _black("Klassisch", ["e2e4", "c7c6", "d2d4", "d7d5", "b1c3", "d5e4"])
    m = merge_side_trees([a, b], chess.BLACK)
    rows = overview_rows(m, chess.BLACK)
    labels = [r["label"] for r in rows]
    assert labels[0] == "1.e4"        # Weiß-Zug
    assert labels[1] == "1…c6"        # Schwarz-Zug (eigener)
    assert "3.e5" in labels                      # SAN englisch; Germanisierung macht die UI
    assert "3.Nc3" in labels
    # Hauptlinie bleibt flach (Tiefe 0); nur Varianten rücken ein
    assert rows[0]["depth"] == 0 and rows[1]["depth"] == 0
    assert max(r["depth"] for r in rows) == 1    # eine Verzweigungs-Ebene
    # eigener Zug erkannt
    assert rows[1]["is_user_move"] is True       # 1...c6 = Schwarz am Zug
    assert rows[0]["is_user_move"] is False      # 1.e4 = Weiß


def test_merge_carries_line_names_to_leaves():
    a = _black("B18 Caro Klassisch", ["e2e4", "c7c6", "d2d4", "d7d5", "b1c3", "d5e4"])
    b = _black("B12 Caro Vorstoß", ["e2e4", "c7c6", "d2d4", "d7d5", "e4e5", "c8f5"])
    rows = overview_rows(merge_side_trees([a, b], chess.BLACK), chess.BLACK)
    leaves = [r for r in rows if r["children"] == 0]
    names = {r["comment"] for r in leaves}
    assert "B18 Caro Klassisch" in names
    assert "B12 Caro Vorstoß" in names
    # Stamm-Knoten (mit Kindern) tragen keinen Namen
    assert all(not r["comment"] for r in rows if r["children"] > 0)


def test_merge_stats_counts_lines_and_branches():
    a = _black("Advance", ["e2e4", "c7c6", "d2d4", "d7d5", "e4e5", "c8f5"])
    b = _black("Klassisch", ["e2e4", "c7c6", "d2d4", "d7d5", "b1c3", "d5e4"])
    st = merge_stats([a, b], chess.BLACK)
    assert st["lines"] == 2
    assert st["branches"] == 1                 # eine Verzweigung an 2...d5
    # rein lineare Einzel-Linie -> 0 Verzweigungen
    one = _black("nur", ["e2e4", "c7c6", "d2d4", "d7d5"])
    assert merge_stats([one], chess.BLACK) == {"lines": 1, "branches": 0}
    # falsche Seite zählt nicht
    assert merge_stats([a, b], chess.WHITE) == {"lines": 0, "branches": 0}


def test_overview_branch_node_reports_children():
    a = _black("Advance", ["e2e4", "c7c6", "d2d4", "d7d5", "e4e5"])
    b = _black("Klassisch", ["e2e4", "c7c6", "d2d4", "d7d5", "b1c3"])
    m = merge_side_trees([a, b], chess.BLACK)
    rows = overview_rows(m, chess.BLACK)
    # die Zeile »2...d5« hat zwei Kinder (Verzweigung)
    d5 = next(r for r in rows if r["label"] == "2…d5")
    assert d5["children"] == 2
