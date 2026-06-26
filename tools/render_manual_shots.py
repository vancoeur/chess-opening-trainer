"""Rendert die Screenshots fürs Bedienungshandbuch nach docs/handbuch/.

Lädt ein kleines Beispiel-Repertoire (Caro-Kann, deutsch), seedet etwas
Trainingshistorie und fotografiert jede wichtige Seite offscreen.

Aufruf:  QT_QPA_PLATFORM=offscreen PYTHONPATH=. python3 tools/render_manual_shots.py
"""
import os, tempfile, pathlib, chess
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6 import QtWidgets

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "docs/handbuch"
OUT.mkdir(parents=True, exist_ok=True)

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
import qt_app.main_window as mw
tmp = pathlib.Path(tempfile.mkdtemp()); data = tmp / "data"; data.mkdir()
mw.data_dir = lambda: data
win = mw.MainWindow(); win._set_language("de")
win._set_ui_theme("light")          # Handbuch zeigt den hellen Standard-Look

pgn = '''[Event "x"]
[ChapterName "B18 · Caro-Kann: Klassisch"]

1. e4 c6 2. d4 d5 3. Nc3 dxe4 4. Nxe4 Bf5 5. Ng3 Bg6 *

[Event "x"]
[ChapterName "B12 · Caro-Kann: Vorstoss"]

1. e4 c6 2. d4 d5 3. e5 Bf5 4. Nf3 e6 *

[Event "x"]
[ChapterName "B10 · Caro-Kann: Zwei Springer"]

1. e4 c6 2. Nc3 d5 3. Nf3 *

[Event "x"]
[ChapterName "B01 · Skandinavisch"]

1. e4 d5 2. exd5 Qxd5 3. Nc3 Qa5 *
'''
f = tmp / "Schwarz Caro.pgn"; f.write_text(pgn, encoding="utf-8")
win._add_pgn_source(str(f)); win._auto_fill_sides_by_filename()


def fen(ucis):
    b = chess.Board()
    for u in ucis:
        b.push(chess.Move.from_uci(u))
    return b.fen()


def ev(ucis, exp, pl, ok):
    win.stats_store.add_event(source_name="s", line_name="l", fen_before=fen(ucis),
                              expected_san=exp, played_san=pl, correct=ok)


for _ in range(3):
    ev(["e2e4", "c7c6", "d2d4", "d7d5", "b1c3"], "dxe4", "dxe4", True)
ev(["e2e4", "c7c6", "d2d4", "d7d5", "b1c3"], "dxe4", "Nf6", False)
ev(["e2e4", "d7d5", "e4d5"], "Qxd5", "Qxd5", True)

win.resize(1120, 720)


def shot(name):
    app.processEvents(); win.grab().save(str(OUT / f"{name}.png")); print("shot:", name)


win._go_home(); shot("01_start")
win._open_due_overview(); shot("02_heute_faellig")
win._drill_learn_new = True; win._start_due_session(); shot("03_uebe_learn")
win._drill_learn_new = False; win._start_due_session(); shot("04_uebe_abfrage")
win._open_repertoire_tree(); shot("05_repertoire_baum")
win._open_editor(); shot("06_editor")
win._open_tuv(); shot("07_pruefung")
win._player_name = "Achim"; win._open_game_review(); shot("08_partien")
win._open_progress(); shot("09_fortschritt")
win._open_stats(); shot("10_trefferquote")
win._open_library(); shot("11_bibliothek")
print("Fertig ->", OUT)
