"""The bundled sample openings: present, loadable, translated, side-assigned."""
from pathlib import Path

import chess

from opening_trainer.pgn_loader import load_pgn_file
from opening_trainer.opening_names_en import to_english

SAMPLE = Path(__file__).resolve().parent.parent / "assets" / "sample" / "sample_openings.pgn"

EXPECTED_SIDES = {
    "Italienische Partie — Hauptvariante": "white",
    "Caro-Kann — Klassische Variante": "black",
    "Damengambit Abgelehnt — Klassisches System": "black",
}


def test_sample_file_exists():
    assert SAMPLE.is_file()


def test_sample_loads_three_substantial_lines():
    lines = load_pgn_file(SAMPLE)
    assert [l.name for l in lines] == list(EXPECTED_SIDES)
    for line in lines:
        assert len(line.moves_uci) >= 18, line.name


def test_sample_moves_are_legal():
    for line in load_pgn_file(SAMPLE):
        board = chess.Board()
        for uci in line.moves_uci:
            move = chess.Move.from_uci(uci)
            assert move in board.legal_moves, f"{line.name}: {uci}"
            board.push(move)


def test_sample_names_translate_cleanly():
    for name in EXPECTED_SIDES:
        english = to_english(name)
        assert english != name
        for german_word in ("Partie", "Variante", "Abgelehnt", "Klassisch"):
            assert german_word not in english, english


def test_sample_side_mapping_matches_pgn_names():
    """The hard-coded side mapping in the app must cover exactly these names."""
    from qt_app.main_window import MainWindow

    assert MainWindow._SAMPLE_SIDES == EXPECTED_SIDES
