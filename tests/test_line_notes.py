from opening_trainer.line_notes import LineNotes


def test_empty_store_returns_blank():
    n = LineNotes()
    assert n.note_of("a.pgn", "Linie 1") == ""
    assert n.has_note("a.pgn", "Linie 1") is False


def test_set_and_get_note():
    n = LineNotes()
    n.set_note("a.pgn", "Sizilianisch", "  typischer Plan: …  ")
    assert n.note_of("a.pgn", "Sizilianisch") == "typischer Plan: …"  # getrimmt
    assert n.has_note("a.pgn", "Sizilianisch") is True


def test_empty_text_removes_note():
    n = LineNotes()
    n.set_note("a.pgn", "X", "etwas")
    n.set_note("a.pgn", "X", "   ")   # nur Leerzeichen -> löschen
    assert n.has_note("a.pgn", "X") is False


def test_notes_are_per_line():
    n = LineNotes()
    n.set_note("a.pgn", "X", "Notiz X")
    assert n.note_of("a.pgn", "Y") == ""
    assert n.note_of("b.pgn", "X") == ""


def test_roundtrip_save_load(tmp_path):
    p = tmp_path / "line_notes.json"
    n = LineNotes()
    n.set_note("a.pgn", "Caro-Kann", "gegen 1.e4")
    n.set_note("b.pgn", "London", "Lc1-f4 zuerst!")
    n.save(p)
    again = LineNotes.load(p)
    assert again.note_of("a.pgn", "Caro-Kann") == "gegen 1.e4"
    assert again.note_of("b.pgn", "London") == "Lc1-f4 zuerst!"


def test_load_missing_file_is_empty():
    assert LineNotes.load("/does/not/exist.json").notes == {}


def test_load_corrupt_file_is_empty(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{ not valid json", encoding="utf-8")
    assert LineNotes.load(p).notes == {}
