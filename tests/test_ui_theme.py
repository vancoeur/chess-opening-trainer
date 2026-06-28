"""Modernes Aussehen: Hell/Dunkel-Umschalter, Seitenleisten-Navigation, kein
»Gehe zu«-Menü mehr. Die Fachlogik ist unberührt — geprüft wird nur die Hülle.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _win(tmp_path, monkeypatch):
    import qt_app.main_window as mw
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    return mw.MainWindow()


def test_amp_escaping_fixes_button_underscore():
    import qt_app.main_window as mw
    # »&« auf einem Knopf würde sonst zum Tastatur-Kürzel (Unterstrich).
    assert mw.MainWindow._amp("Trefferquote & Fehler") == "Trefferquote && Fehler"
    assert mw.MainWindow._amp("kein Zeichen") == "kein Zeichen"


def test_theme_toggle_applies_and_remembers(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    # Echte Einstellungen sichern (Tests dürfen Achims Wahl nicht verändern).
    orig_ui = win._eval_settings.value("ui_theme")
    orig_board = win._eval_settings.value("board_theme")
    try:
        win._set_ui_theme("dark")
        assert win._ui_theme == "dark"
        assert win._eval_settings.value("ui_theme") == "dark"
        assert win._board_theme == "green"          # passendes Brett-Set
        assert "#302e2a" in win.styleSheet()        # dunkle (Anthrazit) Grundfarbe aktiv

        win._set_ui_theme("light")
        assert win._ui_theme == "light"
        assert win._board_theme == "green"
        assert "#eff6fd" in win.styleSheet()        # helle Grundfarbe (dezent hellblau) aktiv
    finally:
        win._eval_settings.setValue("ui_theme", orig_ui if orig_ui is not None else "light")
        win._eval_settings.setValue("board_theme", orig_board if orig_board is not None else "green")


def test_sidebar_marks_active_page(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    win._open_library()                              # Seite 1
    assert win._nav_buttons[1].objectName() == "navon"
    assert win._nav_buttons[2].objectName() == "nav"
    win._open_stats()                                # Seite 2
    assert win._nav_buttons[2].objectName() == "navon"
    assert win._nav_buttons[1].objectName() == "nav"  # vorige Markierung gelöscht


def test_sidebar_covers_every_section(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    # Start + die vier Rubriken-Ziele müssen als Navigationspunkte existieren.
    for target in (12, 11, 10, 3, 13, 1, 9, 5, 2, 7, 6, 4):
        assert target in win._nav_buttons


def test_go_menu_is_gone(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    titles = [m.title() for m in win.menuBar().findChildren(QtWidgets.QMenu)]
    assert "Gehe zu" not in titles and "Go" not in titles
    # Aber die gewohnten Kürzel-Ziele leben weiter (über die Seitenleiste/Shortcuts).
    assert any(tt in ("Ansicht", "View") for tt in titles)
