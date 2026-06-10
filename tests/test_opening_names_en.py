from opening_trainer.opening_names_en import to_english


def test_keeps_proper_nouns():
    assert to_english("B99 · Caro-Kann: Najdorf") == "B99 · Caro-Kann: Najdorf"


def test_common_terms():
    assert to_english("Ruy López: Berliner Verteidigung") == "Ruy López: Berlin Defence"
    assert to_english("Geschlossene Variante") == "Closed Variation"
    assert to_english("Sizilianisch: Klassische Variante") == "Sicilian: Classical Variation"


def test_no_ending_collision():
    # frühere Bugs: Englishr / Scotchs / Spanishs
    assert to_english("Englischer Angriff") == "English Attack"
    assert to_english("Schottisches Vier-Springer") == "Scotch Four Knights"
    assert to_english("Spanisches Vier-Springer") == "Spanish Four Knights"


def test_hyphen_terms_become_spaces():
    assert to_english("Marshall-Angriff") == "Marshall Attack"
    assert to_english("Tchigorin-Variante") == "Tchigorin Variation"


def test_families():
    assert to_english("Königsindisch: Vier-Bauern-Angriff") == "King's Indian: Four Pawns Attack"
    assert to_english("Damengambit") == "Queen's Gambit"
    assert to_english("Wiener Partie") == "Vienna Game"


def test_unknown_words_unchanged():
    assert to_english("Sämisch") == "Sämisch"
    assert to_english("Giuoco Pianissimo") == "Giuoco Pianissimo"
