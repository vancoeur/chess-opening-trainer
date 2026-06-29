"""Namens-orientierte Baum-Übersicht: gruppiert die Kapitel einer Seite nach
ihrem ECO-Eröffnungsnamen (aus den ersten ~20 Halbzügen der Hauptlinie), je
Gruppe ein verschachtelter Zug-Teilbaum. Reine Logik."""
import chess

from opening_trainer.repertoire_tree import RepertoireTree, BLACK, WHITE
from opening_trainer.tree_session import variation_outline


def _u(sans):
    b = chess.Board()
    out = []
    for s in sans:
        m = b.parse_san(s)
        out.append(m.uci())
        b.push(m)
    return out


def _black(name, sans):
    t = RepertoireTree.new(name, BLACK)
    p = t.root_id
    for u in _u(sans):
        p = t.add_child(p, u).id
    return t


ADV = ["e4", "c6", "d4", "d5", "e5", "Bf5", "Nf3", "e6"]
EXCH = ["e4", "c6", "d4", "d5", "exd5", "cxd5", "Bd3"]
PANOV = ["e4", "c6", "d4", "d5", "exd5", "cxd5", "c4", "Nf6", "Nc3"]


def test_groups_use_eco_names():
    out = variation_outline([_black("Kapitel A", ADV),
                             _black("Kapitel B", EXCH)], chess.BLACK)
    names = [g["name"] for g in out]
    assert any("Advance Variation" in n for n in names)
    assert any("Exchange Variation" in n for n in names)
    # NICHT die (nichtssagenden) Kapitelnamen:
    assert "Kapitel A" not in names and "Kapitel B" not in names


def test_same_eco_name_merges_chapters():
    # Zwei Panov-Kapitel, die erst tief (nach dem benannten ECO-Punkt) abzweigen
    # -> gleicher ECO-Name -> EINE Gruppe mit zwei Linien.
    a = _black("Panov 1", PANOV + ["e6", "Nf3", "Be7"])
    b = _black("Panov 2", PANOV + ["e6", "Nf3", "Bd6"])
    out = variation_outline([a, b], chess.BLACK)
    assert len(out) == 1
    assert "Panov" in out[0]["name"]
    assert out[0]["lines"] == 2


def test_gap_leaf_is_flagged_and_counted():
    # Linie endet mit Weißzug (3.Nf3), Schwarz am Zug ohne Antwort -> Lücke.
    out = variation_outline([_black("X", ["e4", "c6", "d4", "d5", "Nf3"])], chess.BLACK)
    g = out[0]
    assert g["gaps"] == 1

    def leaves(nodes):
        for n in nodes:
            if n["children"]:
                yield from leaves(n["children"])
            else:
                yield n
    leaf = list(leaves(g["nodes"]))[-1]
    assert leaf["is_gap"] is True
    assert leaf["label"] == "3.Nf3"


def test_instructional_chapters_go_to_misc_group_last():
    out = variation_outline([
        _black("Kapitel A", ADV),
        _black("Instructive Game #2 Kasparov - Ivanchuk", PANOV),
        _black("Do's and Don'ts - Middlegame Plan #1", EXCH),
    ], chess.BLACK, misc_label="Lehrmaterial")
    names = [g["name"] for g in out]
    assert "Lehrmaterial" in names
    assert names[-1] == "Lehrmaterial"             # Sammelgruppe steht am Ende
    misc = next(g for g in out if g["name"] == "Lehrmaterial")
    assert misc["lines"] == 2                       # beide Lehr-Kapitel zusammengefasst
    # die echte Variante bleibt eigenständig
    assert any("Advance Variation" in n for n in names)


KLASS = ["e4", "c6", "d4", "d5", "Nc3", "dxe4", "Nxe4", "Bf5", "Ng3"]   # ECO nur Familie


def test_strip_family_shortens_eco_and_merges_fallback():
    out = variation_outline([
        _black("Kapitel A", ADV),                                  # ECO: Advance
        _black("Classical Variation - Karpov", KLASS + ["Bg6"]),   # ECO nur Familie -> Rückfall
        _black("Classical Variation - Capablanca", KLASS + ["Bd7"]),
    ], chess.BLACK, strip_family=True)
    names = [g["name"] for g in out]
    assert "Advance Variation" in names                            # »Caro-Kann Defense:« weg
    assert not any(n.startswith("Caro-Kann Defense") for n in names)
    # beide Classical-Kapitel laufen zu EINER Gruppe zusammen
    assert names.count("Classical Variation") == 1
    classical = next(g for g in out if g["name"] == "Classical Variation")
    assert classical["lines"] == 2


def test_survives_adversarial_trees_without_crashing():
    """Red-Team: kaputte/ungewöhnliche Bäume dürfen die Namens-/Gruppen-Logik
    NICHT zum Absturz bringen — der gute Baum wird trotzdem benannt."""
    good = _black("Kapitel", ADV)

    illegal = RepertoireTree.new("Müll", BLACK)            # illegaler Zug-UCI
    illegal.add_child(illegal.root_id, "e2e5")

    empty = RepertoireTree.new("Leer", BLACK)              # nur Wurzel

    noside = RepertoireTree.new("Ohne Seite", "none")
    p = noside.root_id
    for u in _u(ADV):
        p = noside.add_child(p, u).id

    custom = RepertoireTree.new("Sonderstellung", BLACK,
                                start_fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    custom.add_child(custom.root_id, "e2e4")

    weird = _black("", ["e4", "c6"])                       # leerer Name
    weird.name = ""
    uni = _black("Caro – Königsläufer-Variante ♞", ADV)    # Nicht-ASCII

    trees = [good, illegal, empty, noside, custom, weird, uni]
    out = variation_outline(trees, chess.BLACK, strip_family=True)   # darf nicht werfen
    names = [g["name"] for g in out]
    assert any("Advance Variation" in n for n in names)    # der gute Baum ist benannt


def test_user_move_flag_matches_side():
    out = variation_outline([_black("X", ADV)], chess.BLACK)
    first = out[0]["nodes"][0]
    assert first["is_user_move"] is False                  # 1.e4 (Weiß)
    assert first["children"][0]["label"] == "1…c6"
    assert first["children"][0]["is_user_move"] is True


def _white(name, sans):
    t = RepertoireTree.new(name, WHITE)
    p = t.root_id
    for u in _u(sans):
        p = t.add_child(p, u).id
    return t


def test_transposed_setup_falls_back_to_clean_chapter_name():
    # London gegen …c5 (ECO »Old Benoni«): nicht eindeutig -> PGN-Name, gesäubert.
    c5 = _white("London B1 vs ...c5 Hauptaufbau (e3, c3)",
                ["d4", "c5", "Bf4", "Nf6", "e3", "d5", "c3", "Nc6"])
    out = variation_outline([c5], chess.WHITE, strip_family=True)
    names = [g["name"] for g in out]
    assert names == ["London B1 vs ...c5 Hauptaufbau"]      # Klammer-Zusatz entfernt
    assert not any("Benoni" in n for n in names)            # KEIN ECO-Fehletikett


def test_reliable_eco_name_is_kept_for_real_london():
    # London gegen …d5 ist sauber als London erkennbar -> ECO-Name bleibt.
    d5 = _white("London A1 vs ...d5 Klassisch (Bd3, c3, Nbd2)",
                ["d4", "d5", "Nf3", "Nf6", "Bf4", "e6", "e3", "Bd6"])
    out = variation_outline([d5], chess.WHITE, strip_family=True)
    assert "London System" in out[0]["name"]
