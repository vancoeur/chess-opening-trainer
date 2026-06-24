"""Cutover Scheibe 2: Partie-Auswertung gegen ein varianten-bewusstes Buch.

``position_book.build_san_book`` ersetzt ``game_review.build_repertoire_book``
als Quelle für ``review_game`` — gleiche Form (epd -> Menge SAN), aber aus den
Bäumen statt aus linearen Hauptlinien. Kein Qt.
"""
import chess

from opening_trainer.repertoire_tree import RepertoireTree, WHITE
from opening_trainer.position_book import build_san_book
from opening_trainer.game_review import build_repertoire_book, review_game


def _white_tree_with_variation():
    # Weiß am Zug nach 1.e4 e5: Hauptzug 2.Nf3, Variante 2.Bc4 (beide vorgesehen).
    t = RepertoireTree.new("open", WHITE)
    t.add_child(t.root_id, "e2e4")
    e4 = t.children_of(t.root_id)[0]
    t.add_child(e4.id, "e7e5")
    e5 = t.children_of(e4.id)[0]
    t.add_child(e5.id, "g1f3")     # Hauptlinie
    t.add_child(e5.id, "f1c4")     # Variante
    return t


def _epd_after(ucis):
    b = chess.Board()
    for u in ucis:
        b.push(chess.Move.from_uci(u))
    return b.epd()


def test_san_book_includes_all_variations():
    t = _white_tree_with_variation()
    book = build_san_book([t], chess.WHITE)
    key = _epd_after(["e2e4", "e7e5"])
    assert book[key] == {"Nf3", "Bc4"}        # beide Äste vorgesehen


def test_san_book_matches_repertoire_book_on_a_mainline():
    # Reine Hauptlinie -> identisch zur linearen build_repertoire_book.
    t = RepertoireTree.new("main", WHITE)
    p = t.root_id
    for u in ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4"]:
        p = t.add_child(p, u).id
    tree_book = build_san_book([t], chess.WHITE)
    line_book = build_repertoire_book([["e2e4", "e7e5", "g1f3", "b8c6", "f1c4"]], chess.WHITE)
    assert tree_book == line_book


def test_variation_no_longer_flagged_as_deviation():
    t = _white_tree_with_variation()
    book = build_san_book([t], chess.WHITE)
    # Partie folgt der VARIANTE 2.Bc4 — darf nicht als Abweichung gelten.
    game = ["e2e4", "e7e5", "f1c4"]
    assert review_game(game, book, chess.WHITE).status == "followed"

    # Gegenprobe: das linien-basierte Buch (nur Hauptlinie 2.Nf3) meldet Abweichung.
    line_only = build_repertoire_book([["e2e4", "e7e5", "g1f3"]], chess.WHITE)
    assert review_game(game, line_only, chess.WHITE).status == "deviated"
