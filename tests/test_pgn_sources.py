"""Loading PGN ADDS sources instead of replacing; multiple sources merge + dedupe."""
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets, QtCore  # noqa: E402

from opening_trainer.settings_store import SettingsStore, AppSettings  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

SAMPLE = Path(__file__).resolve().parent.parent / "assets" / "sample" / "sample_openings.pgn"

PGN_EXTRA = """[Event "Extra"]
[ChapterName "Extra-Linie"]

1. g3 d5 2. Bg2 *
"""


def test_settings_pgn_sources_round_trip(tmp_path):
    store = SettingsStore(AppSettings(pgn_sources=("/a/x.pgn", "/b")))
    p = tmp_path / "settings.json"
    store.save(p)
    loaded = SettingsStore.load(p)
    assert loaded.settings.pgn_sources == ("/a/x.pgn", "/b")


def test_load_pgn_adds_and_dedupes(tmp_path, monkeypatch):
    import qt_app.main_window as mw
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    win = mw.MainWindow()
    assert win.lines == []

    # erste Quelle: die 3 Beispiel-Eröffnungen
    added1 = win._add_pgn_source(str(SAMPLE))
    assert added1 == 3 and len(win.lines) == 3

    # zweite Quelle hinzufügen (ersetzt NICHT)
    extra = tmp_path / "extra.pgn"
    extra.write_text(PGN_EXTRA, encoding="utf-8")
    added2 = win._add_pgn_source(str(extra))
    assert added2 == 1 and len(win.lines) == 4         # beide Quellen vorhanden

    # dieselbe Quelle erneut -> keine Dubletten, keine zweite Quelle
    added3 = win._add_pgn_source(str(SAMPLE))
    assert added3 == 0 and len(win.lines) == 4
    assert win.settings_store.settings.pgn_sources.count(str(SAMPLE)) == 1

    # nach Neustart (neue Instanz, gleicher Datenordner) bleiben beide Quellen geladen
    win2 = mw.MainWindow()
    assert len(win2.lines) == 4


def test_clear_repertoire_empties_sources(tmp_path, monkeypatch):
    import qt_app.main_window as mw
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    win = mw.MainWindow()
    win._add_pgn_source(str(SAMPLE))
    assert len(win.lines) == 3
    # _reset_repertoire fragt nach; den Dialog mit „Yes" beantworten
    monkeypatch.setattr(QtWidgets.QMessageBox, "question",
                        staticmethod(lambda *a, **k: QtWidgets.QMessageBox.StandardButton.Yes))
    win._reset_repertoire()
    assert win.lines == []
    assert win.settings_store.settings.pgn_sources == ()


def test_remove_one_source_keeps_the_others(tmp_path, monkeypatch):
    import qt_app.main_window as mw
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    win = mw.MainWindow()
    extra = tmp_path / "extra.pgn"
    extra.write_text(PGN_EXTRA, encoding="utf-8")
    win._add_pgn_source(str(SAMPLE))
    win._add_pgn_source(str(extra))
    assert len(win.lines) == 4

    win._remove_pgn_source(str(extra))
    assert len(win.lines) == 3                       # nur die Extra-Quelle weg
    assert str(extra) not in win.settings_store.settings.pgn_sources
    assert str(SAMPLE) in win.settings_store.settings.pgn_sources


def test_legacy_fallback_keeps_both_file_and_folder(tmp_path, monkeypatch):
    """Alt-Settings (nur last_pgn_*) dürfen weder Datei noch Ordner verwerfen."""
    import qt_app.main_window as mw
    from opening_trainer.settings_store import SettingsStore, AppSettings
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    win = mw.MainWindow()
    # Zustand wie ein altes Bundle: pgn_sources leer, beide Einzelfelder gesetzt
    win.settings_store = SettingsStore(AppSettings(
        last_pgn_folder="/Users/x/Repertoire",
        last_pgn_path="/Users/x/stray.pgn",
    ))
    assert win._effective_sources() == ["/Users/x/Repertoire", "/Users/x/stray.pgn"]


def test_editor_delete_tree_with_confirmation(tmp_path, monkeypatch):
    import qt_app.main_window as mw
    from opening_trainer.repertoire_tree import RepertoireTree
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    win = mw.MainWindow()
    a = RepertoireTree.new("A", "white")
    b = RepertoireTree.new("B", "black")
    win.tree_store.add(a)
    win.tree_store.add(b)
    win.editor_tree = a
    monkeypatch.setattr(QtWidgets.QMessageBox, "warning",
                        staticmethod(lambda *args, **k: QtWidgets.QMessageBox.StandardButton.Yes))
    win._editor_delete_tree()
    assert a.id not in win.tree_store.trees           # gelöscht
    assert b.id in win.tree_store.trees               # der andere bleibt
