from opening_trainer.explorer import parse_explorer_response, percent

# Beispielhafte Lichess-Explorer-Antwort (gekürzt, Struktur wie echt).
SAMPLE = {
    "white": 1000,
    "draws": 200,
    "black": 800,
    "opening": {"eco": "B00", "name": "King's Pawn Game"},
    "moves": [
        {"san": "e4", "uci": "e2e4", "white": 500, "draws": 100, "black": 400, "averageRating": 1900},
        {"san": "d4", "uci": "d2d4", "white": 300, "draws": 60, "black": 240},
    ],
}


def test_percent_basic():
    assert percent(1, 2) == 50
    assert percent(0, 0) == 0
    assert percent(1, 3) == 33


def test_parse_totals_and_opening():
    r = parse_explorer_response(SAMPLE)
    assert r.white == 1000 and r.draws == 200 and r.black == 800
    assert r.total == 2000
    assert r.opening_name == "King's Pawn Game"


def test_parse_moves():
    r = parse_explorer_response(SAMPLE)
    assert len(r.moves) == 2
    e4 = r.moves[0]
    assert e4.san == "e4" and e4.uci == "e2e4"
    assert e4.total == 1000
    # Popularität von e4 = 1000 / 2000 = 50 %
    assert percent(e4.total, r.total) == 50


def test_parse_empty_response():
    r = parse_explorer_response({})
    assert r.total == 0
    assert r.moves == []
    assert r.opening_name is None


def test_parse_tolerates_missing_fields():
    r = parse_explorer_response({"moves": [{"san": "Nf3"}]})
    assert r.moves[0].san == "Nf3"
    assert r.moves[0].total == 0
    assert r.moves[0].uci == ""
