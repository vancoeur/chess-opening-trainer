"""Selectable board colors: themes are well-formed and apply in place."""
from qt_app.board_view import BOARD_THEMES, set_board_theme, LIGHT, DARK


def test_board_themes_well_formed():
    assert set(BOARD_THEMES) >= {"green", "brown", "blue", "grey"}
    for light, dark in BOARD_THEMES.values():
        for hexcol in (light, dark):
            assert hexcol.startswith("#") and len(hexcol) == 7


def test_set_board_theme_applies_in_place():
    set_board_theme("brown")
    assert LIGHT.name() == "#f0d9b5"
    assert DARK.name() == "#b58863"
    set_board_theme("blue")
    assert DARK.name() == "#8ca2ad"


def test_unknown_theme_falls_back_to_green():
    set_board_theme("does-not-exist")
    assert LIGHT.name() == "#ebecd0"
    assert DARK.name() == "#779556"


def teardown_module(module):
    # Standardfarbe wiederherstellen, damit andere Tests/Importe sie sehen.
    set_board_theme("green")
