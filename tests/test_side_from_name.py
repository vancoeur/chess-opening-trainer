"""Spielerfarbe (Repertoire-Seite) aus dem Dateinamen ableiten."""
from opening_trainer.opening_sides import side_from_name, WHITE, BLACK


def test_white_filenames():
    assert side_from_name("Weiss London.pgn") == WHITE
    assert side_from_name("Weiss 1d4.pgn") == WHITE
    assert side_from_name("Schachrepertoire Weiss.pgn") == WHITE
    assert side_from_name("Weissrepertoire_namen_bereinigt.pgn") == WHITE
    assert side_from_name("White_Masterrepertoire.pgn") == WHITE
    assert side_from_name("Eröffnung Weiß.pgn") == WHITE


def test_black_filenames():
    assert side_from_name("Schwarz Pirc.pgn") == BLACK
    assert side_from_name("Schwarz CaroKann.pgn") == BLACK
    assert side_from_name("Schachrepertoire Schwarz_namen_bereinigt.pgn") == BLACK
    assert side_from_name("black_repertoire.pgn") == BLACK


def test_ambiguous_or_neutral_returns_none():
    assert side_from_name("Repertoire.pgn") is None          # keine Farbe
    assert side_from_name("sample_openings.pgn") is None
    assert side_from_name("Schwarz gegen Weiss.pgn") is None  # beide Farben -> nicht raten


def test_full_path_is_handled():
    assert side_from_name("/Users/x/Desktop/Repertoire/Weiss London.pgn") == WHITE
