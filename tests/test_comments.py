"""Kommentar-Aufbereitung: rohe PGN-Zeichen-Anweisungen aus der Anzeige raus."""
from opening_trainer.comments import clean_comment_text, clean_chapter_name, is_instructional


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


# --- clean_chapter_name (Studien-Kapitelnamen säubern) --------------------

def test_chapter_strips_prefix_and_move_tail():
    raw = "Chapter #10: - Classical Variation - Karpov - e4 c6 2. d4 d5"
    assert clean_chapter_name(raw) == "Classical Variation - Karpov"


def test_chapter_strips_quickstarter_and_moves():
    assert clean_chapter_name("Quickstarter Guide - Advance Variation - e4 c6") == "Advance Variation"


def test_chapter_plain_name_kept():
    assert clean_chapter_name("Panov-Botvinnik Attack - Fianchetto Defence") == \
        "Panov-Botvinnik Attack - Fianchetto Defence"


def test_chapter_strips_eco_code_prefix():
    assert clean_chapter_name("B18 · Caro-Kann: Klassische Variante") == \
        "Caro-Kann: Klassische Variante"


def test_chapter_collapses_double_dash():
    assert clean_chapter_name("Instructive Game #2 Kasparov - - Ivanchuk") == \
        "Instructive Game #2 Kasparov - Ivanchuk"


def test_chapter_empty():
    assert clean_chapter_name("") == ""


def test_is_instructional():
    assert is_instructional("Instructive Game #2 Kasparov - Ivanchuk")
    assert is_instructional("Do's and Don'ts - Black's Perspective - Middlegame Plan #2")
    assert is_instructional("Introduction: - Caro Kann - Author's Acknowledgement")
    # echte Varianten sind KEIN Lehrmaterial
    assert not is_instructional("Caro-Kann Defense: Advance Variation")
    assert not is_instructional("Chapter #10: - Classical Variation - Karpov")
