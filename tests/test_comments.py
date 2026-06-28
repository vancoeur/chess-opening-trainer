"""Kommentar-Aufbereitung: rohe PGN-Zeichen-Anweisungen aus der Anzeige raus."""
from opening_trainer.comments import clean_comment_text


def test_empty_stays_empty():
    assert clean_comment_text("") == ""
    assert clean_comment_text("   ") == ""


def test_strips_arrows_and_squares():
    raw = "[%csl Ga5,Gc4][%cal Gc6a5,Ga5c4]"
    assert clean_comment_text(raw) == ""          # nur Markup -> nichts übrig


def test_keeps_readable_text_around_markup():
    raw = "Springer nach a5 [%cal Gc6a5] und schlägt c4."
    assert clean_comment_text(raw) == "Springer nach a5 und schlägt c4."


def test_collapses_whitespace():
    assert clean_comment_text("  Plan:   [%clk 0:05:00]   Druck   ") == "Plan: Druck"
