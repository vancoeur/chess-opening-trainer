"""Spalten-Reihenfolge nach erstem Zug ist sprachunabhängig (per UCI) und deckt
auch seltene erste Züge (1.b3, 1.g3, 1.Sc3 …) ab."""
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

PGN = """[Event "x"]
[ChapterName "Bird"]

1. f4 d5 *

[Event "x"]
[ChapterName "Larsen"]

1. b3 e5 *

[Event "x"]
[ChapterName "Italienisch"]

1. e4 e5 *

[Event "x"]
[ChapterName "Reti"]

1. Nf3 d5 *

[Event "x"]
[ChapterName "Damengambit"]

1. d4 d5 *

[Event "x"]
[ChapterName "Koenigsfianchetto"]

1. g3 d5 *
"""


def _win(tmp_path, monkeypatch):
    import qt_app.main_window as mw
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    return mw.MainWindow()


def test_rare_first_moves_sort_in_canonical_order(tmp_path, monkeypatch):
    from opening_trainer.pgn_loader import load_pgn_text
    win = _win(tmp_path, monkeypatch)
    win.lines = load_pgn_text(PGN, source_name="Weiss Spezial.pgn")
    win._auto_fill_sides_by_filename()                 # alle -> Weiß
    ordered = sorted(win.lines, key=win._category_sort_key)
    moves = [win._first_move_uci(l) for l in ordered]
    # e4, d4, c4, Sf3, g3, b3, f4 … -> hier: e4, d4, Sf3, g3, b3, f4
    assert moves == ["e2e4", "d2d4", "g1f3", "g2g3", "b2b3", "f2f4"]


def test_order_is_language_independent(tmp_path, monkeypatch):
    """Der Sortier-Schlüssel nutzt UCI, nicht das (übersetzte) Etikett —
    die Reihenfolge ist in DE und EN identisch."""
    from opening_trainer.pgn_loader import load_pgn_text
    from qt_app import i18n
    win = _win(tmp_path, monkeypatch)
    win.lines = load_pgn_text(PGN, source_name="Weiss Spezial.pgn")
    win._auto_fill_sides_by_filename()
    old = i18n.language()
    try:
        i18n.set_language("de")
        de = [win._first_move_uci(l) for l in sorted(win.lines, key=win._category_sort_key)]
        i18n.set_language("en")
        en = [win._first_move_uci(l) for l in sorted(win.lines, key=win._category_sort_key)]
    finally:
        i18n.set_language(old)
    assert de == en
    # Springerzug (1.Sf3/1.Nf3) sortiert in BEIDEN Sprachen vor g3/b3/f4
    assert de.index("g1f3") < de.index("g2g3") < de.index("b2b3") < de.index("f2f4")
