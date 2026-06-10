import chess

from opening_trainer.game_review import build_repertoire_book, review_game


def sans_to_uci(sans):
    """Hilfs: SAN-Zugfolge -> UCI-Liste (für lesbare Tests)."""
    board = chess.Board()
    out = []
    for san in sans:
        move = board.parse_san(san)
        out.append(move.uci())
        board.push(move)
    return out


# Weiß-Repertoire: 1.e4 c5 2.Nf3 (eine Linie)
WHITE_LINE = sans_to_uci(["e4", "c5", "Nf3", "d6", "d4"])


def test_book_records_own_moves_only():
    book = build_repertoire_book([WHITE_LINE], chess.WHITE)
    start = chess.Board().epd()
    assert book[start] == {"e4"}
    # nach 1.e4 c5 ist Weiß am Zug -> Nf3 vorgesehen
    b = chess.Board(); b.push_san("e4"); b.push_san("c5")
    assert book[b.epd()] == {"Nf3"}


def test_game_following_repertoire():
    book = build_repertoire_book([WHITE_LINE], chess.WHITE)
    game = sans_to_uci(["e4", "c5", "Nf3", "d6", "d4", "cxd4"])
    r = review_game(game, book, chess.WHITE)
    assert r.status == "followed"
    assert r.booked_plies == 3   # e4, Nf3, d4


def test_game_deviates_from_repertoire():
    book = build_repertoire_book([WHITE_LINE], chess.WHITE)
    # Weiß spielt statt 2.Nf3 das abweichende 2.Nc3
    game = sans_to_uci(["e4", "c5", "Nc3"])
    r = review_game(game, book, chess.WHITE)
    assert r.status == "deviated"
    assert r.deviation.move_number == 2
    assert r.deviation.played_san == "Nc3"
    assert r.deviation.expected_sans == ["Nf3"]
    assert r.booked_plies == 1   # e4 lag noch im Repertoire


def test_white_deviates_at_first_move():
    book = build_repertoire_book([WHITE_LINE], chess.WHITE)
    # Weiß eröffnet 1.d4 statt des Repertoire-Zugs 1.e4 -> Abweichung bei Zug 1
    game = sans_to_uci(["d4", "Nf6", "c4"])
    r = review_game(game, book, chess.WHITE)
    assert r.status == "deviated"
    assert r.deviation.move_number == 1
    assert r.deviation.played_san == "d4"
    assert r.deviation.expected_sans == ["e4"]


def test_black_out_of_book_when_opponent_uncovered():
    # Schwarz-Repertoire nur gegen 1.e4; Gegner spielt 1.d4 -> erste eigene
    # Stellung gar nicht abgedeckt.
    black_line = sans_to_uci(["e4", "c5", "Nf3", "d6"])
    book = build_repertoire_book([black_line], chess.BLACK)
    game = sans_to_uci(["d4", "Nf6", "c4", "e6"])
    r = review_game(game, book, chess.BLACK)
    assert r.status == "out_of_book"
    assert r.booked_plies == 0


def test_transposition_is_matched_via_epd():
    book = build_repertoire_book([WHITE_LINE], chess.WHITE)
    # Zugumstellung: 1.Nf3 c5 2.e4 d6 3.d4 -> selbe Stellungen wie 1.e4 c5 2.Nf3
    game = sans_to_uci(["Nf3", "c5", "e4", "d6", "d4"])
    r = review_game(game, book, chess.WHITE)
    # 1.Nf3 ist NICHT der Buch-Zug der Startstellung (dort steht e4) -> Abweichung
    assert r.status == "deviated"
    assert r.deviation.move_number == 1
    assert r.deviation.played_san == "Nf3"


def test_black_repertoire_side():
    # Schwarz-Repertoire gegen 1.e4: 1...c5 2.Nf3 d6
    black_line = sans_to_uci(["e4", "c5", "Nf3", "d6"])
    book = build_repertoire_book([black_line], chess.BLACK)
    game = sans_to_uci(["e4", "c5", "Nf3", "Nc6"])   # Schwarz weicht mit 2...Nc6 ab
    r = review_game(game, book, chess.BLACK)
    assert r.status == "deviated"
    assert r.deviation.played_san == "Nc6"
    assert r.deviation.expected_sans == ["d6"]
