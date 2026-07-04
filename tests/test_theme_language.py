"""Design/Sprache (M3): Hell/Dunkel behält die Brettfarbe; Übe-Hinweise sind im
DE-Modus germanisiert; Sprachwechsel behält die Repertoire-Baum-Auswahl.
Offscreen; echte QSettings werden nicht beschrieben."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets  # noqa: E402

import qt_app.main_window as mw  # noqa: E402
from opening_trainer.repertoire_tree import RepertoireTree, WHITE, BLACK  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _win(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    win = mw.MainWindow()
    monkeypatch.setattr(win._eval_settings, "setValue", lambda *a, **k: None)  # keine echten QSettings
    return win


def _tree(name, side, ucis):
    t = RepertoireTree.new(name, side)
    p = t.root_id
    for u in ucis:
        p = t.add_child(p, u).id
    return t


def test_appearance_switch_keeps_board_colour(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    win._set_board_theme("wood")
    assert win._board_theme == "wood"
    win._set_ui_theme("dark")
    assert win._board_theme == "wood"          # Hell/Dunkel überschreibt die Brettfarbe NICHT
    win._set_ui_theme("light")
    assert win._board_theme == "wood"
    win._set_board_theme("green")              # globalen Brett-Zustand zurücksetzen


def test_solution_hint_is_germanised(tmp_path, monkeypatch):
    monkeypatch.setattr(mw.i18n, "language", lambda: "de")
    win = _win(tmp_path, monkeypatch)
    tree = _tree("Italienisch", WHITE, ["g1f3"])   # einziger Zug: Nf3 -> Sf3
    win.tree_store.add(tree)
    win._drill_learn_new = False
    win._start_tree_drill(tree)
    win._tree_drill_solution()
    txt = win.tree_drill_status.text()
    assert "Sf3" in txt and "Nf3" not in txt


def test_language_switch_preserves_reptree_family(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    win.tree_store.add(_tree("Caro", BLACK, ["e2e4", "c7c6", "d2d4", "d7d5"]))
    win.tree_store.add(_tree("Skandi", BLACK, ["e2e4", "d7d5", "e4d5", "d8d5"]))
    win._open_repertoire_tree()
    win.reptree_side_combo.setCurrentIndex(1)      # Schwarz
    win._reptree_refresh_families()
    fam = win._tree_family(next(t for t in win.tree_store.by_side("black") if t.name == "Skandi"))
    win.reptree_family_combo.setCurrentIndex(win.reptree_family_combo.findData(fam))
    win._apply_language_live()                     # Sprache live umschalten (Neuaufbau)
    assert win.reptree_family_combo.currentData() == fam   # Auswahl überlebt
