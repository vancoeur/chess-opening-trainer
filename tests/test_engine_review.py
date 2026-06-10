from opening_trainer.engine_review import (
    classify_loss,
    is_blunder_move,
    judge_deviation,
    sparring_strength,
)


def test_clean_move_is_not_flagged():
    # Bester Zug gespielt, Stellung gleich: nichts melden.
    assert classify_loss(0, 20) is None


def test_small_loss_in_good_position_is_ok():
    # Etwas schlechter als der beste Zug, aber Stellung steht weiter gut.
    assert classify_loss(160, 40) is None


def test_dubious_move_is_inaccuracy():
    # Spürbarer Verlust UND danach leicht schlechter -> Ungenauigkeit.
    assert classify_loss(180, -60) == "ungenau"


def test_big_loss_into_bad_position_is_blunder():
    assert classify_loss(350, -250) == "patzer"


def test_big_loss_but_still_fine_is_not_blunder():
    # Großer relativer Verlust, aber Stellung danach noch ausgeglichen:
    # kein echter Patzer (z. B. von +5 auf +1.5).
    assert classify_loss(350, 150) is None


def test_inaccuracy_threshold_boundary():
    assert classify_loss(150, -50) == "ungenau"
    assert classify_loss(149, -50) is None
    assert classify_loss(150, -49) is None


def test_lost_position_is_blunder_even_if_relative_loss_small():
    # C31-Fall: bester Zug auch schon schlecht, gespielter Zug landet auf -5.6;
    # relativer Verlust 290 < 300, aber Stellung klar verloren -> Patzer, nicht "ungenau".
    assert classify_loss(290, -560) == "patzer"


def test_forced_move_in_lost_position_is_not_blamed():
    # Stellung schon verloren, es gab keinen spuerbar besseren Zug -> nicht melden.
    assert classify_loss(50, -300) is None


# --- judge_deviation (Üben: "War mein Zug gut?") ------------------------

def test_deviation_equal_move_is_ok():
    assert judge_deviation(0, 30) == "gleichwertig"


def test_deviation_better_move_is_ok():
    # Gespielter Zug sogar besser als der Repertoire-Zug (negativer Verlust).
    assert judge_deviation(-60, 50) == "gleichwertig"


def test_deviation_small_loss_is_ok():
    assert judge_deviation(40, 10) == "gleichwertig"


def test_deviation_medium_loss_is_inaccuracy():
    assert judge_deviation(90, -20) == "ungenau"


def test_deviation_large_loss_is_mistake():
    assert judge_deviation(200, 50) == "fehler"


def test_deviation_into_lost_position_is_mistake():
    # Nur 120 schlechter als der Repertoire-Zug, aber landet klar verloren.
    assert judge_deviation(120, -300) == "fehler"


def test_deviation_boundaries():
    assert judge_deviation(40, 0) == "gleichwertig"
    assert judge_deviation(41, 0) == "ungenau"
    assert judge_deviation(150, 0) == "ungenau"
    assert judge_deviation(151, 0) == "fehler"


# --- sparring_strength (Sparring-Gegnerstärke) --------------------------

def test_sparring_levels_increase_in_strength():
    a_skill, a_time = sparring_strength("anfaenger")
    m_skill, m_time = sparring_strength("mittel")
    s_skill, s_time = sparring_strength("stark")
    assert a_skill < m_skill < s_skill
    assert 0 <= a_skill <= 20 and 0 <= s_skill <= 20


def test_sparring_unknown_level_falls_back_to_mittel():
    assert sparring_strength("quatsch") == sparring_strength("mittel")


# --- is_blunder_move (Sparring-Patzer-Hinweis) --------------------------

def test_white_blunder_is_detected():
    # Weiß stand +0.5, nach eigenem Zug -2.0 -> Einbruch 2.5 > 1.5.
    assert is_blunder_move(50, -200, mover_is_white=True) is True


def test_white_good_move_no_blunder():
    assert is_blunder_move(50, 40, mover_is_white=True) is False


def test_black_blunder_is_detected():
    # Aus Weiß-Sicht: vorher -50 (Schwarz +50), danach +200 (Schwarz -200).
    assert is_blunder_move(-50, 200, mover_is_white=False) is True


def test_black_good_move_no_blunder():
    assert is_blunder_move(-50, -40, mover_is_white=False) is False


def test_blunder_threshold_boundary():
    assert is_blunder_move(0, -151, mover_is_white=True) is True
    assert is_blunder_move(0, -150, mover_is_white=True) is False


def test_improving_move_is_never_blunder():
    assert is_blunder_move(0, 300, mover_is_white=True) is False
