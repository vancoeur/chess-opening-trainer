from __future__ import annotations

from datetime import date
from pathlib import Path
import random

import json

import chess
import chess.pgn
from PySide6 import QtCore, QtGui, QtWidgets, QtNetwork

from opening_trainer.pgn_loader import load_pgn_file, load_pgn_folder
from opening_trainer.settings_store import SettingsStore
from opening_trainer.schedule_store import ScheduleStore
from opening_trainer.stats_store import StatsStore
from opening_trainer.scheduler import is_new
from opening_trainer.repertoire import SIDE_WHITE, SIDE_BLACK
from opening_trainer.repertoire_store import RepertoireStore
from opening_trainer.opening_sides import OpeningSides, side_from_name
from opening_trainer.line_notes import LineNotes
from opening_trainer.session_log import overall_progress
from opening_trainer.engine_review import sparring_strength, is_blunder_move
from opening_trainer.scheduler import review as schedule_review
from opening_trainer.training_state import TrainingState
from opening_trainer.repertoire_tree_store import RepertoireTreeStore
from opening_trainer.position_schedule_store import PositionScheduleStore
from opening_trainer.migration_v2 import run_migration
from opening_trainer.tree_sync import sync_auto_trees
from opening_trainer.catalog import build_catalog
from qt_app.board_view import (
    BoardView, EvalBar, MasteryBar, WdlBar, BOARD_THEMES, set_board_theme,
    set_ui_palette,
)
from qt_app import i18n
from qt_app.i18n import t
from opening_trainer.mastery import mastery_bucket, summarize_mastery
from opening_trainer.explorer import parse_explorer_response, percent
from opening_trainer.game_review import review_game
from opening_trainer.position_book import build_san_book
from opening_trainer.opening_names_en import to_english
from qt_app.paths import data_dir, sample_pgn_path

# Zwei Oberflächen-Themes: HELL = ruhiges Blau mit dezent hellblauem Hintergrund,
# DUNKEL = warmes Anthrazit mit kräftigem Grün (chess.com-Stil). Das Aussehen hängt
# komplett an EINEM Stylesheet aus diesen Paletten — Umschalten ändert nur die Palette.
UI_THEMES = {
    "light": dict(
        bg="#eff6fd", card="#ffffff", side="#dfeaf8", header="#dfeaf8",
        text="#1b232c", muted="#5f6a76", border="#d2def0", neutral="#ccd9e8",
        accent="#3a86c8", accent_h="#2f72ad", accent_dis="#bcd9ee", on_accent_dis="#ffffff",
        hover="#d0e3f5", press="#c3dbf2", sel="#cee2f6", scroll="#b6c8db", herotint="#d9e8f8",
    ),
    "dark": dict(
        bg="#302e2a", card="#3a3834", side="#24221f", header="#24221f",
        text="#ededeb", muted="#a8a7a1", border="#46433d", neutral="#46433d",
        accent="#81b64c", accent_h="#8fc257", accent_dis="#4a5a36", on_accent_dis="#9a9a92",
        hover="#2f2d29", press="#403d37", sel="#38402d", scroll="#514d47", herotint="#33402a",
    ),
}
# Passende Brettfarbe je Oberflächen-Theme (klassisches Grün passt zu beiden).
THEME_BOARD = {"light": "green", "dark": "green"}


# Typografie: durchgängig klare, serifenlose Schrift (Lucida Grande — klassischer,
# ruhiger Mac-App-Look), auch für Überschriften. FONT_SERIF zeigt bewusst auf
# dieselbe Schrift, damit nirgends Serifen erscheinen.
FONT_SANS = "'Lucida Grande', -apple-system, 'Helvetica Neue', Arial, sans-serif"
FONT_SERIF = FONT_SANS


def build_style(t: dict) -> str:
    return f"""
QWidget {{ background: {t['bg']}; color: {t['text']}; font-family: {FONT_SANS}; font-size: 14px; }}
QLabel#name, QLabel#brand, QLabel#heroT, QLabel#cardN, QLabel#cathead, QLabel#navgroup {{ font-family: {FONT_SERIF}; }}
QLabel {{ background: transparent; color: {t['text']}; }}
QLabel#eyebrow {{ color: {t['accent']}; font-size: 12px; font-weight: 700; }}
QLabel#pagehead {{ background: {t['header']}; color: {t['text']}; font-size: 15px; font-weight: 700; padding: 11px 20px; border-bottom: 1px solid {t['border']}; }}
QLabel#name    {{ font-size: 27px; font-weight: 800; color: {t['text']}; }}
QLabel#hint    {{ color: {t['muted']}; font-size: 14px; }}
QLabel#note    {{ color: {t['muted']}; font-size: 13px; font-style: italic; }}
QLabel#status  {{ font-size: 15px; color: {t['text']}; }}
QLabel#due     {{ color: {t['muted']}; font-size: 13px; }}
QLabel#empty   {{ color: {t['muted']}; font-size: 16px; }}
QLabel#rowname {{ font-size: 15px; font-weight: 600; color: {t['text']}; }}
QLabel#rowsub  {{ font-size: 12px; color: {t['muted']}; }}
QLabel#duename {{ font-size: 13px; font-weight: 600; color: {t['text']}; }}
QLabel#cathead {{ color: {t['text']}; font-size: 18px; font-weight: 800; padding: 14px 4px 6px 4px; }}
QLabel#subhead {{ color: {t['accent']}; font-size: 14px; font-weight: 700; padding: 8px 4px 3px 22px; }}

QPushButton {{ background: {t['card']}; border: 1px solid {t['border']}; border-radius: 11px; padding: 9px 15px; color: {t['text']}; font-weight: 600; }}
QPushButton:hover {{ background: {t['hover']}; border-color: {t['accent']}; }}
QPushButton:pressed {{ background: {t['press']}; }}
QPushButton:disabled {{ background: {t['card']}; color: {t['muted']}; border-color: {t['border']}; }}
QPushButton#primary {{ background: {t['accent']}; border: none; color: white; font-weight: 700; padding: 11px 18px; }}
QPushButton#primary:hover {{ background: {t['accent_h']}; }}
QPushButton#primary:disabled {{ background: {t['accent_dis']}; color: {t['on_accent_dis']}; }}
QPushButton#more {{ background: {t['card']}; border: 1px solid {t['border']}; border-radius: 11px; padding: 9px 15px; color: {t['text']}; font-weight: 600; }}
QPushButton#more:hover {{ background: {t['hover']}; border-color: {t['accent']}; }}
QPushButton#more:pressed {{ background: {t['press']}; }}
QPushButton#more:disabled {{ background: {t['card']}; color: {t['muted']}; border-color: {t['border']}; }}
QPushButton#seg {{ background: {t['card']}; border: 1px solid {t['border']}; border-radius: 9px; padding: 7px 14px; color: {t['text']}; }}
QPushButton#seg:hover {{ background: {t['hover']}; }}
QPushButton#seg:checked {{ background: {t['accent']}; border: 1px solid {t['accent']}; color: white; font-weight: 700; }}

/* Seitenleiste (feste Navigation links) */
QWidget#sidebar {{ background: {t['side']}; border-right: 1px solid {t['border']}; }}
QLabel#brand {{ font-size: 17px; font-weight: 800; color: {t['text']}; padding: 2px 6px 2px 6px; }}
QLabel#navgroup {{ color: {t['muted']}; font-size: 11px; font-weight: 700; padding: 14px 8px 4px 8px; }}
QPushButton#nav {{ text-align: left; background: transparent; border: none; border-radius: 9px; padding: 9px 12px; color: {t['text']}; font-size: 14px; font-weight: 500; }}
QPushButton#nav:hover {{ background: {t['sel']}; }}
QPushButton#navon {{ text-align: left; background: {t['accent']}; border: none; border-radius: 9px; padding: 9px 12px; color: white; font-size: 14px; font-weight: 700; }}

/* Dashboard-Karten der Startseite */
QFrame#hero {{ background: {t['herotint']}; border: 1px solid {t['accent']}; border-radius: 16px; }}
QFrame#statcard {{ background: {t['card']}; border: 1px solid {t['border']}; border-radius: 14px; }}
QLabel#heroT {{ font-size: 21px; font-weight: 800; color: {t['text']}; }}
QLabel#cardN {{ font-size: 26px; font-weight: 800; color: {t['text']}; }}
QLabel#cardL {{ font-size: 13px; color: {t['muted']}; }}

QWidget#libraryrow {{ background: transparent; }}
QListWidget#library {{ background: transparent; border: none; }}
QListWidget#library::item {{ background: transparent; border: none; margin: 3px 0; }}
QListWidget#library::item:enabled {{ background: {t['card']}; border: 1px solid {t['border']}; border-radius: 10px; color: {t['text']}; }}
QListWidget#library::item:hover:enabled {{ background: {t['hover']}; }}
QListWidget#library::item:selected {{ background: {t['sel']}; border: 1px solid {t['accent']}; color: {t['text']}; }}

QLineEdit#search {{ font-size: 15px; padding: 10px 14px; margin: 2px 0 6px 0; border: 1px solid {t['border']}; border-radius: 11px; background: {t['card']}; color: {t['text']}; }}
QLineEdit#search:focus {{ border-color: {t['accent']}; }}

QComboBox {{ background: {t['card']}; border: 1px solid {t['border']}; border-radius: 9px; padding: 7px 12px; color: {t['text']}; }}
QComboBox:hover {{ border-color: {t['accent']}; }}
QComboBox QAbstractItemView {{ background: {t['card']}; color: {t['text']}; selection-background-color: {t['accent']}; selection-color: white; }}

QMenuBar {{ background: {t['header']}; color: {t['text']}; }}
QMenuBar::item:selected {{ background: {t['sel']}; }}
QMenu {{ background: {t['card']}; color: {t['text']}; border: 1px solid {t['border']}; }}
QMenu::item:selected {{ background: {t['accent']}; color: white; }}

QScrollBar:vertical   {{ background: transparent; width: 12px; margin: 0; border-radius: 6px; }}
QScrollBar:horizontal {{ background: transparent; height: 12px; margin: 0; border-radius: 6px; }}
QScrollBar::handle:vertical   {{ background: {t['scroll']}; min-height: 36px; border-radius: 6px; }}
QScrollBar::handle:horizontal {{ background: {t['scroll']}; min-width: 36px;  border-radius: 6px; }}
QScrollBar::handle:hover {{ background: {t['accent']}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; background: none; border: none; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
"""


APP_VERSION = "1.4.0"
REPO_URL = "https://github.com/vancoeur/chess-opening-trainer"

# Eine »Schwächen üben«-Runde nimmt höchstens so viele Stellungen (hartnäckigste
# zuerst), damit sie nicht uferlos lang wird. Gibt es mehr offene Fehler, bleibt
# der Rest für die nächste Runde.
WEAK_SESSION_LIMIT = 15

# Länge eines Blitz-Sprints in Sekunden (Tempo-Auffrischung).
BLITZ_SECONDS = 60

# Stichwort -> Eröffnungs-Familie (erste passende Übereinstimmung gewinnt)
_FAMILY_KEYWORDS = [
    ("sizilian", "Sizilianisch"), ("alapin", "Sizilianisch"),
    ("caro", "Caro-Kann"),
    ("franz", "Französisch"), ("french", "Französisch"),
    ("vier-springer", "Vier-Springer"), ("vierspringer", "Vier-Springer"),
    ("zwei-springer", "Italienisch"), ("giuoco", "Italienisch"), ("italien", "Italienisch"),
    ("evans", "Italienisch"), ("ungarisch", "Italienisch"),
    ("ruy", "Spanisch (Ruy López)"), ("spanisch", "Spanisch (Ruy López)"),
    ("pirc", "Pirc/Modern"), ("moderne", "Pirc/Modern"),
    ("königsgambit", "Königsgambit"), ("koenigsgambit", "Königsgambit"),
    ("skandinav", "Skandinavisch"),
    ("russisch", "Russisch (Petrow)"), ("petrow", "Russisch (Petrow)"),
    ("aljechin", "Aljechin"), ("alekhin", "Aljechin"),
    ("wiener", "Wiener Partie"), ("schottisch", "Schottische Partie"),
    ("königsindisch", "Königsindisch"), ("koenigsindisch", "Königsindisch"),
    ("nimzo", "Nimzo-Indisch"),
    ("damenindisch", "Damenindisch"), ("bogo", "Damenindisch/Bogo"),
    ("grünfeld", "Grünfeld"), ("grunfeld", "Grünfeld"),
    ("slawisch", "Slawisch"), ("slav", "Slawisch"),
    ("damen-gambit", "Damengambit"), ("damengambit", "Damengambit"),
    ("katalan", "Katalanisch"), ("catalan", "Katalanisch"),
    ("london", "London-System"),
    ("holländ", "Holländisch"), ("dutch", "Holländisch"),
    ("benoni", "Benoni/Benkö"), ("benkö", "Benoni/Benkö"), ("benko", "Benoni/Benkö"),
    ("budapest", "Budapester Gambit"), ("schmetterling", "Schmetterlingsindisch"),
    ("englisch", "Englisch"), ("english", "Englisch"),
]

# Englische Anzeigenamen der Eröffnungsfamilien (für den Englisch-Modus).
_FAMILY_EN = {
    "Sizilianisch": "Sicilian",
    "Caro-Kann": "Caro-Kann",
    "Französisch": "French",
    "Vier-Springer": "Four Knights",
    "Italienisch": "Italian",
    "Spanisch (Ruy López)": "Ruy López (Spanish)",
    "Pirc/Modern": "Pirc/Modern",
    "Königsgambit": "King's Gambit",
    "Skandinavisch": "Scandinavian",
    "Russisch (Petrow)": "Petroff (Russian)",
    "Aljechin": "Alekhine",
    "Wiener Partie": "Vienna Game",
    "Schottische Partie": "Scotch Game",
    "Königsindisch": "King's Indian",
    "Nimzo-Indisch": "Nimzo-Indian",
    "Damenindisch": "Queen's Indian",
    "Damenindisch/Bogo": "Queen's Indian / Bogo",
    "Grünfeld": "Grünfeld",
    "Slawisch": "Slav",
    "Damengambit": "Queen's Gambit",
    "Katalanisch": "Catalan",
    "London-System": "London System",
    "Holländisch": "Dutch",
    "Benoni/Benkö": "Benoni / Benko",
    "Budapester Gambit": "Budapest Gambit",
    "Schmetterlingsindisch": "Schmetterlingsindisch",
    "Englisch": "English",
}


class _TuvPath:
    """Ein Wurzel-zu-Blatt-Pfad (Repertoire-Variante) als Prüf-Job. Quakt wie
    eine Line (``.name``/``.moves_uci``) für den unveränderten Worker und die
    Ergebnis-Anzeige, trägt zusätzlich den ``tree`` fürs gezielte Üben."""

    __slots__ = ("name", "moves_uci", "tree")

    def __init__(self, name, moves_uci, tree) -> None:
        self.name = name
        self.moves_uci = moves_uci
        self.tree = tree


class _TuvWorker(QtCore.QObject):
    """Läuft im Hintergrund-Thread: prüft jede Repertoire-Variante mit Stockfish."""

    progress = QtCore.Signal(int, int, str)   # erledigt, gesamt, Linienname
    finished = QtCore.Signal(list)            # [{"line": …, "issues": [MoveIssue, …]}]
    failed = QtCore.Signal(str)               # Fehlertext ("nostockfish" o. Ä.)

    def __init__(self, jobs: list) -> None:
        super().__init__()
        self._jobs = jobs                     # [(line, chess.Color), …]
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:
        import chess.engine
        from qt_app.engine import find_stockfish, review_line

        sf = find_stockfish()
        if sf is None:
            self.failed.emit("nostockfish")
            return
        try:
            engine = chess.engine.SimpleEngine.popen_uci(str(sf))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
            return

        limit = chess.engine.Limit(depth=12)
        results: list = []
        total = len(self._jobs)
        try:
            for i, (line, side) in enumerate(self._jobs, 1):
                if self._cancel:
                    break
                self.progress.emit(i, total, line.name)
                issues = review_line(engine, line.moves_uci, side, limit)
                if issues:
                    results.append({"line": line, "issues": issues})
        finally:
            try:
                engine.quit()
            except Exception:  # noqa: BLE001
                pass
        self.finished.emit(results)




class _SparringWorker(QtCore.QObject):
    """Spielt im Hintergrund-Thread Stockfishs Antwortzug (gedrosselte Stärke)
    und liefert die Bewertung der Stellung danach. Eigene Engine-Instanz."""

    # angefragte_fen, zug_uci, eval_nach_Achims_Zug(Weiß-cp), eval_nach_Antwort(Weiß-cp), mate
    played = QtCore.Signal(str, str, int, int, int)
    evaluated = QtCore.Signal(str, int, int)     # fen, cp(Weiß), mate (für Bar-Auffrischung)
    game_over = QtCore.Signal(str)               # angefragte_fen (Engine hat keinen Zug)
    failed = QtCore.Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._engine = None
        self._broken = False

    def _start_engine(self):
        import chess.engine
        if self._engine is None and not self._broken:
            from qt_app.engine import find_stockfish
            sf = find_stockfish()
            if sf is None:
                self._broken = True
                self.failed.emit("nostockfish")
                return None
            try:
                self._engine = chess.engine.SimpleEngine.popen_uci(str(sf))
            except Exception as exc:  # noqa: BLE001
                self._broken = True
                self.failed.emit(str(exc))
                return None
        return self._engine

    @staticmethod
    def _white_eval(info) -> tuple[int, int]:
        score = info["score"].white()
        mate = score.mate() or 0
        cp = 0 if mate else (score.score() or 0)
        return int(cp), int(mate)

    @QtCore.Slot(str)
    def evaluate(self, fen: str) -> None:
        import chess
        import chess.engine
        engine = self._start_engine()
        if engine is None:
            return
        try:
            cp, mate = self._white_eval(engine.analyse(chess.Board(fen), chess.engine.Limit(depth=10)))
            self.evaluated.emit(fen, cp, mate)
        except Exception:  # noqa: BLE001
            pass

    @QtCore.Slot(str, int, int)
    def play(self, fen: str, skill: int, movetime_ms: int) -> None:
        import chess
        import chess.engine
        engine = self._start_engine()
        if engine is None:
            return
        try:
            board = chess.Board(fen)
            if board.is_game_over():
                self.game_over.emit(fen)
                return
            # Bewertung direkt nach Achims Zug (für den Patzer-Hinweis)
            e1_cp, e1_mate = self._white_eval(engine.analyse(board, chess.engine.Limit(depth=10)))
            e1 = e1_mate * 10000 if e1_mate else e1_cp
            engine.configure({"Skill Level": int(skill)})
            result = engine.play(board, chess.engine.Limit(time=movetime_ms / 1000.0))
            if result.move is None:
                self.game_over.emit(fen)
                return
            board.push(result.move)
            e2_cp, e2_mate = self._white_eval(engine.analyse(board, chess.engine.Limit(depth=10)))
            self.played.emit(fen, result.move.uci(), int(e1), int(e2_cp), int(e2_mate))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))

    @QtCore.Slot()
    def shutdown(self) -> None:
        if self._engine is not None:
            try:
                self._engine.quit()
            except Exception:  # noqa: BLE001
                pass
            self._engine = None


class _GameAnalysisWorker(QtCore.QObject):
    """Prüft im Hintergrund die eigenen Züge EINER gespielten Partie mit
    Stockfish (per review_line) und meldet die Patzer/Ungenauigkeiten."""

    done = QtCore.Signal(list)     # list[MoveIssue]
    failed = QtCore.Signal(str)

    def __init__(self, moves_uci: list, side: int) -> None:
        super().__init__()
        self._moves = moves_uci
        self._side = side

    @QtCore.Slot()
    def run(self) -> None:
        import chess.engine
        from qt_app.engine import find_stockfish, review_line
        sf = find_stockfish()
        if sf is None:
            self.failed.emit("nostockfish")
            return
        try:
            engine = chess.engine.SimpleEngine.popen_uci(str(sf))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
            return
        try:
            issues = review_line(engine, self._moves, self._side, chess.engine.Limit(depth=12))
            self.done.emit(issues)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
        finally:
            try:
                engine.quit()
            except Exception:  # noqa: BLE001
                pass


class MainWindow(QtWidgets.QMainWindow):
    _sparRequested = QtCore.Signal(str, int, int)
    _sparEvalRequested = QtCore.Signal(str)
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Opening Trainer")

        data = data_dir()
        self.settings_path = data / "settings.json"
        self.settings_store = SettingsStore.load(self.settings_path)
        self.schedule_path = data / "schedule.json"
        self.schedule_store = ScheduleStore.load(self.schedule_path)
        self.stats_path = data / "training_stats.json"
        self.stats_store = StatsStore.load(self.stats_path)
        self.repertoire_store = RepertoireStore.load(data / "repertoire.json")
        self.sides_path = data / "opening_sides.json"
        self.opening_sides = OpeningSides.load(self.sides_path)
        self.notes_path = data / "line_notes.json"
        self.line_notes = LineNotes.load(self.notes_path)
        self._side_filter = None  # None=alle, "white", "black", "none"
        self.search_query = ""
        self._progress_filter = "alle"  # Fortschritt-Filter: alle | sitzt | wackelt | neu
        self._explorer_board = None      # chess.Board des Explorer-Browsens
        self._explorer_seed_plies = 0
        self._explorer_cache: dict = {}  # fen -> ExplorerResult (schont die API)
        self._explorer_nam = None        # QNetworkAccessManager (lazy)
        # Legacy-Linien NUR für die einmalige Migration parsen — NICHT als Dauer-
        # zustand halten. Die Bibliothek/Partien/Seiten-Zuordnung leiten ihre
        # Eröffnungen jetzt aus den Bäumen ab (siehe _catalog()).
        legacy_lines = self._load_lines()
        self._migrate_sides_from_groups(legacy_lines)
        self.train_color = chess.BLACK if self.settings_store.settings.train_color == "black" else chess.WHITE

        # Repertoire-Bäume sind die alleinige Datenhaltung: einmalige, idempotente
        # Migration der linearen Bestandsdaten, danach laden + synchronisieren.
        self.trees_path = data / "repertoire_trees.json"
        self.position_schedule_path = data / "position_schedule.json"
        try:
            run_migration(data, legacy_lines)
        except Exception:  # noqa: BLE001 — die Migration darf den Start nie verhindern
            pass
        self.tree_store = RepertoireTreeStore.load(self.trees_path)
        self.position_schedule = PositionScheduleStore.load(self.position_schedule_path)
        # Auto-Bäume + Positions-Karten aus den aktuell geladenen Quellen erzeugen,
        # damit die positions-basierte Tagessitzung für JEDES geladene Repertoire
        # funktioniert (nicht nur die einmal-migrierten Daten). ADDITIV.
        self._sync_auto_trees()

        self.training: TrainingState | None = None
        self.current_line = None
        self.editor_tree = None        # aktuell bearbeiteter RepertoireTree
        self.editor_node = None        # aktueller Knoten (ID) im Editor
        self._editor_pos = chess.Board()
        self._tree_trainer = None      # PositionTrainer für das Baum-Üben
        self._tree_drill_wrong = False
        self._drill_tree = None        # aktuell geübter Baum
        self._drill_manual = False     # True: Gegnerzüge selbst spielen
        self._drill_learn_new = True   # neue Stellungen erst zeigen (Learn-Modus)
        self._drill_learn_active = False  # aktuell wird eine neue Stellung „gelernt"
        self._due_session = False      # True: „Heute fällig (Bäume)"-Sitzung läuft
        self._due_queue: list = []     # offene fällige Stellungen (tree, node_id, color)
        self._due_total = 0
        # Blitz-Sprint (Tempo-Auffrischung): eigener Modus neben _due_session,
        # rührt Lernplan/Statistik NICHT an — zählt nur den Punktestand.
        self._blitz = False
        self._blitz_score = 0
        self._blitz_pool: list = []    # voller Vorrat, aus dem die Runde nachfüllt
        self._blitz_remaining = 0
        self._blitz_over = False
        self._blitz_timer = QtCore.QTimer(self)
        self._blitz_timer.setInterval(1000)
        self._blitz_timer.timeout.connect(self._blitz_tick)
        self._had_wrong = False
        self._queue: list = []
        self._drill = False
        self._drill_queue: list = []
        self._drill_current = None
        self._drill_board = None

        self._eval_settings = QtCore.QSettings("OpeningTrainer", "OpeningTrainer")
        # Ohne gespeicherte Wahl folgt die Sprache der Systemsprache des Macs.
        _sys_lang = "de" if QtCore.QLocale.system().name().startswith("de") else "en"
        i18n.set_language(self._eval_settings.value("language", _sys_lang, type=str))
        # Brettfarbe aus den Einstellungen anwenden, bevor die Bretter gebaut werden.
        self._board_theme = self._eval_settings.value("board_theme", "green", type=str)
        if self._board_theme not in BOARD_THEMES:
            self._board_theme = "green"
        set_board_theme(self._board_theme)
        # Oberflächen-Theme (hell/dunkel) — wird im Stylesheet angewandt.
        self._ui_theme = self._eval_settings.value("ui_theme", "light", type=str)
        if self._ui_theme not in UI_THEMES:
            self._ui_theme = "light"
        _pal = UI_THEMES[self._ui_theme]
        set_ui_palette(_pal["muted"], _pal["border"], _pal["neutral"])
        self._show_eval_bar = self._eval_settings.value("show_eval_bar", True, type=bool)
        from qt_app.engine import find_stockfish
        self._stockfish_available = find_stockfish() is not None

        self._spar_thread = None
        self._spar_worker = None
        self._spar_board = None          # chess.Board des laufenden Sparrings
        self._spar_color = chess.WHITE   # Farbe, die Achim spielt
        self._spar_level = self._eval_settings.value("spar_level", "mittel", type=str)
        self._spar_thinking = False
        self._spar_floor_plies = 0       # bis hierher darf „Zug zurück" gehen (Eröffnungsstellung)
        self._spar_prev_eval = None      # Bewertung (Weiß-cp) vor Achims Zug, für Patzer-Hinweis
        self._spar_judge = False         # nächste Engine-Antwort betrifft einen Zug von Achim?
        self._lichess_token = self._eval_settings.value("lichess_token", "", type=str)
        self._player_name = self._eval_settings.value("player_name", "", type=str)
        self._viewer_moves: list = []
        self._viewer_pos = 0
        self._viewer_dev = None
        self._viewer_drill_fen = None
        self._viewer_color = chess.WHITE
        self._viewer_issues: dict = {}   # ply -> MoveIssue (Stockfish-Patzer der Partie)
        self._viewer_anal_thread = None
        self._viewer_anal_worker = None

        self._threads_stopped = False
        # Navigations-Historie: »Zurück« führt zur zuletzt besuchten Seite.
        self._nav_history: list[int] = []
        self._nav_current = 0
        self._nav_suppress = False
        # App-Standardschrift = Avenir Next, BEVOR Widgets gebaut werden: sonst
        # berechnen Listen ihre Zeilenhöhe noch mit der alten (niedrigeren)
        # Schrift und schneiden Unterlängen (g, y, p) ab. Pixelgröße leicht über
        # der größten Zeilen-Schrift (15 px), damit nichts klemmt.
        _app0 = QtWidgets.QApplication.instance()
        if _app0 is not None:
            _f = QtGui.QFont("Avenir Next")
            _f.setPixelSize(16)
            _app0.setFont(_f)
        self._build_ui()
        self._build_menu()
        self._install_shortcuts()
        self._restore_geometry()
        # Threads sicher beenden, EGAL wie die App geschlossen wird (⌘Q, app.quit(),
        # letztes Fenster zu) — closeEvent allein deckt nicht alle Beende-Wege ab,
        # sonst zerstört Qt beim Interpreter-Shutdown noch laufende Worker → SIGABRT.
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._stop_all_threads)
        pass
        pass
        # Primäre Tagessitzung ist die stellungs-basierte Wiederholung: beim Start
        # dorthin springen, wenn etwas fällig/neu ist (sonst auf der Startseite bleiben).
        self._open_default_session()

    # --- Menü / Tastatur / Fenster ---------------------------------------

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu(t("Datei", "File"))
        load_act = file_menu.addAction(t("PGN laden …", "Load PGN …"))
        load_act.setShortcut(QtGui.QKeySequence.StandardKey.Open)          # ⌘O
        load_act.triggered.connect(lambda: self._load_pgn_dialog())
        folder_act = file_menu.addAction(t("Ordner laden …", "Load folder …"))
        folder_act.setShortcut(QtGui.QKeySequence("Shift+Ctrl+O"))         # ⇧⌘O
        folder_act.triggered.connect(lambda: self._load_folder_dialog())
        file_menu.addSeparator()
        manage_act = file_menu.addAction(t("Geladene Repertoires verwalten …", "Manage loaded repertoires …"))
        manage_act.triggered.connect(self._manage_sources)
        trees_act = file_menu.addAction(t("Eigene Bäume verwalten/aufräumen …", "Manage/clean custom trees …"))
        trees_act.triggered.connect(self._manage_trees)
        reset_act = file_menu.addAction(t("Repertoire leeren …", "Clear repertoire …"))
        reset_act.triggered.connect(self._reset_repertoire)

        # (Das frühere »Gehe zu«-Menü ist entfallen — die feste Seitenleiste links
        #  übernimmt die Navigation. Die gewohnten Tastenkürzel bleiben über
        #  _install_shortcuts erhalten.)

        view_menu = self.menuBar().addMenu(t("Ansicht", "View"))

        appearance_menu = view_menu.addMenu(t("Erscheinungsbild", "Appearance"))
        self._theme_actions = {}
        appearance_group = QtGui.QActionGroup(self)
        for code, label in [("light", t("Hell", "Light")), ("dark", t("Dunkel", "Dark"))]:
            act = appearance_menu.addAction(label)
            act.setCheckable(True)
            act.setChecked(self._ui_theme == code)
            act.triggered.connect(lambda _=False, c=code: self._set_ui_theme(c))
            appearance_group.addAction(act)
            self._theme_actions[code] = act

        theme_menu = view_menu.addMenu(t("Brettfarbe", "Board color"))
        theme_group = QtGui.QActionGroup(self)
        self._board_actions = {}
        for code, label in [
            ("green", t("Grün", "Green")),
            ("brown", t("Holz", "Wood")),
            ("blue", t("Blau", "Blue")),
            ("grey", t("Grau", "Grey")),
        ]:
            act = theme_menu.addAction(label)
            act.setCheckable(True)
            act.setChecked(self._board_theme == code)
            act.triggered.connect(lambda _=False, c=code: self._set_board_theme(c))
            theme_group.addAction(act)
            self._board_actions[code] = act

        lang_menu = view_menu.addMenu(t("Sprache", "Language"))
        self._lang_actions = {}
        group = QtGui.QActionGroup(self)
        for code, label in [("de", "Deutsch"), ("en", "English")]:
            act = lang_menu.addAction(label)
            act.setCheckable(True)
            act.setChecked(i18n.language() == code)
            act.triggered.connect(lambda _=False, c=code: self._set_language(c))
            group.addAction(act)
            self._lang_actions[code] = act

        help_menu = self.menuBar().addMenu(t("Hilfe", "Help"))
        start_act = help_menu.addAction(t("Erste Schritte", "Getting started"))
        start_act.triggered.connect(self._show_getting_started)
        web_act = help_menu.addAction(t("Projektseite öffnen (GitHub)", "Open project website (GitHub)"))
        web_act.triggered.connect(
            lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(REPO_URL))
        )
        help_menu.addSeparator()
        act = help_menu.addAction(t("Über Opening Trainer", "About Opening Trainer"))
        act.setMenuRole(QtGui.QAction.MenuRole.AboutRole)
        act.triggered.connect(self._show_about)

    def _set_language(self, code: str) -> None:
        if code == i18n.language():
            return
        self._eval_settings.setValue("language", code)
        i18n.set_language(code)
        self._apply_language_live()

    def _apply_language_live(self) -> None:
        """Oberfläche sofort in der neuen Sprache neu aufbauen — ohne Neustart.
        Fenstergröße und aktuelle Seite bleiben erhalten; die Daten (Repertoire,
        Lernplan, Statistik) liegen auf self und überleben den Neuaufbau."""
        geo = self.saveGeometry()
        idx = self.stack.currentIndex() if getattr(self, "stack", None) is not None else 0
        self._nav_history.clear()           # Historie verweist auf alte Oberfläche
        # Hintergrund-Worker stoppen (sie verweisen auf die alten Widgets); sie
        # werden bei Bedarf neu erzeugt.
        self._stop_all_threads()
        self._threads_stopped = False
        # Menü + zentrale Oberfläche in der neuen Sprache neu bauen.
        self.menuBar().clear()
        self._build_menu()
        self._build_ui()
        self.restoreGeometry(geo)
        # Daten-Sichten auffrischen und auf die zuvor gezeigte Seite zurück.
        pass
        self._refresh_library()
        pass
        self.stack.setCurrentIndex(min(idx, self.stack.count() - 1))

    def _set_board_theme(self, code: str) -> None:
        """Brettfarbe live umschalten — alle vorhandenen Bretter neu zeichnen."""
        self._board_theme = code
        self._eval_settings.setValue("board_theme", code)
        set_board_theme(code)
        for name in ("board", "spar_board", "explorer_board", "viewer_board"):
            board = getattr(self, name, None)
            if board is not None:
                board.update()

    @staticmethod
    def _add_board_with_eval(layout, board, eval_bar) -> None:
        """Setzt die Bewertungs-Leiste links und das Brett rechts ins Layout —
        die Leiste exakt auf Höhe des 8×8-Felds (bündig an den Brett-Ecken,
        nicht im Koordinatenrand darüber/darunter). Dafür wird sie um den
        oberen Rand des Bretts nach unten versetzt."""
        col = QtWidgets.QVBoxLayout()
        col.setContentsMargins(0, board.board_offset(), 0, 0)
        col.setSpacing(0)
        col.addWidget(eval_bar)
        col.addStretch(1)
        layout.addLayout(col)
        layout.addWidget(board, 0, QtCore.Qt.AlignTop)

    def _tcolor(self, color) -> str:
        return t("Weiß", "White") if color == chess.WHITE else t("Schwarz", "Black")

    def _tname(self, name: str) -> str:
        """Eröffnungsname für die Anzeige — im Englisch-Modus übersetzt."""
        return to_english(name) if i18n.language() == "en" else name

    def _display_name(self, line) -> str:
        return self._tname(line.name)

    @staticmethod
    def _plain_label(text: str = "") -> QtWidgets.QLabel:
        """QLabel, das seinen Inhalt IMMER wörtlich anzeigt (PlainText). Schützt
        davor, dass Markup aus fremden PGN-Namen/Spielernamen als HTML/Rich-Text
        gerendert wird (Red-Team-Härtung)."""
        lbl = QtWidgets.QLabel(text)
        lbl.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        return lbl

    def _empty_state(self, de: str, en: str) -> QtWidgets.QWidget:
        """Zentrierter, freundlicher Leer-Zustand (statt kahler Fläche oben links)."""
        w = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.addStretch(1)
        row = QtWidgets.QHBoxLayout()
        row.addStretch(1)
        lbl = self._plain_label(t(de, en))
        lbl.setObjectName("empty")
        lbl.setAlignment(QtCore.Qt.AlignCenter)
        lbl.setWordWrap(True)
        # FESTE Breite (statt nur Maximalbreite): sonst rechnet Qt die Wordwrap-Höhe
        # falsch und die Zeilen überlappen/werden abgeschnitten.
        lbl.setFixedWidth(440)
        row.addWidget(lbl)
        row.addStretch(1)
        v.addLayout(row)
        v.addStretch(1)
        return w

    # ---- Repertoire-Editor (Bäume bauen/korrigieren) --------------------
    def _build_editor_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(page)
        layout.setContentsMargins(26, 26, 26, 26)
        layout.setSpacing(24)

        self.editor_board = BoardView(square_size=66)
        self.editor_board.edit_mode = True
        self.editor_board.moveRequested.connect(self._editor_on_move)
        layout.addWidget(self.editor_board, 0, QtCore.Qt.AlignTop)

        side = QtWidgets.QVBoxLayout()
        side.setSpacing(10)

        eyebrow = QtWidgets.QLabel(t("REPERTOIRE-EDITOR", "REPERTOIRE EDITOR"))
        eyebrow.setObjectName("eyebrow")
        side.addWidget(eyebrow)

        row = QtWidgets.QHBoxLayout()
        self.editor_tree_combo = QtWidgets.QComboBox()
        self.editor_tree_combo.currentIndexChanged.connect(self._editor_combo_changed)
        new_btn = QtWidgets.QPushButton(t("＋ Neuer Baum", "＋ New tree"))
        new_btn.setObjectName("more")
        new_btn.clicked.connect(self._editor_new_tree)
        del_tree_btn = QtWidgets.QPushButton(t("🗑 Baum löschen", "🗑 Delete tree"))
        del_tree_btn.setObjectName("more")
        del_tree_btn.clicked.connect(self._editor_delete_tree)
        row.addWidget(self.editor_tree_combo, 1)
        row.addWidget(new_btn, 0)
        row.addWidget(del_tree_btn, 0)
        side.addLayout(row)

        side_row = QtWidgets.QHBoxLayout()
        side_row.addWidget(QtWidgets.QLabel(t("Seite:", "Side:")))
        self.editor_side_combo = QtWidgets.QComboBox()
        for code, label in [("white", t("Weiß", "White")), ("black", t("Schwarz", "Black")), ("none", "—")]:
            self.editor_side_combo.addItem(label, code)
        self.editor_side_combo.currentIndexChanged.connect(self._editor_side_changed)
        side_row.addWidget(self.editor_side_combo, 1)
        side.addLayout(side_row)

        self.editor_train_btn = QtWidgets.QPushButton(t("▶  Diesen Baum üben", "▶  Train this tree"))
        self.editor_train_btn.setObjectName("primary")
        self.editor_train_btn.clicked.connect(lambda: self._start_tree_drill(self.editor_tree))
        side.addWidget(self.editor_train_btn, 0, QtCore.Qt.AlignLeft)

        self.editor_hint = self._plain_label(t(
            "Spiel Züge aufs Brett, um Varianten anzuhängen. Klick einen Zug in der Liste, "
            "um dorthin zu springen. Für eine zweite Gegner-Antwort: zum Elternzug "
            "zurückspringen und einen anderen Zug spielen — er erscheint eingerückt als Nebenvariante.",
            "Play moves on the board to add lines. Click a move in the list to jump there. "
            "For a second opponent reply: jump back to the parent move and play a different "
            "move — it appears indented as a side line.",
        ))
        self.editor_hint.setObjectName("hint")
        self.editor_hint.setWordWrap(True)
        side.addWidget(self.editor_hint)

        self.editor_list = QtWidgets.QListWidget()
        self.editor_list.setObjectName("library")
        self.editor_list.itemClicked.connect(self._editor_list_clicked)
        side.addWidget(self.editor_list, 1)

        actions = QtWidgets.QHBoxLayout()
        for label_de, label_en, slot in [
            ("Zur Hauptlinie", "To main line", self._editor_promote),
            ("Zug löschen", "Delete move", self._editor_delete),
            ("✏ Kommentar", "✏ Comment", self._editor_comment),
        ]:
            b = QtWidgets.QPushButton(t(label_de, label_en))
            b.setObjectName("more")
            b.clicked.connect(lambda _=False, s=slot: s())
            actions.addWidget(b)
        side.addLayout(actions)

        nav = QtWidgets.QHBoxLayout()
        start_btn = QtWidgets.QPushButton(t("⟲ Grundstellung", "⟲ Start position"))
        start_btn.setObjectName("more")
        start_btn.clicked.connect(self._editor_goto_root)
        export_btn = QtWidgets.QPushButton(t("Als PGN exportieren …", "Export as PGN …"))
        export_btn.setObjectName("more")
        export_btn.clicked.connect(self._editor_export)
        nav.addWidget(start_btn)
        nav.addWidget(export_btn)
        side.addLayout(nav)

        back = QtWidgets.QPushButton(t("‹  Zurück", "‹  Back"))
        back.setObjectName("more")
        back.clicked.connect(self._go_back)
        side.addWidget(back, 0, QtCore.Qt.AlignLeft)

        layout.addLayout(side, 1)
        return page

    def _open_editor(self) -> None:
        trees = self.tree_store.all()
        if self.editor_tree is None or self.editor_tree.id not in self.tree_store.trees:
            self.editor_tree = trees[0] if trees else None
        self.stack.setCurrentIndex(9)
        if self.editor_tree is None:
            self._editor_refresh_combo()
            self._editor_new_tree()
            return
        self._editor_refresh_combo()
        self._editor_goto_node(self.editor_tree.root_id)

    def _editor_refresh_combo(self) -> None:
        self.editor_tree_combo.blockSignals(True)
        self.editor_tree_combo.clear()
        for tree in self.tree_store.all():
            self.editor_tree_combo.addItem(self._tname(tree.name) or t("(ohne Namen)", "(unnamed)"), tree.id)
        if self.editor_tree is not None:
            idx = self.editor_tree_combo.findData(self.editor_tree.id)
            if idx >= 0:
                self.editor_tree_combo.setCurrentIndex(idx)
        self.editor_tree_combo.blockSignals(False)

    def _editor_combo_changed(self, _index: int) -> None:
        tid = self.editor_tree_combo.currentData()
        tree = self.tree_store.get(tid) if tid else None
        if tree is not None:
            self.editor_tree = tree
            self._editor_goto_node(tree.root_id)

    def _editor_new_tree(self) -> None:
        from opening_trainer.repertoire_tree import RepertoireTree
        name, ok = QtWidgets.QInputDialog.getText(
            self, t("Neuer Baum", "New tree"), t("Name des Repertoires:", "Repertoire name:"))
        if not ok:
            return
        items = [t("Weiß", "White"), t("Schwarz", "Black")]
        choice, ok2 = QtWidgets.QInputDialog.getItem(
            self, t("Seite", "Side"),
            t("Welche Farbe spielst du in diesem Repertoire?",
              "Which color do you play in this repertoire?"),
            items, 0, False)
        if not ok2:
            return
        side = "white" if choice == items[0] else "black"
        tree = RepertoireTree.new(name=name.strip() or t("Neues Repertoire", "New repertoire"), side=side)
        self.tree_store.add(tree)
        self._editor_save()
        self.editor_tree = tree
        self._editor_refresh_combo()
        self._editor_goto_node(tree.root_id)

    def _editor_delete_tree(self) -> None:
        from opening_trainer.repertoire_tree import RepertoireTree
        if self.editor_tree is None:
            return
        name = self._tname(self.editor_tree.name) or t("(ohne Namen)", "(unnamed)")
        if QtWidgets.QMessageBox.warning(
            self, t("Baum löschen?", "Delete tree?"),
            t(f"Den ganzen Baum »{name}« löschen?\n\nDas entfernt alle seine Varianten "
              "und kann nicht rückgängig gemacht werden.",
              f"Delete the whole tree »{name}«?\n\nThis removes all its lines and "
              "cannot be undone."),
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.Cancel,
            QtWidgets.QMessageBox.StandardButton.Cancel,
        ) != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        self.tree_store.remove(self.editor_tree.id)
        self._editor_save()
        trees = self.tree_store.all()
        if trees:
            self.editor_tree = trees[0]
        else:                                   # letzter Baum -> leeren Baum anlegen
            self.editor_tree = RepertoireTree.new(t("Neues Repertoire", "New repertoire"), side="white")
            self.tree_store.add(self.editor_tree)
            self._editor_save()
        self._editor_refresh_combo()
        self._editor_goto_node(self.editor_tree.root_id)

    def _editor_side_changed(self, _index: int) -> None:
        if self.editor_tree is None:
            return
        code = self.editor_side_combo.currentData()
        if code and code != self.editor_tree.side:
            self._editor_make_permanent()
            self.editor_tree.set_side(code)
            self._editor_save()
            self.editor_board.set_flipped(self.editor_tree.side == "black")
            self.editor_board.set_board(self._editor_pos)

    def _editor_pos_for_node(self, node_id: str) -> chess.Board:
        board = chess.Board(self.editor_tree.start_fen) if self.editor_tree.start_fen else chess.Board()
        for uci in self.editor_tree.path_to(node_id):
            move = chess.Move.from_uci(uci)
            if move not in board.legal_moves:
                break
            board.push(move)
        return board

    def _editor_goto_root(self) -> None:
        if self.editor_tree is not None:
            self._editor_goto_node(self.editor_tree.root_id)

    def _editor_goto_node(self, node_id: str) -> None:
        if self.editor_tree is None or node_id not in self.editor_tree.nodes:
            return
        self.editor_node = node_id
        self._editor_pos = self._editor_pos_for_node(node_id)
        node = self.editor_tree.nodes[node_id]
        last = None
        if node.parent_id is not None and node.move_uci:
            m = chess.Move.from_uci(node.move_uci)
            last = (m.from_square, m.to_square)
        self.editor_board.set_flipped(self.editor_tree.side == "black")
        self.editor_board.set_board(self._editor_pos, last_move=last)
        self.editor_side_combo.blockSignals(True)
        si = self.editor_side_combo.findData(self.editor_tree.side)
        if si >= 0:
            self.editor_side_combo.setCurrentIndex(si)
        self.editor_side_combo.blockSignals(False)
        # Üben braucht eine Seite — sonst Knopf deaktivieren statt erst auf der
        # Drill-Seite zu scheitern.
        playable = self.editor_tree.side in ("white", "black")
        self.editor_train_btn.setEnabled(playable)
        self.editor_train_btn.setToolTip("" if playable else t(
            "Setz oben die Seite (Weiß/Schwarz), um diesen Baum zu üben.",
            "Set the side (White/Black) above to train this tree."))
        self._editor_render_list()

    def _editor_make_permanent(self) -> None:
        """Bearbeiten eines Auto-Baums macht ihn zu einem dauerhaften Editor-Baum
        (Marke entfernen) — sonst überschriebe ihn der nächste Auto-Sync."""
        tr = self.editor_tree
        if tr is not None and tr.headers.pop("_auto", None) is not None:
            tr.headers.pop("_source", None)

    def _editor_on_move(self, from_square: int, to_square: int) -> None:
        if self.editor_tree is None or self.editor_node is None:
            return
        try:
            move = self._editor_pos.find_move(from_square, to_square)
        except ValueError:
            return
        self._editor_make_permanent()
        child = self.editor_tree.add_child(self.editor_node, move.uci())
        self._editor_save()
        self._editor_goto_node(child.id)

    def _editor_list_clicked(self, item) -> None:
        nid = item.data(QtCore.Qt.UserRole)
        if nid:
            self._editor_goto_node(nid)

    def _editor_promote(self) -> None:
        if self.editor_tree and self.editor_node and self.editor_node != self.editor_tree.root_id:
            self._editor_make_permanent()
            self.editor_tree.promote(self.editor_node)
            self._editor_save()
            self._editor_render_list()

    def _editor_delete(self) -> None:
        if not self.editor_tree or not self.editor_node or self.editor_node == self.editor_tree.root_id:
            return
        parent = self.editor_tree.nodes[self.editor_node].parent_id
        self._editor_make_permanent()
        self.editor_tree.delete_subtree(self.editor_node)
        self._editor_save()
        self._editor_goto_node(parent or self.editor_tree.root_id)

    def _editor_comment(self) -> None:
        if not self.editor_tree or not self.editor_node or self.editor_node == self.editor_tree.root_id:
            return
        node = self.editor_tree.nodes[self.editor_node]
        text, ok = QtWidgets.QInputDialog.getMultiLineText(
            self, t("Kommentar", "Comment"), t("Kommentar zu diesem Zug:", "Comment on this move:"), node.comment)
        if ok:
            self._editor_make_permanent()
            node.comment = text.strip()
            self._editor_save()
            self._editor_render_list()

    def _editor_export(self) -> None:
        if self.editor_tree is None:
            return
        from opening_trainer.pgn_tree_export import export_trees
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, t("Als PGN exportieren", "Export as PGN"), "repertoire.pgn",
            t("PGN-Dateien (*.pgn)", "PGN files (*.pgn)"))
        if not path:
            return
        try:
            Path(path).write_text(export_trees([self.editor_tree]), encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.warning(self, t("Export fehlgeschlagen", "Export failed"), str(exc))
            return
        QtWidgets.QMessageBox.information(
            self, t("Exportiert", "Exported"),
            t(f"Repertoire (mit allen Varianten) gespeichert:\n{path}",
              f"Repertoire (with all variations) saved:\n{path}"))

    def _editor_save(self) -> None:
        self.tree_store.save(self.trees_path)

    def _editor_render_list(self) -> None:
        self.editor_list.clear()
        tree = self.editor_tree
        if tree is None:
            return
        board = chess.Board(tree.start_fen) if tree.start_fen else chess.Board()
        selected_item = None

        def walk(node, depth):
            nonlocal selected_item
            for i, cid in enumerate(node.children_ids):
                child = tree.nodes[cid]
                try:
                    move = chess.Move.from_uci(child.move_uci)
                    san = board.san(move)
                except Exception:  # noqa: BLE001
                    continue
                num = board.fullmove_number
                dots = "." if board.turn == chess.WHITE else "…"
                indent = "    " * depth + ("" if i == 0 else "└ ")
                text = f"{indent}{num}{dots} {san}" + ("  💬" if child.comment else "")
                item = QtWidgets.QListWidgetItem(text)
                item.setData(QtCore.Qt.UserRole, cid)
                if cid == self.editor_node:
                    item.setBackground(QtGui.QColor("#dbe7c8"))
                    selected_item = item
                self.editor_list.addItem(item)
                board.push(move)
                walk(child, depth + (0 if i == 0 else 1))
                board.pop()

        walk(tree.root, 0)
        # Nach dem Neuaufbau den gewählten Zug sichtbar halten — sonst springt die
        # Liste auf den Anfang zurück (Klick auf Züge weit unten »verschwand«).
        if selected_item is not None:
            self.editor_list.setCurrentItem(selected_item)
            self.editor_list.scrollToItem(
                selected_item, QtWidgets.QAbstractItemView.ScrollHint.PositionAtCenter
            )

    # ---- Baum üben (positions-basiert, additiv neben dem normalen Training) ----
    def _build_tree_drill_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(page)
        layout.setContentsMargins(26, 26, 26, 26)
        layout.setSpacing(24)

        self.tree_drill_board = BoardView(square_size=70)
        self.tree_drill_board.moveRequested.connect(self._tree_drill_on_move)
        layout.addWidget(self.tree_drill_board, 0, QtCore.Qt.AlignTop)

        side = QtWidgets.QVBoxLayout()
        side.setSpacing(12)
        self.drill_eyebrow = QtWidgets.QLabel(t("BAUM ÜBEN", "TRAIN TREE"))
        self.drill_eyebrow.setObjectName("eyebrow")
        side.addWidget(self.drill_eyebrow)
        # Blitz-Anzeige: Uhr + Punktestand (nur im Blitz-Modus sichtbar).
        self.blitz_bar = QtWidgets.QWidget()
        bb = QtWidgets.QHBoxLayout(self.blitz_bar)
        bb.setContentsMargins(0, 0, 0, 0)
        bb.setSpacing(16)
        self.blitz_clock = QtWidgets.QLabel("⏱ 60")
        self.blitz_clock.setObjectName("heroT")
        self.blitz_score_label = QtWidgets.QLabel(t("Punkte: 0", "Score: 0"))
        self.blitz_score_label.setObjectName("heroT")
        bb.addWidget(self.blitz_clock)
        bb.addWidget(self.blitz_score_label)
        bb.addStretch(1)
        self.blitz_bar.setVisible(False)
        side.addWidget(self.blitz_bar)
        self.tree_drill_combo = QtWidgets.QComboBox()
        self.tree_drill_combo.currentIndexChanged.connect(self._drill_combo_changed)
        side.addWidget(self.tree_drill_combo)
        self.drill_manual_check = QtWidgets.QCheckBox(
            t("Gegnerzüge selbst spielen", "Play the opponent's moves myself"))
        self.drill_manual_check.toggled.connect(self._drill_toggle_manual)
        side.addWidget(self.drill_manual_check)
        # Learn-Modus: neue Stellungen erst MIT Lösung zeigen, dann abfragen.
        self.drill_learn_check = QtWidgets.QCheckBox(
            t("Neue Stellungen erst zeigen (lernen)", "Show new positions first (learn)"))
        self.drill_learn_check.setChecked(True)
        self.drill_learn_check.toggled.connect(self._drill_toggle_learn)
        side.addWidget(self.drill_learn_check)
        self.tree_drill_name = self._plain_label("—")
        self.tree_drill_name.setObjectName("name")
        self.tree_drill_name.setWordWrap(True)
        side.addWidget(self.tree_drill_name)
        # Linien-Kontext: die Züge bis zur aktuellen Stellung (»wo bin ich?«).
        self.tree_drill_line = self._plain_label("")
        self.tree_drill_line.setObjectName("hint")
        self.tree_drill_line.setWordWrap(True)
        side.addWidget(self.tree_drill_line)
        # »Idee zu dieser Stellung«: Kommentar des vorgesehenen Zuges (falls vorhanden).
        self.tree_drill_note = self._plain_label("")
        self.tree_drill_note.setObjectName("note")
        self.tree_drill_note.setWordWrap(True)
        self.tree_drill_note.setVisible(False)
        side.addWidget(self.tree_drill_note)
        self.tree_drill_status = self._plain_label("")
        self.tree_drill_status.setObjectName("status")
        self.tree_drill_status.setWordWrap(True)
        self.tree_drill_status.setMinimumHeight(48)
        side.addWidget(self.tree_drill_status)
        # Bleibende Feedback-Zeile (überdauert den Wechsel zur nächsten Stellung):
        # zeigt nach jeder Antwort, wann die Stellung wieder fällig wird.
        self.tree_drill_feedback = self._plain_label("")
        self.tree_drill_feedback.setObjectName("hint")
        self.tree_drill_feedback.setWordWrap(True)
        side.addWidget(self.tree_drill_feedback)

        # Learn-Modus: »Verstanden, weiter« (nur sichtbar, wenn eine neue Stellung gezeigt wird).
        self.drill_learned_btn = QtWidgets.QPushButton(t("✓  Verstanden, weiter", "✓  Got it, next"))
        self.drill_learned_btn.setObjectName("primary")
        self.drill_learned_btn.clicked.connect(self._drill_mark_learned)
        self.drill_learned_btn.setVisible(False)
        side.addWidget(self.drill_learned_btn, 0, QtCore.Qt.AlignLeft)

        btns = QtWidgets.QHBoxLayout()
        sol = QtWidgets.QPushButton(t("Lösung zeigen", "Show solution"))
        sol.clicked.connect(self._tree_drill_solution)
        again = QtWidgets.QPushButton(t("Neu", "Restart"))
        again.clicked.connect(self._tree_drill_restart)
        btns.addWidget(sol)
        btns.addWidget(again)
        side.addLayout(btns)
        side.addStretch(1)

        self.drill_back_btn = QtWidgets.QPushButton(t("‹  Zurück", "‹  Back"))
        self.drill_back_btn.setObjectName("more")
        self.drill_back_btn.clicked.connect(self._go_back)   # zur vorigen Seite
        side.addWidget(self.drill_back_btn, 0, QtCore.Qt.AlignLeft)

        layout.addLayout(side, 1)
        return page

    def _open_tree_drill(self) -> None:
        """Menü-Einstieg „Bäume üben": einen Baum wählen und drillen."""
        tree = self._drill_tree or self.editor_tree
        if tree is None or tree.id not in self.tree_store.trees:
            trees = self.tree_store.all()
            tree = trees[0] if trees else None
        if tree is None:
            QtWidgets.QMessageBox.information(
                self, t("Keine Bäume", "No trees"),
                t("Lege zuerst im Repertoire-Editor (⌘E) einen Baum an.",
                  "Create a tree in the repertoire editor (⌘E) first."))
            return
        self._start_tree_drill(tree)

    def _start_tree_drill(self, tree=None) -> None:
        tree = tree if tree is not None else (self._drill_tree or self.editor_tree)
        if tree is None:
            return
        self._blitz_stop()                         # falls vorher ein Blitz lief
        self._due_session = False
        self.tree_drill_feedback.setText("")
        self.drill_eyebrow.setText(t("BAUM ÜBEN", "TRAIN TREE"))
        self.tree_drill_combo.setVisible(True)
        self.drill_manual_check.setVisible(True)
        self.drill_learn_check.setVisible(False)   # Learn-Modus nur in der Tagessitzung
        self.drill_learned_btn.setVisible(False)
        self._drill_tree = tree
        self._drill_refresh_combo()
        self.tree_drill_name.setText(self._tname(tree.name))
        self.stack.setCurrentIndex(10)
        if tree.side not in ("white", "black"):
            self._tree_trainer = None
            self.tree_drill_board.set_board(chess.Board())
            self.tree_drill_status.setText(t(
                "Diesem Baum fehlt die Seite. Setz sie im Editor auf Weiß oder Schwarz.",
                "This tree has no side yet. Set it to White or Black in the editor."))
            return
        from opening_trainer.position_training import PositionTrainer
        side = chess.WHITE if tree.side == "white" else chess.BLACK
        # Gegner wählt an Verzweigungen zufällig -> über mehrere Durchläufe werden
        # ALLE vorbereiteten Äste geübt. Im manuellen Modus spielt der Nutzer Weiß selbst.
        self._tree_trainer = PositionTrainer(
            tree, side, opponent_pick=random.choice, auto_opponent=not self._drill_manual)
        self._tree_drill_wrong = False
        self.tree_drill_board.train_color = side
        self.tree_drill_board.edit_mode = self._drill_manual   # manuell: beide Farben ziehbar
        self._tree_drill_present()

    def _drill_toggle_manual(self, checked: bool) -> None:
        self._drill_manual = checked
        if self._drill_tree is not None:
            self._start_tree_drill(self._drill_tree)

    def _drill_refresh_combo(self) -> None:
        self.tree_drill_combo.blockSignals(True)
        self.tree_drill_combo.clear()
        for tr in self.tree_store.all():
            self.tree_drill_combo.addItem(self._tname(tr.name) or t("(ohne Namen)", "(unnamed)"), tr.id)
        if self._drill_tree is not None:
            idx = self.tree_drill_combo.findData(self._drill_tree.id)
            if idx >= 0:
                self.tree_drill_combo.setCurrentIndex(idx)
        self.tree_drill_combo.blockSignals(False)

    def _drill_combo_changed(self, _index: int) -> None:
        tid = self.tree_drill_combo.currentData()
        tree = self.tree_store.get(tid) if tid else None
        if tree is not None and (self._drill_tree is None or tree.id != self._drill_tree.id):
            self._start_tree_drill(tree)

    # ---- „Heute fällig": Übersicht + stellungs-basierte Tagessitzung ----
    def _build_due_overview_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        outer = QtWidgets.QVBoxLayout(page)
        outer.setContentsMargins(26, 22, 26, 22)
        outer.setSpacing(12)

        # Kopf wie die anderen Listen-Seiten: Zurück oben-links + Titel.
        header = QtWidgets.QHBoxLayout()
        back = QtWidgets.QPushButton(t("‹  Zurück", "‹  Back"))
        back.setObjectName("more")
        back.clicked.connect(self._go_back)
        header.addWidget(back, 0, QtCore.Qt.AlignLeft)
        header.addStretch(1)
        outer.addLayout(header)
        title = QtWidgets.QLabel(t("Heute fällig", "Due today"))
        title.setObjectName("name")
        outer.addWidget(title)

        self.due_overview_forecast = self._plain_label("")
        self.due_overview_forecast.setObjectName("hint")
        self.due_overview_forecast.setWordWrap(True)
        outer.addWidget(self.due_overview_forecast)

        self.due_overview_all_btn = QtWidgets.QPushButton(t("▶  Alles üben", "▶  Train all"))
        self.due_overview_all_btn.setObjectName("primary")
        self.due_overview_all_btn.clicked.connect(lambda: self._start_due_session())
        outer.addWidget(self.due_overview_all_btn, 0, QtCore.Qt.AlignLeft)

        self.due_overview_list = QtWidgets.QListWidget()
        self.due_overview_list.setObjectName("library")
        self.due_overview_list.setSpacing(2)
        # Zeilen passen in die Breite -> kein horizontaler Scrollbalken nötig.
        self.due_overview_list.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        outer.addWidget(self.due_overview_list, 1)
        return page

    def _due_overview_row(self, r: dict) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        lay = QtWidgets.QHBoxLayout(w)
        lay.setContentsMargins(10, 5, 10, 5)
        name = self._plain_label(self._tname(r["name"]) or t("(ohne Namen)", "(unnamed)"))
        name.setObjectName("duename")
        counts = QtWidgets.QLabel(t(f"{r['due']} fällig · {r['new']} neu",
                                    f"{r['due']} due · {r['new']} new"))
        counts.setObjectName("rowsub")
        btn = QtWidgets.QPushButton(t("▶ üben", "▶ train"))
        btn.setEnabled((r["due"] + r["new"]) > 0)
        btn.clicked.connect(lambda _=False, tr=r["tree"]: self._start_due_session(only_tree=tr))
        lay.addWidget(name, 0)
        lay.addStretch(1)
        lay.addWidget(counts, 0)
        lay.addWidget(btn, 0)
        return w

    def _open_due_overview(self) -> None:
        self._refresh_due_overview()
        self.stack.setCurrentIndex(11)

    def _refresh_due_overview(self) -> None:
        """Übersicht vor dem Üben: Vorschau + Aufschlüsselung pro Eröffnung."""
        from opening_trainer.tree_session import due_breakdown, due_forecast
        today = date.today()
        rows: list = []
        fc = {"today": 0, "tomorrow": 0, "week": 0, "new": 0}
        for side_name, color in (("white", chess.WHITE), ("black", chess.BLACK)):
            trees = self.tree_store.by_side(side_name)
            rows += due_breakdown(trees, color, self.position_schedule, today)
            f = due_forecast(trees, color, self.position_schedule, today)
            for k in fc:
                fc[k] += f[k]
        rows.sort(key=lambda r: (-r["due"], -r["new"], r["name"]))

        self.due_overview_forecast.setText(t(
            f"Heute: {fc['today']}   ·   Morgen: {fc['tomorrow']}   ·   "
            f"Diese Woche: {fc['week']}   ·   Neu: {fc['new']}",
            f"Today: {fc['today']}   ·   Tomorrow: {fc['tomorrow']}   ·   "
            f"This week: {fc['week']}   ·   New: {fc['new']}"))
        total = len(self._due_items())          # echte (deduplizierte) Sitzungsgröße
        self.due_overview_all_btn.setText(t(f"▶  Alles üben  ({total})", f"▶  Train all  ({total})"))
        self.due_overview_all_btn.setEnabled(total > 0)

        self.due_overview_list.clear()
        if not rows:
            item = QtWidgets.QListWidgetItem(t("Nichts fällig — schau morgen wieder vorbei. 🎉",
                                               "Nothing due — come back tomorrow. 🎉"))
            item.setFlags(QtCore.Qt.NoItemFlags)
            self.due_overview_list.addItem(item)
        else:
            # Platz für den vertikalen Scrollbalken lassen -> kein horizontaler Überlauf.
            width = max(self.due_overview_list.viewport().width() - 18, 600)
            for r in rows:
                row = self._due_overview_row(r)
                item = QtWidgets.QListWidgetItem()
                # Mindesthöhe, damit der „üben"-Knopf nicht gestaucht wird und sein
                # Text verschwindet (row.sizeHint() ist beim Befüllen noch zu klein).
                item.setSizeHint(QtCore.QSize(width, max(row.sizeHint().height(), 50)))
                self.due_overview_list.addItem(item)
                self.due_overview_list.setItemWidget(item, row)

    def _due_items(self, only_tree=None, only_side=None) -> list:
        """Heute fällige/neue eigene Stellungen — über das ganze Repertoire (beide
        Seiten), oder nur für eine Eröffnung (``only_tree``) bzw. eine Seite
        (``only_side`` = "white"/"black")."""
        from opening_trainer.tree_session import due_drill_items, due_items_for_tree
        today = date.today()
        items: list = []
        if only_tree is not None:
            side = chess.WHITE if only_tree.side == "white" else chess.BLACK
            for tree, node_id in due_items_for_tree(only_tree, side, self.position_schedule, today):
                items.append((tree, node_id, side))
            return items
        sides = (("white", chess.WHITE), ("black", chess.BLACK))
        if only_side in ("white", "black"):
            sides = ((only_side, chess.WHITE if only_side == "white" else chess.BLACK),)
        for side_name, color in sides:
            trees = self.tree_store.by_side(side_name)
            for tree, node_id in due_drill_items(trees, color, self.position_schedule, today):
                items.append((tree, node_id, color))
        return items

    # ---- Repertoire-Baum: alle Linien einer Seite als EIN verzweigter Baum ----
    def _build_repertoire_tree_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(page)
        layout.setContentsMargins(26, 26, 26, 26)
        layout.setSpacing(24)

        self.reptree_board = BoardView(square_size=58)
        layout.addWidget(self.reptree_board, 0, QtCore.Qt.AlignTop)

        col = QtWidgets.QVBoxLayout()
        col.setSpacing(10)
        back = QtWidgets.QPushButton(t("‹  Zurück", "‹  Back"))
        back.setObjectName("more")
        back.clicked.connect(self._go_back)
        col.addWidget(back, 0, QtCore.Qt.AlignLeft)
        eyebrow = QtWidgets.QLabel(t("REPERTOIRE-BAUM", "REPERTOIRE TREE"))
        eyebrow.setObjectName("eyebrow")
        col.addWidget(eyebrow)
        side_row = QtWidgets.QHBoxLayout()
        self.reptree_side_combo = QtWidgets.QComboBox()
        self.reptree_side_combo.addItem(t("Weiß", "White"), "white")
        self.reptree_side_combo.addItem(t("Schwarz", "Black"), "black")
        self.reptree_side_combo.currentIndexChanged.connect(self._reptree_side_changed)
        # Zweite Auswahl: konkretes Repertoire (»Alles« oder eine Eröffnung).
        self.reptree_family_combo = QtWidgets.QComboBox()
        self.reptree_family_combo.currentIndexChanged.connect(lambda _i: self._refresh_repertoire_tree())
        side_row.addWidget(self.reptree_side_combo, 0)
        side_row.addWidget(self.reptree_family_combo, 1)
        col.addLayout(side_row)
        self.reptree_hint = QtWidgets.QLabel("")
        self.reptree_hint.setObjectName("hint")
        self.reptree_hint.setWordWrap(True)
        col.addWidget(self.reptree_hint)
        self.reptree_list = QtWidgets.QListWidget()
        self.reptree_list.setObjectName("library")
        self.reptree_list.itemClicked.connect(self._reptree_clicked)
        col.addWidget(self.reptree_list, 1)
        btn_row = QtWidgets.QHBoxLayout()
        self.reptree_train_btn = QtWidgets.QPushButton(t("▶  Dieses Repertoire üben", "▶  Train this repertoire"))
        self.reptree_train_btn.setObjectName("primary")
        self.reptree_train_btn.clicked.connect(self._reptree_train)
        self.reptree_drill_btn = QtWidgets.QPushButton(t("Diese Stellung üben", "Drill this position"))
        self.reptree_drill_btn.setObjectName("more")
        self.reptree_drill_btn.setEnabled(False)
        self.reptree_drill_btn.clicked.connect(self._reptree_drill)
        self.reptree_gap_btn = QtWidgets.QPushButton(t("⚠  Im Editor ergänzen", "⚠  Add in editor"))
        self.reptree_gap_btn.setObjectName("more")
        self.reptree_gap_btn.setEnabled(False)
        self.reptree_gap_btn.clicked.connect(self._reptree_fill_gap)
        btn_row.addWidget(self.reptree_train_btn)
        btn_row.addWidget(self.reptree_drill_btn)
        btn_row.addWidget(self.reptree_gap_btn)
        btn_row.addStretch(1)
        col.addLayout(btn_row)

        holder = QtWidgets.QWidget()
        holder.setLayout(col)
        layout.addWidget(holder, 1)
        return page

    @staticmethod
    def _family_of_name(name: str) -> str:
        """Eröffnungs-Familie aus dem Linien-Namen: »B18 · Caro-Kann: Klassisch«
        → »Caro-Kann«. So lassen sich die Bäume zu benannten Repertoires
        gruppieren (= die Auswahl, die der Nutzer erwartet)."""
        f = name or ""
        if "·" in f:
            f = f.split("·", 1)[1]
        if ":" in f:
            f = f.split(":", 1)[0]
        return f.strip() or t("Sonstige", "Other")

    def _tree_family(self, tree) -> str:
        """Repertoire-Familie eines Baums — ZUERST aus den ZÜGEN erkannt
        (kanonisch, reload-stabil, fasst »Sizilianisch Najdorf/Alapin/…« zu
        einem »Sizilianisch« zusammen und behebt Schreibweisen-Dubletten wie
        »Französisch«/»Franzoesisch«). Nur wenn die Züge unbekannt sind, dient
        der (normalisierte) PGN-Name als Rückfall."""
        from opening_trainer.opening_id import identify_opening
        from opening_trainer.tree_session import tree_mainline_uci
        detected = identify_opening(tree_mainline_uci(tree))
        if detected:
            return detected
        raw = (tree.name or "").strip()
        return self._family_of_name(raw) if raw else t("Sonstige", "Other")

    def _reptree_families(self, side_name: str) -> list:
        """Sortierte, eindeutige Repertoire-Familien der Seite (für die Auswahl)."""
        fams = {self._tree_family(tr) for tr in self.tree_store.by_side(side_name)}
        return sorted(fams, key=str.casefold)

    def _open_repertoire_tree(self) -> None:
        # Voreinstellung: die Seite zeigen, für die ein Repertoire existiert.
        if self.tree_store.by_side("black") and not self.tree_store.by_side("white"):
            self.reptree_side_combo.setCurrentIndex(1)
        elif self.tree_store.by_side("white"):
            self.reptree_side_combo.setCurrentIndex(0)
        self._reptree_refresh_families()
        self._refresh_repertoire_tree()
        self.stack.setCurrentIndex(13)

    def _reptree_side_changed(self, _i: int) -> None:
        self._reptree_refresh_families()
        self._refresh_repertoire_tree()

    # Schwarz-Verteidigungen: als Weiß spielt man GEGEN sie (Label »gegen X«).
    _DEFENSES = frozenset({
        "Sizilianisch", "Französisch", "Caro-Kann", "Skandinavisch",
        "Aljechin-Verteidigung", "Pirc-Verteidigung", "Moderne Verteidigung",
        "Russische Verteidigung (Petrow)", "Philidor-Verteidigung", "Nimzo-Indisch",
        "Königsindisch", "Damenindisch", "Grünfeld-Verteidigung", "Slawische Verteidigung",
        "Semi-Slawisch", "Holländisch", "Benoni", "Benko-Gambit", "Indische Verteidigung",
    })

    def _reptree_family_label(self, fam: str, side_name: str) -> str:
        """Anzeigetext einer Familie: im WEISS-Repertoire bekommt eine Schwarz-
        Verteidigung ein »gegen« vorangestellt (du spielst dagegen)."""
        if side_name == "white" and fam in self._DEFENSES:
            return t(f"gegen {fam}", f"vs {fam}")
        return fam

    def _reptree_refresh_families(self) -> None:
        """Füllt die Repertoire-Auswahl passend zur gewählten Seite: »Alles«
        plus jede benannte Familie (Verteidigungen als »gegen …« bei Weiß)."""
        self.reptree_family_combo.blockSignals(True)
        self.reptree_family_combo.clear()
        side_name = self.reptree_side_combo.currentData()
        self.reptree_family_combo.addItem(t("Alles", "All"), None)
        for fam in self._reptree_families(side_name):
            self.reptree_family_combo.addItem(self._reptree_family_label(fam, side_name), fam)
        self.reptree_family_combo.blockSignals(False)

    def _reptree_selected_trees(self):
        """(Bäume, Farbe) für die aktuelle Seiten-/Repertoire-Auswahl."""
        side_name = self.reptree_side_combo.currentData()
        color = chess.WHITE if side_name == "white" else chess.BLACK
        trees = self.tree_store.by_side(side_name)
        fam = self.reptree_family_combo.currentData()
        if fam is not None:
            trees = [tr for tr in trees if self._tree_family(tr) == fam]
        return trees, color

    def _refresh_repertoire_tree(self) -> None:
        from opening_trainer.tree_session import merge_side_trees, overview_rows, repertoire_gaps
        self.reptree_list.clear()
        self.reptree_drill_btn.setEnabled(False)
        self.reptree_gap_btn.setEnabled(False)
        self._reptree_fen = None
        self._reptree_gap = None
        trees, color = self._reptree_selected_trees()
        self._reptree_gap_map = {g["epd"]: g for g in repertoire_gaps(trees, color)}
        rows = overview_rows(merge_side_trees(trees, color), color)
        self.reptree_board.set_flipped(color == chess.BLACK)
        self.reptree_board.set_board(chess.Board())
        self.reptree_train_btn.setEnabled(bool(rows))
        if not rows:
            self.reptree_hint.setText(t(
                "Für diese Auswahl ist kein Repertoire geladen.",
                "No repertoire loaded for this selection."))
            return
        branches = sum(1 for r in rows if r["children"] > 1)
        variations = sum(1 for r in rows if r["children"] == 0)   # vollständige Linien = Blätter
        fam = self.reptree_family_combo.currentData()
        scope = (self._reptree_family_label(fam, self.reptree_side_combo.currentData())
                 if fam is not None else t("ganzes Repertoire", "whole repertoire"))
        var_de = "Variante" if variations == 1 else "Varianten"
        var_en = "variation" if variations == 1 else "variations"
        br_de = "Verzweigung" if branches == 1 else "Verzweigungen"
        br_en = "branch" if branches == 1 else "branches"
        gaps_n = len(self._reptree_gap_map)
        luecke = "Lücke" if gaps_n == 1 else "Lücken"
        gap_en = "gap" if gaps_n == 1 else "gaps"
        gaps_de = f" · ⚠ {gaps_n} {luecke} (ohne deine Antwort)" if gaps_n else ""
        gaps_en = f" · ⚠ {gaps_n} {gap_en} (no reply yet)" if gaps_n else ""
        self.reptree_hint.setText(t(
            f"{scope}: {variations} {var_de} · {branches} {br_de} (⎇){gaps_de}. "
            "Klick eine Zeile für die Stellung — ⚠ = Lücke, »Im Editor ergänzen«.",
            f"{scope}: {variations} {var_en} · {branches} {br_en} (⎇){gaps_en}. "
            "Click a row for the position — ⚠ = gap, »Add in editor«."))
        de = (i18n.language() == "de")
        for r in rows:
            label = r["label"]
            if de:
                label = label.translate(str.maketrans({"N": "S", "B": "L", "R": "T", "Q": "D"}))
            prefix = "    " * r["depth"] + ("" if r["depth"] == 0 else "└ ")
            mark = "  ⎇" if r["children"] > 1 else ""
            # Lücke? = Blatt, dessen Folgestellung in der Lücken-Liste steht.
            r["_gap"] = None
            if r["children"] == 0:
                try:
                    b = chess.Board(r["fen_before"])
                    b.push(chess.Move.from_uci(r["move_uci"]))
                    r["_gap"] = self._reptree_gap_map.get(b.epd())
                except (ValueError, KeyError):
                    pass
            warn = "  ⚠" if r["_gap"] else ""
            # Am Ende einer Linie (Blatt) den Eröffnungsnamen anzeigen.
            name = f"   · {r['comment']}" if (r["comment"] and r["children"] == 0) else ""
            item = QtWidgets.QListWidgetItem(prefix + label + mark + warn + name)
            item.setData(QtCore.Qt.UserRole, r)
            self.reptree_list.addItem(item)

    def _reptree_clicked(self, item: QtWidgets.QListWidgetItem) -> None:
        r = item.data(QtCore.Qt.UserRole)
        if not r:
            return
        try:
            board = chess.Board(r["fen_before"])
            move = chess.Move.from_uci(r["move_uci"])
        except (ValueError, KeyError):
            return
        last = (move.from_square, move.to_square)
        board.push(move)                       # Brett zeigt den Zug gespielt …
        self.reptree_board.set_board(board, last_move=last)
        # … geübt wird die Entscheidung davor (nur bei eigenen Zügen).
        self._reptree_fen = r["fen_before"] if r["is_user_move"] else None
        self.reptree_drill_btn.setEnabled(bool(self._reptree_fen))
        # Lücke? -> »Im Editor ergänzen« freischalten.
        self._reptree_gap = r.get("_gap")
        self.reptree_gap_btn.setEnabled(self._reptree_gap is not None)

    def _reptree_drill(self) -> None:
        if self._reptree_fen:
            self._drill_positions_for_fens([self._reptree_fen], t("STELLUNG ÜBEN", "DRILL POSITION"))

    def _reptree_fill_gap(self) -> None:
        """Springt zur Lücke im Editor, damit man die fehlende Antwort eintragen kann."""
        g = self._reptree_gap
        if g:
            self._editor_open_at(g["tree"], g["node_id"])

    def _editor_open_at(self, tree, node_id) -> None:
        if tree is None or tree.id not in self.tree_store.trees:
            return
        self.editor_tree = tree
        self.stack.setCurrentIndex(9)
        self._editor_refresh_combo()
        self._editor_goto_node(node_id if node_id in tree.nodes else tree.root_id)

    def _reptree_train(self) -> None:
        """Übt genau das oben gewählte Repertoire: heute fällige/neue Stellungen
        zuerst; ist nichts fällig, alle Stellungen dieses Repertoires."""
        from opening_trainer.tree_session import due_drill_items, build_user_position_index
        trees, color = self._reptree_selected_trees()
        if not trees:
            return
        items = [(tr, nid, color) for tr, nid in
                 due_drill_items(trees, color, self.position_schedule, date.today())]
        if not items:                                   # nichts fällig -> ganzes Repertoire
            items = [(tr, nid, color) for (tr, nid) in
                     build_user_position_index(trees, color).values()]
        if items:
            self._run_position_session(items, t("REPERTOIRE ÜBEN", "TRAIN REPERTOIRE"))

    # ---- Start-Hub: Dashboard (Navigation macht die Seitenleiste) ----
    def _build_home_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        outer = QtWidgets.QVBoxLayout(page)
        outer.setContentsMargins(36, 30, 36, 30)
        outer.setSpacing(18)

        title = QtWidgets.QLabel(t("Start", "Home"))
        title.setObjectName("name")
        outer.addWidget(title)
        subtitle = QtWidgets.QLabel(t("Willkommen zurück — hier ist dein Überblick.",
                                      "Welcome back — here's your overview."))
        subtitle.setObjectName("hint")
        outer.addWidget(subtitle)

        # --- Hero-Karte: heutige Übung (sichtbar, sobald ein Repertoire da ist) ---
        self.home_hero = QtWidgets.QFrame()
        self.home_hero.setObjectName("hero")
        hero = QtWidgets.QHBoxLayout(self.home_hero)
        hero.setContentsMargins(26, 22, 26, 22)
        hero.setSpacing(16)
        col = QtWidgets.QVBoxLayout()
        col.setSpacing(4)
        hero_title = QtWidgets.QLabel(t("Heute fällig", "Due today"))
        hero_title.setObjectName("heroT")
        col.addWidget(hero_title)
        self.home_forecast = self._plain_label("")
        self.home_forecast.setObjectName("cardL")
        self.home_forecast.setWordWrap(True)
        col.addWidget(self.home_forecast)
        hero.addLayout(col, 1)
        self.home_due_btn = QtWidgets.QPushButton(t("▶  Jetzt üben", "▶  Train now"))
        self.home_due_btn.setObjectName("primary")
        self.home_due_btn.clicked.connect(self._open_due_overview)
        hero.addWidget(self.home_due_btn, 0, QtCore.Qt.AlignVCenter)
        outer.addWidget(self.home_hero)

        # --- Kennzahl-Karten ---
        self.home_stats = QtWidgets.QWidget()
        stats = QtWidgets.QHBoxLayout(self.home_stats)
        stats.setContentsMargins(0, 0, 0, 0)
        stats.setSpacing(16)
        self._home_stat_labels = []
        for caption in (t("Repertoires", "Repertoires"),
                        t("Stellungen im Repertoire", "Positions in repertoire"),
                        t("Diese Woche fällig", "Due this week")):
            card = QtWidgets.QFrame()
            card.setObjectName("statcard")
            cv = QtWidgets.QVBoxLayout(card)
            cv.setContentsMargins(22, 18, 22, 18)
            cv.setSpacing(4)
            n = QtWidgets.QLabel("0")
            n.setObjectName("cardN")
            cv.addWidget(n)
            lab = QtWidgets.QLabel(caption)
            lab.setObjectName("cardL")
            cv.addWidget(lab)
            stats.addWidget(card)
            self._home_stat_labels.append(n)
        outer.addWidget(self.home_stats)

        # --- Schwächen-Karte: offene Fehlerstellungen gezielt üben ---
        # Nur sichtbar, wenn es offene Fehler gibt; unabhängig vom Lernplan
        # (eine Stellung kann »nicht fällig«, aber trotzdem wacklig sein).
        self.home_weak = QtWidgets.QFrame()
        self.home_weak.setObjectName("hero")
        weak = QtWidgets.QHBoxLayout(self.home_weak)
        weak.setContentsMargins(26, 22, 26, 22)
        weak.setSpacing(16)
        wcol = QtWidgets.QVBoxLayout()
        wcol.setSpacing(4)
        weak_title = QtWidgets.QLabel(t("Das sitzt noch nicht", "Not solid yet"))
        weak_title.setObjectName("heroT")
        wcol.addWidget(weak_title)
        self.home_weak_label = self._plain_label("")
        self.home_weak_label.setObjectName("cardL")
        self.home_weak_label.setWordWrap(True)
        wcol.addWidget(self.home_weak_label)
        weak.addLayout(wcol, 1)
        self.home_weak_btn = QtWidgets.QPushButton(t("▶  Schwächen üben", "▶  Drill weak spots"))
        self.home_weak_btn.setObjectName("primary")
        self.home_weak_btn.clicked.connect(self._start_weak_session)
        weak.addWidget(self.home_weak_btn, 0, QtCore.Qt.AlignVCenter)
        outer.addWidget(self.home_weak)

        # --- Blitz-Karte: kurze Tempo-Auffrischung ---
        self.home_blitz = QtWidgets.QFrame()
        self.home_blitz.setObjectName("hero")
        blitz = QtWidgets.QHBoxLayout(self.home_blitz)
        blitz.setContentsMargins(26, 22, 26, 22)
        blitz.setSpacing(16)
        bcol = QtWidgets.QVBoxLayout()
        bcol.setSpacing(4)
        blitz_title = QtWidgets.QLabel(t("⏱ Blitz-Auffrischung", "⏱ Blitz refresh"))
        blitz_title.setObjectName("heroT")
        bcol.addWidget(blitz_title)
        blitz_desc = self._plain_label(t(
            f"{BLITZ_SECONDS} Sekunden Tempo — so viele richtige Züge wie möglich. Zählt nur den Spaß, "
            "nicht den Lernplan.",
            f"{BLITZ_SECONDS} seconds against the clock — as many correct moves as you can. Just for fun, "
            "the schedule stays untouched."))
        blitz_desc.setObjectName("cardL")
        blitz_desc.setWordWrap(True)
        bcol.addWidget(blitz_desc)
        blitz.addLayout(bcol, 1)
        self.home_blitz_btn = QtWidgets.QPushButton(t("▶  Blitz starten", "▶  Start blitz"))
        self.home_blitz_btn.setObjectName("primary")
        self.home_blitz_btn.clicked.connect(self._start_blitz_session)
        blitz.addWidget(self.home_blitz_btn, 0, QtCore.Qt.AlignVCenter)
        outer.addWidget(self.home_blitz)

        # --- Leer-Zustand (kein Repertoire): Beispiele / Hinweis ---
        self.home_empty = QtWidgets.QWidget()
        ev = QtWidgets.QVBoxLayout(self.home_empty)
        ev.setContentsMargins(0, 0, 0, 0)
        ev.setSpacing(10)
        self.home_sample_btn = QtWidgets.QPushButton(
            t("🎁  Beispiel-Eröffnungen ausprobieren", "🎁  Try the sample openings"))
        self.home_sample_btn.setObjectName("primary")
        self.home_sample_btn.clicked.connect(self._load_sample_lines)
        ev.addWidget(self.home_sample_btn, 0, QtCore.Qt.AlignLeft)
        self.home_new_hint = self._plain_label(t(
            "Noch kein Repertoire geladen — hol dir die Beispiele oder lade ein PGN "
            "links über »Alle Eröffnungen«.",
            "No repertoire loaded yet — grab the samples or load a PGN via »All openings« on the left."))
        self.home_new_hint.setObjectName("hint")
        self.home_new_hint.setWordWrap(True)
        ev.addWidget(self.home_new_hint)
        outer.addWidget(self.home_empty)

        outer.addStretch(1)
        return page

    def _open_home(self) -> None:
        self._refresh_home()
        self.stack.setCurrentIndex(12)

    def _refresh_home(self) -> None:
        from opening_trainer.tree_session import due_forecast, build_user_position_index
        today = date.today()
        fc = {"today": 0, "tomorrow": 0, "week": 0, "new": 0}
        for side_name, color in (("white", chess.WHITE), ("black", chess.BLACK)):
            f = due_forecast(self.tree_store.by_side(side_name), color, self.position_schedule, today)
            for k in fc:
                fc[k] += f[k]
        has_rep = bool(self.tree_store.all())
        total = len(self._due_items())
        self.home_forecast.setText(t(
            f"heute {fc['today']} fällig   ·   morgen {fc['tomorrow']}  ·  diese Woche {fc['week']}"
            f"   ·   noch nie geübt {fc['new']}",
            f"today {fc['today']} due   ·   tomorrow {fc['tomorrow']}  ·  this week {fc['week']}"
            f"   ·   never trained {fc['new']}"))
        # Tagesportion = fällige Wiederholungen + ein paar neue Stellungen.
        self.home_due_btn.setText(t(f"▶  Jetzt üben  ({total})", f"▶  Train now  ({total})"))
        self.home_due_btn.setEnabled(total > 0)
        # Kennzahl-Karten füllen.
        reps = len(self.tree_store.all())
        positions = (len(build_user_position_index(self.tree_store.all(), chess.WHITE))
                     + len(build_user_position_index(self.tree_store.all(), chess.BLACK)))
        for label, value in zip(self._home_stat_labels, (reps, positions, fc["week"])):
            label.setText(str(value))
        # Schwächen-Karte: nur zeigen, wenn es offene Fehler gibt.
        weak = len(self._weak_fens())
        this_round = min(weak, WEAK_SESSION_LIMIT)      # eine Runde ist gedeckelt
        if weak > WEAK_SESSION_LIMIT:
            self.home_weak_label.setText(t(
                f"{weak} Stellungen wackeln noch — diese Runde übst du die "
                f"{this_round} hartnäckigsten.",
                f"{weak} positions still shaky — this round drills the "
                f"{this_round} most stubborn."))
        else:
            self.home_weak_label.setText(t(
                f"{weak} Stellungen hast du zuletzt daneben gehabt — die wackligsten zuerst.",
                f"{weak} positions you got wrong last time — the shakiest first."))
        self.home_weak_btn.setText(t(
            f"▶  Schwächen üben  ({this_round})", f"▶  Drill weak spots  ({this_round})"))
        # Sichtbarkeit: Dashboard bei vorhandenem Repertoire, sonst Leer-Zustand.
        self.home_hero.setVisible(has_rep)
        self.home_stats.setVisible(has_rep)
        self.home_weak.setVisible(has_rep and weak > 0)
        self.home_blitz.setVisible(has_rep)
        self.home_empty.setVisible(not has_rep)
        self.home_forecast.setVisible(has_rep)      # explizit (Tests prüfen die Knöpfe direkt)
        self.home_due_btn.setVisible(has_rep)
        self.home_sample_btn.setVisible(not has_rep)
        self.home_new_hint.setVisible(not has_rep)

    def _open_default_session(self) -> None:
        """Beim Start auf den Start-Hub (von dort verzweigt alles); ohne die
        Navigations-Historie zu füllen (man startet frisch zuhause)."""
        self._go_home()

    def _run_position_session(self, items, eyebrow: str) -> None:
        """Fährt eine stellungs-basierte Sitzung über die übergebenen
        ``(tree, node_id, color)``-Items auf der Drill-Seite — gemeinsamer Kern
        für »Heute fällig«, »Stellung üben« (Einzel-Drill) und »Fehler üben«."""
        self._blitz_stop()                         # falls vorher ein Blitz lief
        self._due_queue = list(items)
        self._due_total = len(self._due_queue)
        self._due_session = True
        self._drill_manual = False
        self.tree_drill_feedback.setText("")
        self.drill_eyebrow.setText(eyebrow)
        self.tree_drill_combo.setVisible(False)
        self.drill_manual_check.setVisible(False)
        self.drill_learn_check.setVisible(True)    # Learn-Modus hier wählbar
        self.stack.setCurrentIndex(10)
        self._due_present_current()

    def _trees_for_source(self, src: str) -> list:
        """Alle (Auto-)Bäume, die aus dieser geladenen Quelle (Datei/Ordner) stammen."""
        from opening_trainer.tree_sync import pgn_files_of_source
        names = {f.name for f in pgn_files_of_source(src)} or {Path(src).name}
        return [t for t in self.tree_store.all() if t.headers.get("_source") in names]

    def _train_trees(self, trees, eyebrow: str) -> bool:
        """Übt genau diese Bäume: fällige/neue Stellungen zuerst, sonst alle.
        Gibt zurück, ob etwas zu üben war."""
        from opening_trainer.tree_session import due_drill_items, build_user_position_index
        today = date.today()
        items = []
        for sn, color in (("white", chess.WHITE), ("black", chess.BLACK)):
            st = [t for t in trees if t.side == sn]
            if st:
                items += [(t, n, color) for t, n in due_drill_items(st, color, self.position_schedule, today)]
        if not items:
            for sn, color in (("white", chess.WHITE), ("black", chess.BLACK)):
                st = [t for t in trees if t.side == sn]
                items += [(t, n, color) for (t, n) in build_user_position_index(st, color).values()]
        if items:
            self._run_position_session(items, eyebrow)
        return bool(items)

    def _train_source(self, src: str) -> None:
        trees = self._trees_for_source(src)
        if not self._train_trees(trees, t("DATEI ÜBEN", "TRAIN FILE")):
            QtWidgets.QMessageBox.information(
                self, t("Nichts zu üben", "Nothing to train"),
                t("Diese Datei enthält (noch) keine trainierbaren Stellungen — ist ihr eine Seite zugeordnet?",
                  "This file has no trainable positions (yet) — is a side assigned to it?"))

    def _start_due_session(self, only_tree=None, only_side=None) -> None:
        self._run_position_session(
            self._due_items(only_tree, only_side), t("HEUTE FÄLLIG", "DUE TODAY"))

    def _weak_fens(self, limit=None) -> list:
        """FENs der offenen Fehlerstellungen über beide Seiten (häufigste zuerst)
        — Grundlage für die Schwächen-Kachel und die »Schwächen üben«-Sitzung.
        ``limit`` deckelt auf die N hartnäckigsten, ``None`` = alle."""
        from opening_trainer.tree_session import weak_position_fens
        return weak_position_fens(
            self.tree_store.by_side("white"),
            self.tree_store.by_side("black"),
            self.stats_store,
            limit=limit,
        )

    def _start_weak_session(self) -> None:
        """Übt gezielt nur die wackligen Stellungen (offene Fehler), häufigste
        zuerst und auf eine Runde gedeckelt — nutzt dieselbe Sitzungs-Maschinerie
        wie »Heute fällig«."""
        self._drill_positions_for_fens(
            self._weak_fens(limit=WEAK_SESSION_LIMIT), t("SCHWÄCHEN", "WEAK SPOTS"))

    # --- Blitz-Sprint (Tempo-Auffrischung) -------------------------------

    def _start_blitz_session(self) -> None:
        """Startet einen Blitz-Sprint: gemischter Vorrat aller eigenen Stellungen,
        die Uhr läuft, jeder Treffer ein Punkt. Lernplan und Fehler-Statistik
        bleiben dabei unberührt — reine Tempo-Übung."""
        from opening_trainer.tree_session import blitz_pool
        pool = blitz_pool(self.tree_store.by_side("white"), self.tree_store.by_side("black"))
        if not pool:
            QtWidgets.QMessageBox.information(
                self, t("Nichts zu üben", "Nothing to train"),
                t("Lade zuerst ein Repertoire — dann gibt es Stellungen für den Blitz.",
                  "Load a repertoire first — then there are positions to blitz."))
            return
        self._blitz_pool = pool
        self._blitz = True
        self._due_session = False
        self._blitz_over = False
        self._blitz_score = 0
        self._blitz_remaining = BLITZ_SECONDS
        self._drill_manual = False
        self._tree_drill_wrong = False
        self.drill_eyebrow.setText(t("⏱ BLITZ", "⏱ BLITZ"))
        self.tree_drill_feedback.setText(t(
            "Tempo! So viele richtige Züge wie möglich, bis die Zeit abläuft.",
            "Go! As many correct moves as you can before the clock runs out."))
        # Normale Übe-Steuerung aus, Blitz-Anzeige an.
        self.tree_drill_combo.setVisible(False)
        self.drill_manual_check.setVisible(False)
        self.drill_learn_check.setVisible(False)
        self.drill_learned_btn.setVisible(False)
        self.blitz_bar.setVisible(True)
        self._blitz_update_labels()
        self._due_queue = self._blitz_shuffled()
        self._due_total = len(self._due_queue)
        self.stack.setCurrentIndex(10)
        self._blitz_present_current()
        self._blitz_timer.start()

    def _blitz_shuffled(self) -> list:
        items = list(self._blitz_pool)
        random.shuffle(items)
        return items

    def _blitz_update_labels(self) -> None:
        self.blitz_clock.setText(f"⏱ {self._blitz_remaining}")
        self.blitz_score_label.setText(
            t(f"Punkte: {self._blitz_score}", f"Score: {self._blitz_score}"))

    def _blitz_present_current(self) -> None:
        """Zeigt die aktuelle Blitz-Stellung — ohne Learn-Modus, ohne »X von Y«.
        Ist der Vorrat leer, wird neu gemischt: in 60 s gehen die Aufgaben nie aus."""
        if not self._due_queue:
            self._due_queue = self._blitz_shuffled()
        tree, node_id, color = self._due_queue[0]
        from opening_trainer.position_training import PositionTrainer
        self._tree_trainer = PositionTrainer(tree, color, start_node_id=node_id, auto_opponent=True)
        self._tree_drill_wrong = False
        self._drill_learn_active = False
        self.tree_drill_board.edit_mode = False
        self.tree_drill_board.train_color = color
        self.tree_drill_name.setText(self._tname(tree.name))
        last = None
        if self._tree_trainer.last_move_uci:
            m = chess.Move.from_uci(self._tree_trainer.last_move_uci)
            last = (m.from_square, m.to_square)
        self.tree_drill_board.set_flipped(color == chess.BLACK)
        self.tree_drill_board.set_board(self._tree_trainer.board, last_move=last)
        self.tree_drill_status.setText(t("Du bist am Zug.", "Your move."))
        self._drill_update_context()

    def _blitz_advance(self) -> None:
        if self._due_queue:
            self._due_queue.pop(0)
        self._blitz_present_current()

    def _blitz_tick(self) -> None:
        self._blitz_remaining -= 1
        if self._blitz_remaining <= 0:
            self._blitz_remaining = 0
            self._blitz_update_labels()
            self._blitz_finish()
            return
        self._blitz_update_labels()

    def _blitz_finish(self) -> None:
        """Zeit abgelaufen: Uhr stoppen, Brett sperren, Endstand zeigen."""
        self._blitz_timer.stop()
        self._blitz_over = True
        self._tree_trainer = None
        self.tree_drill_status.setText(t(
            f"⏱ Zeit! Endstand: {self._blitz_score} Treffer. »Neu« startet eine neue Runde.",
            f"⏱ Time! Final score: {self._blitz_score}. »Restart« for another round."))
        self.tree_drill_feedback.setText("")

    def _blitz_stop(self) -> None:
        """Blitz verlassen (z. B. Seitenwechsel): Uhr stoppen, Anzeige und Modus aus."""
        self._blitz_timer.stop()
        self._blitz = False
        self._blitz_over = False
        self.blitz_bar.setVisible(False)

    def _drill_positions_for_fens(self, fens, eyebrow: str) -> None:
        """Lenkt die alten Einzelstellungs-Drills (Statistik-Fehler, »Fehler
        üben«, Partie-Abweichung) auf eine stellungs-basierte Sitzung um, indem
        jede Stellung über die Bäume auf (tree, node, color) aufgelöst wird."""
        items = []
        for fen in fens:
            loc = self._locate_in_trees(fen)
            if loc is not None:
                items.append(loc)
        if items:
            self._run_position_session(items, eyebrow)

    def _locate_in_trees(self, fen: str):
        """(tree, node_id, color) für eine Stellung (FEN) über beide Seiten,
        sonst ``None``. EPD = die ersten vier FEN-Felder."""
        from opening_trainer.tree_session import build_user_position_index, locate_position
        epd = " ".join(fen.split(" ")[:4])
        for side_name, color in (("white", chess.WHITE), ("black", chess.BLACK)):
            index = build_user_position_index(self.tree_store.by_side(side_name), color)
            hit = locate_position(index, epd)
            if hit is not None:
                return (hit[0], hit[1], color)
        return None

    def _due_present_current(self) -> None:
        if not self._due_queue:
            self._tree_trainer = None
            self.tree_drill_name.setText(t("Heute fällig", "Due today"))
            if self._due_total:
                self.tree_drill_status.setText(t(
                    f"Geschafft 🎉 — {self._due_total} Stellungen wiederholt. Nichts mehr fällig.",
                    f"Done 🎉 — reviewed {self._due_total} positions. Nothing left due."))
            else:
                self.tree_drill_status.setText(t(
                    "Nichts fällig — schau morgen wieder vorbei. 🎉",
                    "Nothing due — come back tomorrow. 🎉"))
            self.tree_drill_board.set_board(chess.Board())
            self._drill_update_context()
            return
        tree, node_id, color = self._due_queue[0]
        from opening_trainer.position_training import PositionTrainer
        self._tree_trainer = PositionTrainer(tree, color, start_node_id=node_id, auto_opponent=True)
        self._tree_drill_wrong = False
        self.tree_drill_board.edit_mode = False
        self.tree_drill_board.train_color = color
        done = self._due_total - len(self._due_queue)
        self.tree_drill_name.setText(self._tname(tree.name))
        last = None
        if self._tree_trainer.last_move_uci:
            m = chess.Move.from_uci(self._tree_trainer.last_move_uci)
            last = (m.from_square, m.to_square)
        self.tree_drill_board.set_flipped(color == chess.BLACK)
        self.tree_drill_board.set_board(self._tree_trainer.board, last_move=last)
        from opening_trainer.scheduler import is_new
        epd = self._tree_trainer.board.epd()
        learn = bool(self._drill_learn_new and is_new(self.position_schedule.card_for(epd)))
        self._drill_learn_active = learn
        self.drill_learned_btn.setVisible(learn)
        if learn:
            # Learn-Modus: den vorgesehenen Zug gleich zeigen (nicht abfragen).
            sol = self._tree_trainer.expected_solution()
            san = sol.san if sol else "—"
            if sol is not None:
                m = chess.Move.from_uci(sol.uci)
                self.tree_drill_board.show_solution(m.from_square, m.to_square)
            self.tree_drill_status.setText(t(
                f"Neu — Stellung {done + 1} von {self._due_total}. Der Zug hier ist {san}. "
                "Präg ihn dir ein, dann »Verstanden«.",
                f"New — position {done + 1} of {self._due_total}. The move here is {san}. "
                "Memorise it, then »Got it«."))
        else:
            self.tree_drill_status.setText(t(
                f"Heute fällig — Stellung {done + 1} von {self._due_total}. Du bist am Zug.",
                f"Due today — position {done + 1} of {self._due_total}. Your move."))
        self._drill_update_context()

    def _drill_update_context(self) -> None:
        """Vereinte Ansicht: zeigt die Linie bis hierher (»wo bin ich?«) und die
        »Idee« (Kommentar des vorgesehenen Zuges, falls vorhanden)."""
        tr = self._tree_trainer
        if tr is None:
            self.tree_drill_line.setText("")
            self.tree_drill_note.setVisible(False)
            return
        de = (i18n.language() == "de")
        start = chess.Board(tr.tree.start_fen) if tr.tree.start_fen else chess.Board()
        parts = []
        b = start
        for mv in tr.board.move_stack:
            num = b.fullmove_number
            dots = "." if b.turn == chess.WHITE else "…"
            san = b.san(mv)
            if de:
                san = san.translate(str.maketrans({"N": "S", "B": "L", "R": "T", "Q": "D"}))
            parts.append(f"{num}{dots}{san}")
            b.push(mv)
        line = "  ".join(parts)
        if tr.is_user_turn() and not tr.is_finished():
            line = (line + "   …?") if line else t("Du bist am Zug …?", "Your move …?")
        self.tree_drill_line.setText(line)
        # Idee = Kommentar des ersten vorgesehenen Zuges an dieser Stellung.
        note = ""
        kids = tr.tree.children_of(tr.node.id)
        if kids and kids[0].comment:
            note = kids[0].comment
        self.tree_drill_note.setText(t("💡 Idee: ", "💡 Idea: ") + note if note else "")
        self.tree_drill_note.setVisible(bool(note))

    def _tree_drill_present(self) -> None:
        tr = self._tree_trainer
        if tr is None:
            return
        last = None
        if tr.last_move_uci:
            m = chess.Move.from_uci(tr.last_move_uci)
            last = (m.from_square, m.to_square)
        self.tree_drill_board.set_flipped(tr.side == chess.BLACK)
        self.tree_drill_board.set_board(tr.board, last_move=last)
        if tr.is_finished():
            self.tree_drill_status.setText(t("Linie zu Ende 🎉 — »Neu« startet von vorn.",
                                             "End of line 🎉 — »Restart« to begin again."))
        elif not tr.is_user_turn():
            opp = self._tcolor(chess.WHITE if tr.side == chess.BLACK else chess.BLACK)
            opts = ", ".join(sorted(tr.opponent_moves().values()))
            self.tree_drill_status.setText(t(
                f"{opp} am Zug — spiel eine deiner vorbereiteten Optionen: {opts}",
                f"{opp} to move — play one of your prepared options: {opts}"))
        else:
            self.tree_drill_status.setText(t("Du bist am Zug.", "Your move."))
        self._drill_update_context()

    def _drill_toggle_learn(self, checked: bool) -> None:
        self._drill_learn_new = checked
        if self._due_session and self._due_queue:
            self._due_present_current()        # aktuelle Stellung passend neu zeigen

    def _drill_mark_learned(self) -> None:
        """Learn-Modus: »Verstanden« — die neue Stellung als gelernt einplanen
        (kommt zur echten Abfrage wieder) und zur nächsten gehen."""
        tr = self._tree_trainer
        if tr is None or not self._drill_learn_active:
            return
        epd = tr.board.epd()
        new_card = schedule_review(self.position_schedule.card_for(epd), True, date.today())
        self.position_schedule.set_card(epd, new_card)
        self.position_schedule.save(self.position_schedule_path)
        sol = tr.expected_solution()
        self.stats_store.add_event(
            source_name="", line_name=tr.tree.name, fen_before=tr.board.fen(),
            expected_san=(sol.san if sol else None),
            played_san=(sol.san if sol else None), correct=True)
        self.stats_store.save(self.stats_path)
        self._show_next_review(new_card, True)
        self._drill_learn_active = False
        self.drill_learned_btn.setVisible(False)
        if self._due_queue:
            self._due_queue.pop(0)
        self._due_present_current()

    def _tree_drill_on_move(self, from_square: int, to_square: int) -> None:
        if self._blitz_over:                    # Zeit abgelaufen: keine Züge mehr
            return
        tr = self._tree_trainer
        if tr is None or tr.is_finished() or self._drill_learn_active:
            return
        try:
            move = tr.board.find_move(from_square, to_square)
        except ValueError:
            return

        if not tr.is_user_turn():
            # Manueller Modus: der Nutzer spielt den Gegnerzug (muss ein Ast sein).
            if tr.play_opponent_move_uci(move.uci()):
                self._tree_drill_present()
            else:
                self.tree_drill_board.flash_wrong(to_square)
                opts = ", ".join(sorted(tr.opponent_moves().values())) or "—"
                self.tree_drill_status.setText(t(
                    "Das ist nicht vorbereitet. Spiel eine deiner Optionen: " + opts,
                    "That move isn't prepared. Play one of your options: " + opts))
            return

        fen_before = tr.board.fen()
        epd_before = tr.board.epd()
        result = tr.play_user_move_uci(move.uci())

        if result.kind == "wrong":
            self._tree_drill_wrong = True
            self.tree_drill_board.flash_wrong(to_square)
            # Im Blitz keinen verratenden Hinweis zeigen — nur »nochmal«.
            hint = ""
            if not self._blitz and result.expected_san:
                hint = "  " + t("Richtig wäre:", "Correct would be:") + " " + result.expected_san
            self.tree_drill_status.setText(t("Noch nicht.", "Not yet.") + hint)
            return

        if result.kind == "correct":
            if self._blitz:                      # Tempo-Modus: Punkt, dann weiter —
                self._blitz_score += 1           # Lernplan/Statistik bleiben unberührt
                self._blitz_update_labels()
                self._blitz_advance()
                return
            passed = not self._tree_drill_wrong
            today = date.today()
            card = self.position_schedule.card_for(epd_before)
            new_card = schedule_review(card, passed, today)
            self.position_schedule.set_card(epd_before, new_card)
            self.position_schedule.save(self.position_schedule_path)
            self._show_next_review(new_card, passed)
            self.stats_store.add_event(
                source_name="", line_name=tr.tree.name, fen_before=fen_before,
                expected_san=result.expected_san, played_san=result.played_san, correct=passed)
            self.stats_store.save(self.stats_path)
            self._tree_drill_wrong = False
            if self._due_session:
                if self._due_queue:
                    self._due_queue.pop(0)        # erledigte Stellung abhaken
                self._due_present_current()
            else:
                self._tree_drill_present()

    def _show_next_review(self, card, passed: bool) -> None:
        """Macht die Spaced-Repetition-Mechanik sichtbar: wann die Stellung wieder
        fällig wird."""
        if passed:
            x = card.interval_days
            unit = t("Tag", "day") if x == 1 else t("Tagen", "days")
            self.tree_drill_feedback.setText(t(
                f"✓ Sitzt — nächste Wiederholung in {x} {unit}.",
                f"✓ Got it — next review in {x} {unit}."))
        else:
            self.tree_drill_feedback.setText(t(
                "✓ Richtig (mit Hilfe) — kommt heute nochmal dran.",
                "✓ Correct (with help) — comes up again today."))

    def _tree_drill_restart(self) -> None:
        if self._blitz:
            self._start_blitz_session()          # »Neu« = neue Blitz-Runde
        elif self._due_session:
            self._start_due_session()
        elif self._drill_tree is not None:
            self._start_tree_drill(self._drill_tree)

    def _tree_drill_solution(self) -> None:
        tr = self._tree_trainer
        if tr is None:
            return
        sol = tr.expected_solution()
        if sol is not None:
            self._tree_drill_wrong = True       # Lösung gezeigt => zählt als nicht bestanden
            move = chess.Move.from_uci(sol.uci)
            self.tree_drill_board.show_solution(move.from_square, move.to_square)
            self.tree_drill_status.setText(t("Lösung:", "Solution:") + " " + sol.san)

    def _show_getting_started(self) -> None:
        box = QtWidgets.QMessageBox(self)
        box.setWindowTitle(t("Erste Schritte", "Getting started"))
        box.setTextFormat(QtCore.Qt.TextFormat.RichText)
        box.setText(t(
            "<b>So legst du los:</b>"
            "<ul>"
            "<li><b>Eigenes Repertoire laden:</b> »Alle Eröffnungen ansehen …« → "
            "»PGN laden …« — z. B. eine als PGN exportierte Lichess-Studie. Oder "
            "probier zuerst die <b>Beispiel-Eröffnungen</b> auf dem Startbildschirm.</li>"
            "<li><b>Üben:</b> Spiel die richtigen Züge aufs Brett. Die App plant "
            "Wiederholungen automatisch (»heute dran«).</li>"
            "<li><b>Stockfish ist eingebaut:</b> Repertoire-Prüfung, »War mein Zug gut?«, "
            "Bewertungs-Leiste und Sparring — nichts zu installieren.</li>"
            "<li><b>Lichess-Explorer:</b> braucht einen kostenlosen Token — der Knopf "
            "»🔑 Lichess-Token« richtet ihn in einem Klick ein.</li>"
            "<li><b>Partien auswerten:</b> lade eine PGN deiner gespielten Partien und "
            "sieh, wo du vom Repertoire abgewichen bist und wo du gepatzt hast.</li>"
            "<li><b>Verzweigte Repertoires (Bäume):</b> wenn dein Gegner mehrere Antworten "
            "hat, baust du im <b>Repertoire-Editor</b> (»Gehe zu → Repertoire-Editor«, ⌘E) "
            "eigene Varianten — oder lädst eine varianten-reiche PGN (z. B. Lichess-Studie); "
            "der Import übernimmt die Verzweigungen. Üben: »Heute üben« (Tagessitzung, ⌘D) "
            "oder »Repertoire-Baum« (⌘R) → »Dieses Repertoire üben«.</li>"
            "<li><b>Sprache:</b> Menü »Ansicht → Sprache« (gilt sofort).</li>"
            "</ul>",
            "<b>How to get started:</b>"
            "<ul>"
            "<li><b>Load your own repertoire:</b> “Browse all openings …” → "
            "“Load PGN …” — e.g. a Lichess study exported as PGN. Or try the "
            "<b>sample openings</b> on the start screen first.</li>"
            "<li><b>Practice:</b> play the correct moves on the board. The app "
            "schedules reviews automatically (“due today”).</li>"
            "<li><b>Stockfish is built in:</b> repertoire check, “was my move good?”, "
            "evaluation bar and sparring — nothing to install.</li>"
            "<li><b>Lichess explorer:</b> needs a free token — the “🔑 Lichess token” "
            "button sets it up in one click.</li>"
            "<li><b>Review your games:</b> load a PGN of your played games and see "
            "where you left your repertoire and where you blundered.</li>"
            "<li><b>Branched repertoires (trees):</b> when your opponent has several "
            "replies, build your own variations in the <b>Repertoire editor</b> "
            "(“Go → Repertoire editor”, ⌘E) — or load a variation-rich PGN (e.g. a Lichess "
            "study); the import keeps the branches. Practise via “Train today” (daily "
            "session, ⌘D) or “Repertoire tree” (⌘R) → “Train this repertoire”.</li>"
            "<li><b>Language:</b> “View → Language” menu (takes effect immediately).</li>"
            "</ul>",
        ))
        box.exec()

    def _show_about(self) -> None:
        QtWidgets.QMessageBox.about(
            self,
            t("Über Opening Trainer", "About Opening Trainer"),
            f"<b>Opening Trainer</b> {APP_VERSION}<br><br>"
            + t(
                "Dein persönlicher Schach-Eröffnungstrainer.<br>"
                "Üben, tägliche Wiederholung, Fehler-Drill, Auswertung, Stockfish-Analyse.",
                "Your personal chess opening trainer.<br>"
                "Practice, daily review, mistake drills, analysis, Stockfish review.",
            )
            + "<br><br>"
            + t(
                "Freie Software unter der GPLv3+ (siehe LICENSE / NOTICE.md).",
                "Free software under the GPLv3+ (see LICENSE / NOTICE.md).",
            )
            + "<br>"
            "Engine: Stockfish (GPLv3). python-chess (GPL-3.0+).<br>"
            "Qt/PySide6 (LGPLv3). Pieces: Cburnett (GPLv2+/BSD/GFDL).",
        )

    def _install_shortcuts(self) -> None:
        # Die gewohnten Sprung-Kürzel (früher am »Gehe zu«-Menü) bleiben erhalten,
        # auch ohne sichtbares Menü — die Seitenleiste übernimmt die Navigation.
        for keys, slot in [
            ("Ctrl+1", self._open_home),
            ("Ctrl+2", self._open_library),
            ("Ctrl+3", self._open_stats),
            ("Ctrl+4", self._open_progress),
            ("Ctrl+5", self._open_game_review),
            ("Ctrl+6", self._open_tuv),
            ("Ctrl+R", self._open_repertoire_tree),
            ("Ctrl+E", self._open_editor),
            ("Ctrl+D", self._open_due_overview),
            ("Ctrl+T", self._open_tree_drill),
        ]:
            QtGui.QShortcut(QtGui.QKeySequence(keys), self).activated.connect(slot)

    def _restore_geometry(self) -> None:
        self._qsettings = QtCore.QSettings("OpeningTrainer", "OpeningTrainer")
        geo = self._qsettings.value("geometry")
        if geo is not None:
            self.restoreGeometry(geo)

    def _stop_all_threads(self) -> None:
        """Beendet alle Hintergrund-Worker und ihre Stockfish-Engines sauber.

        Idempotent und gegen jeden Beende-Weg abgesichert: erst die Engines
        beenden (damit blockierende analyse()-Aufrufe zurückkehren), dann jeden
        QThread quit()+wait(); läuft ein Thread nach dem Timeout noch, wird er
        per terminate() zwangsbeendet — denn ein noch laufender Thread im
        Destruktor löst Qts qFatal/abort() aus (SIGABRT beim Programmende)."""
        if getattr(self, "_threads_stopped", False):
            return
        self._threads_stopped = True

        worker = getattr(self, "_tuv_worker", None)
        if worker is not None:
            try:
                worker.cancel()
            except Exception:  # noqa: BLE001
                pass
        eval_engine = getattr(self, "_eval_engine", None)
        if eval_engine not in (None, "unset"):
            try:
                eval_engine.quit()
            except Exception:  # noqa: BLE001
                pass
        # Worker mit eigener Warteschleife erst über 'shutdown' aus dem Loop holen.
        for thread_attr, worker_attr in (
            ("_spar_thread", "_spar_worker"),
        ):
            th = getattr(self, thread_attr, None)
            wk = getattr(self, worker_attr, None)
            if th is not None and wk is not None:
                try:
                    QtCore.QMetaObject.invokeMethod(
                        wk, "shutdown", QtCore.Qt.BlockingQueuedConnection
                    )
                except Exception:  # noqa: BLE001
                    pass

        for attr in ("_tuv_thread", "_spar_thread", "_viewer_anal_thread"):
            th = getattr(self, attr, None)
            if th is None:
                continue
            try:
                th.quit()
                if not th.wait(3000):
                    th.terminate()      # Notbremse: verhindert SIGABRT im Destruktor
                    th.wait()
            except RuntimeError:
                pass                    # zugrunde liegendes C++-Objekt schon gelöscht
            setattr(self, attr, None)

    def closeEvent(self, event) -> None:
        self._stop_all_threads()
        try:
            self._qsettings.setValue("geometry", self.saveGeometry())
        except Exception:  # noqa: BLE001
            pass
        super().closeEvent(event)

    # --- Daten -----------------------------------------------------------

    def _effective_sources(self) -> list:
        """Liste der geladenen PGN-Quellen; fällt auf die alten Einzelfelder zurück.

        Beim Übergang vom alten Einzelquellen-Modell werden BEIDE Altfelder
        (Datei und Ordner) übernommen — sonst verdrängte eine einzelne zuletzt
        geladene Datei den ganzen Ordner und das Repertoire wirkte nach Neustart
        „verschwunden". Sobald der Nutzer einmal lädt/entfernt, ist pgn_sources
        gesetzt und dieser Fallback greift nicht mehr."""
        srcs = list(self.settings_store.settings.pgn_sources)
        if not srcs:
            s = self.settings_store.settings
            for legacy in (s.last_pgn_folder, s.last_pgn_path):
                if legacy and legacy not in srcs:
                    srcs.append(legacy)
        return srcs

    def _load_lines(self) -> list:
        """Lädt ALLE Quellen (Dateien und Ordner) und führt sie zusammen
        (dedupliziert nach Quelle + Name)."""
        lines: list = []
        seen: set = set()
        for src in self._effective_sources():
            p = Path(src)
            if not p.exists():
                continue
            try:
                part = load_pgn_folder(p) if p.is_dir() else load_pgn_file(p)
            except Exception:  # noqa: BLE001 — eine kaputte Quelle darf die anderen nicht blockieren
                continue
            for line in part:
                key = (line.source_name, line.name)
                if key not in seen:
                    seen.add(key)
                    lines.append(line)
        return lines

    def _catalog(self) -> list:
        """Die Eröffnungs-Liste (früher self.lines) — abgeleitet aus den Auto-Bäumen,
        also direkt aus der EINZIGEN Quelle. Ein Eintrag je Auto-Baum (Name/Quelle/
        Hauptpfad/Seite); Editor-eigene Bäume zeigt die Bibliothek separat."""
        return build_catalog(self.tree_store.all())

    def _sync_auto_trees(self) -> None:
        """Hält die automatisch erzeugten Repertoire-Bäume + Positions-Karten mit den
        geladenen Quellen + Seiten-Zuordnungen in Sync (speist die Tagessitzung).
        Idempotent, additiv — Editor-Bäume bleiben. Darf den Ablauf nie verhindern."""
        try:
            sync_auto_trees(self._effective_sources(), self.opening_sides,
                            self.schedule_store, self.tree_store, self.position_schedule)
            self.tree_store.save(self.trees_path)
            self.position_schedule.save(self.position_schedule_path)
        except Exception:  # noqa: BLE001
            pass

    def _add_pgn_source(self, path: str) -> int:
        """Fügt eine PGN-Quelle (Datei ODER Ordner) HINZU (ersetzt nicht). Gibt die
        Zahl der neu hinzugekommenen Eröffnungen zurück."""
        before = len(self._catalog())
        srcs = self._effective_sources()
        path = str(Path(path))
        if path not in srcs:
            srcs.append(path)
        self.settings_store.update(pgn_sources=tuple(srcs))
        self.settings_store.save(self.settings_path)
        self._migrate_sides_from_groups(self._load_lines())
        self._sync_auto_trees()
        self._refresh_library()
        return max(0, len(self._catalog()) - before)

    def _custom_trees(self) -> list:
        """Bäume, die NICHT aus einer geladenen PGN-Quelle stammen (selbst gebaut,
        importiert oder Reste alter Importe). Genau hier sammeln sich verwaiste
        Bäume, die Zähler/Repertoire-Baum aufblähen."""
        return [tr for tr in self.tree_store.all() if tr.headers.get("_auto") != "1"]

    def _manage_trees(self) -> None:
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle(t("Eigene Repertoire-Bäume", "Custom repertoire trees"))
        lay = QtWidgets.QVBoxLayout(dlg)
        info = self._plain_label(t(
            "Bäume, die NICHT aus einer geladenen PGN-Datei stammen (selbst gebaut, "
            "importiert oder Reste alter Importe). Hier kannst du aufräumen — z. B. "
            "verwaiste Bäume entfernen, die die Zähler aufblähen. Bäume aus geladenen "
            "Dateien verwaltest du über »Geladene Repertoires«.",
            "Trees NOT from a loaded PGN file (built yourself, imported, or leftovers of "
            "old imports). Clean up here — e.g. remove orphaned trees that inflate the "
            "counters. Trees from loaded files are managed under »Loaded repertoires«."))
        info.setWordWrap(True)
        lay.addWidget(info)
        listw = QtWidgets.QListWidget()
        listw.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        lay.addWidget(listw)
        count_lbl = QtWidgets.QLabel("")

        def refresh() -> None:
            listw.clear()
            for tr in sorted(self._custom_trees(), key=lambda x: self._tree_family(x).casefold()):
                side = {"white": t("Weiß", "White"), "black": t("Schwarz", "Black")}.get(tr.side, "—")
                plies = max(0, len(tr.nodes) - 1)
                item = QtWidgets.QListWidgetItem(
                    f"{self._tree_family(tr)}    ({side}, {plies} {t('Halbzüge', 'plies')})")
                item.setData(QtCore.Qt.UserRole, tr.id)
                item.setToolTip(tr.name or "")
                listw.addItem(item)
            count_lbl.setText(t(f"{listw.count()} eigene Bäume", f"{listw.count()} custom trees"))

        def delete_selected() -> None:
            ids = [it.data(QtCore.Qt.UserRole) for it in listw.selectedItems()]
            if not ids:
                return
            if QtWidgets.QMessageBox.warning(
                dlg, t("Bäume löschen?", "Delete trees?"),
                t(f"{len(ids)} Baum/Bäume dauerhaft löschen? Geladene PGN-Dateien bleiben unberührt.",
                  f"Delete {len(ids)} tree(s) permanently? Loaded PGN files stay untouched."),
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.Cancel,
                QtWidgets.QMessageBox.StandardButton.Cancel,
            ) == QtWidgets.QMessageBox.StandardButton.Yes:
                for tid in ids:
                    self.tree_store.remove(tid)
                self.tree_store.save(self.trees_path)
                self._refresh_library()
                refresh()

        refresh()
        lay.addWidget(count_lbl)
        btns = QtWidgets.QHBoxLayout()
        sel = QtWidgets.QPushButton(t("Alle auswählen", "Select all"))
        sel.clicked.connect(listw.selectAll)
        rm = QtWidgets.QPushButton(t("Ausgewählte löschen", "Delete selected"))
        rm.clicked.connect(delete_selected)
        close = QtWidgets.QPushButton(t("Schließen", "Close"))
        close.clicked.connect(dlg.accept)
        btns.addWidget(sel)
        btns.addWidget(rm)
        btns.addStretch(1)
        btns.addWidget(close)
        lay.addLayout(btns)
        dlg.resize(540, 440)
        dlg.exec()

    def _reset_repertoire(self) -> None:
        if QtWidgets.QMessageBox.question(
            self, t("Repertoire leeren", "Clear repertoire"),
            t("Alles aus der App entfernen — geladene PGN-Quellen UND alle "
              "Repertoire-Bäume (auch selbst gebaute/importierte)? Deine PGN-Dateien "
              "auf der Platte bleiben unberührt; nur der Inhalt der App wird geleert.",
              "Remove everything from the app — loaded PGN sources AND all repertoire "
              "trees (including ones you built/imported)? Your PGN files on disk stay "
              "untouched; only the app's content is cleared."),
        ) != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        self.settings_store.update(pgn_sources=(), last_pgn_path="", last_pgn_folder="", last_pgn_kind="")
        self.settings_store.save(self.settings_path)
        # ALLE Bäume leeren (auch Nicht-Auto): sonst überleben alte/verwaiste Bäume
        # das Leeren und verfälschen weiter Zähler/Repertoire-Baum.
        self.tree_store = RepertoireTreeStore()
        self.tree_store.save(self.trees_path)
        self._sync_auto_trees()              # baut aus den (nun leeren) Quellen = nichts
        pass
        self._refresh_library()
        pass

    def _source_opening_count(self, src: str) -> int:
        p = Path(src)
        if not p.exists():
            return 0
        try:
            return len(load_pgn_folder(p) if p.is_dir() else load_pgn_file(p))
        except Exception:  # noqa: BLE001
            return 0

    def _remove_pgn_source(self, src: str) -> None:
        srcs = [s for s in self._effective_sources() if s != src]
        self.settings_store.update(pgn_sources=tuple(srcs))
        self.settings_store.save(self.settings_path)
        self._sync_auto_trees()
        self._refresh_library()

    def _manage_sources(self) -> None:
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle(t("Geladene Repertoires", "Loaded repertoires"))
        lay = QtWidgets.QVBoxLayout(dlg)
        info = self._plain_label(t(
            "Geladene PGN-Quellen. »Entfernen« lädt die Eröffnungen aus der App aus — "
            "die PGN-Datei auf der Platte bleibt unberührt.",
            "Loaded PGN sources. »Remove« un-loads its openings from the app — "
            "the PGN file on disk stays untouched."))
        info.setWordWrap(True)
        lay.addWidget(info)
        listw = QtWidgets.QListWidget()
        lay.addWidget(listw)

        def refresh() -> None:
            listw.clear()
            for src in self._effective_sources():
                p = Path(src)
                kind = t("Ordner", "folder") if p.is_dir() else t("Datei", "file")
                n = self._source_opening_count(src)
                item = QtWidgets.QListWidgetItem(
                    f"{p.name}    ({n} {t('Eröffnungen', 'openings')}, {kind})")
                item.setData(QtCore.Qt.UserRole, src)
                item.setToolTip(src)
                listw.addItem(item)
            if listw.count():
                listw.setCurrentRow(0)

        refresh()

        def do_remove() -> None:
            item = listw.currentItem()
            if item is None:
                return
            src = item.data(QtCore.Qt.UserRole)
            if QtWidgets.QMessageBox.warning(
                dlg, t("Repertoire entfernen?", "Remove repertoire?"),
                t(f"»{Path(src).name}« aus der App entfernen?\n\nDie Eröffnungen werden "
                  "ausgeladen. Deine PGN-Datei auf der Platte bleibt erhalten.",
                  f"Remove »{Path(src).name}« from the app?\n\nIts openings get unloaded. "
                  "Your PGN file on disk is kept."),
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.Cancel,
                QtWidgets.QMessageBox.StandardButton.Cancel,
            ) == QtWidgets.QMessageBox.StandardButton.Yes:
                self._remove_pgn_source(src)
                refresh()

        def do_train() -> None:
            item = listw.currentItem()
            if item is None:
                return
            dlg.accept()
            self._train_source(item.data(QtCore.Qt.UserRole))

        btns = QtWidgets.QHBoxLayout()
        train = QtWidgets.QPushButton(t("▶  Ausgewählte üben", "▶  Train selected"))
        train.setObjectName("primary")
        train.clicked.connect(do_train)
        remove = QtWidgets.QPushButton(t("Ausgewählte entfernen", "Remove selected"))
        remove.clicked.connect(do_remove)
        close = QtWidgets.QPushButton(t("Schließen", "Close"))
        close.clicked.connect(dlg.accept)
        btns.addWidget(train)
        btns.addWidget(remove)
        btns.addStretch(1)
        btns.addWidget(close)
        lay.addLayout(btns)
        dlg.resize(520, 360)
        dlg.exec()

    def _build_ui(self) -> None:
        self.stack = QtWidgets.QStackedWidget()
        # Feste Navigations-Seitenleiste LINKS, Inhalt rechts. Die Leiste ist auf
        # jeder Seite sichtbar und ersetzt das frühere »Gehe zu«-Menü.
        central = QtWidgets.QWidget()
        root = QtWidgets.QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_sidebar())
        # Orientierungs-Label bleibt (unsichtbar) erhalten, damit Fenstertitel-Code
        # weiterläuft — die eigentliche Überschrift steht jetzt je Seite im Inhalt.
        self.page_head = QtWidgets.QLabel("")
        self.page_head.setObjectName("pagehead")
        self.page_head.setVisible(False)
        root.addWidget(self.stack, 1)
        self.setCentralWidget(central)
        self.stack.addWidget(self._build_train_page())     # 0
        self.stack.addWidget(self._build_library_page())   # 1
        self.stack.addWidget(self._build_stats_page())     # 2
        self.stack.addWidget(self._build_tuv_page())       # 3
        self.stack.addWidget(self._build_sparring_page())  # 4
        self.stack.addWidget(self._build_progress_page())  # 5
        self.stack.addWidget(self._build_explorer_page())  # 6
        self.stack.addWidget(self._build_game_review_page())  # 7
        self.stack.addWidget(self._build_game_viewer_page())  # 8
        self.stack.addWidget(self._build_editor_page())       # 9
        self.stack.addWidget(self._build_tree_drill_page())   # 10
        self.stack.addWidget(self._build_due_overview_page())  # 11
        self.stack.addWidget(self._build_home_page())          # 12  (Start-Hub)
        self.stack.addWidget(self._build_repertoire_tree_page())  # 13  (Repertoire-Baum)
        self.setStyleSheet(build_style(UI_THEMES[self._ui_theme]))
        self.resize(1040, 720)
        # Seitenwechsel mitschreiben (für »Zurück« zur vorigen Seite).
        self._nav_current = self.stack.currentIndex()
        self.page_head.setText(self._page_name(self._nav_current))   # Kopfzeile von Anfang an
        self._update_nav_active(self._nav_current)
        self.stack.currentChanged.connect(self._on_page_changed)

    def _on_page_changed(self, new: int) -> None:
        if self._nav_suppress:
            self._nav_suppress = False
        elif self._nav_current is not None and self._nav_current != new:
            self._nav_history.append(self._nav_current)
            del self._nav_history[:-50]          # nicht unbegrenzt wachsen lassen
        self._nav_current = new
        self.setWindowTitle(self._page_title(new))   # Orientierung: Fenstertitel …
        if hasattr(self, "page_head"):               # … und sichtbare Kopfzeile
            self.page_head.setText(self._page_name(new))
        self._update_nav_active(new)             # aktive Seite in der Leiste markieren
        if new != 10 and self._blitz:            # Drill-Seite verlassen -> Blitz beenden
            self._blitz_stop()
        if new == 11:                            # »Heute fällig«-Übersicht stets frisch zeigen
            self._refresh_due_overview()
        elif new == 12:                          # Start-Hub aktualisieren
            self._refresh_home()

    # --- Seitenleiste (feste Navigation) ---------------------------------

    @staticmethod
    def _amp(label: str) -> str:
        """»&« in Knopf-Beschriftungen verdoppeln, sonst macht Qt daraus ein
        Tastatur-Kürzel (»Trefferquote & Fehler« → »Trefferquote _Fehler«)."""
        return label.replace("&", "&&")

    def _build_sidebar(self) -> QtWidgets.QWidget:
        side = QtWidgets.QWidget()
        side.setObjectName("sidebar")
        side.setFixedWidth(244)
        v = QtWidgets.QVBoxLayout(side)
        v.setContentsMargins(14, 18, 14, 14)
        v.setSpacing(2)
        v.addWidget(QtWidgets.QLabel("♟  Opening Trainer", objectName="brand"))
        self._nav_buttons: dict[int, QtWidgets.QPushButton] = {}

        def item(label: str, opener, target) -> None:
            b = QtWidgets.QPushButton(self._amp(label))
            b.setObjectName("nav")
            b.setCursor(QtCore.Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, o=opener: o())
            if target is not None:               # None = Aktion ohne eigene Seite
                self._nav_buttons[target] = b
            v.addWidget(b)

        item(t("⌂  Start", "⌂  Home"), self._open_home, 12)
        groups = [
            (t("ÜBEN", "PRACTICE"), [
                (t("▶  Heute fällig", "▶  Due today"), self._open_due_overview, 11),
                (t("⏱  Blitz", "⏱  Blitz"), self._start_blitz_session, None),
                (t("Baum frei durchspielen", "Free-play a tree"), self._open_tree_drill, 10),
                (t("Repertoire-Prüfung", "Repertoire check"), self._open_tuv, 3),
            ]),
            (t("REPERTOIRE", "REPERTOIRE"), [
                (t("Repertoire-Baum", "Repertoire tree"), self._open_repertoire_tree, 13),
                (t("Alle Eröffnungen", "All openings"), self._open_library, 1),
                (t("Repertoire-Editor", "Repertoire editor"), self._open_editor, 9),
            ]),
            (t("AUSWERTEN", "REVIEW"), [
                (t("Fortschritt", "Progress"), self._open_progress, 5),
                (t("Trefferquote & Fehler", "Accuracy & mistakes"), self._open_stats, 2),
                (t("Partien auswerten", "Review games"), self._open_game_review, 7),
            ]),
            (t("ERKUNDEN", "EXPLORE"), [
                (t("Eröffnungs-Explorer", "Opening explorer"), self._open_explorer, 6),
                (t("Gegen Stockfish", "Play Stockfish"), self._open_sparring, 4),
            ]),
        ]
        for header, items in groups:
            v.addWidget(QtWidgets.QLabel(header, objectName="navgroup"))
            for label, opener, target in items:
                item(label, opener, target)
        v.addStretch(1)
        return side

    def _nav_active_for(self, page: int) -> int:
        """Welcher Navigations-Eintrag wird für diese Seite hervorgehoben?
        Seiten ohne eigenen Eintrag spiegeln auf den passenden zurück."""
        return {8: 7, 10: 10, 0: 12}.get(page, page)

    def _update_nav_active(self, page: int) -> None:
        target = self._nav_active_for(page)
        for idx, btn in getattr(self, "_nav_buttons", {}).items():
            name = "navon" if idx == target else "nav"
            if btn.objectName() != name:
                btn.setObjectName(name)
                btn.style().unpolish(btn)
                btn.style().polish(btn)

    def _set_ui_theme(self, code: str) -> None:
        """Oberfläche hell/dunkel live umschalten (gemerkt wie die Brettfarbe)."""
        if code not in UI_THEMES:
            return
        self._ui_theme = code
        self._eval_settings.setValue("ui_theme", code)
        self.setStyleSheet(build_style(UI_THEMES[code]))
        pal = UI_THEMES[code]
        set_ui_palette(pal["muted"], pal["border"], pal["neutral"])
        # Passende Brettfarbe mitnehmen und alle Bretter neu zeichnen.
        board_code = THEME_BOARD.get(code)
        if board_code and board_code in BOARD_THEMES:
            self._board_theme = board_code
            self._eval_settings.setValue("board_theme", board_code)
            set_board_theme(board_code)
            for c, act in getattr(self, "_board_actions", {}).items():
                act.setChecked(c == board_code)
        for bv in self.findChildren(BoardView):
            bv.update()
        for c, act in getattr(self, "_theme_actions", {}).items():
            act.setChecked(c == code)

    def _page_name(self, index: int) -> str:
        """Klartext-Name der Seite (für Kopfzeile + Fenstertitel)."""
        names = {
            0: t("Üben", "Train"),
            1: t("Alle Eröffnungen", "All openings"),
            2: t("Trefferquote & Fehler", "Accuracy & mistakes"),
            3: t("Repertoire-Prüfung", "Repertoire check"),
            4: t("Gegen Stockfish", "Play Stockfish"),
            5: t("Fortschritt", "Progress"),
            6: t("Eröffnungs-Explorer", "Opening explorer"),
            7: t("Partien auswerten", "Review games"),
            8: t("Partie-Betrachter", "Game viewer"),
            9: t("Repertoire-Editor", "Repertoire editor"),
            10: t("Üben", "Train"),
            11: t("Heute fällig", "Due today"),
            12: t("Start", "Home"),
            13: t("Repertoire-Baum", "Repertoire tree"),
        }
        return names.get(index, "")

    def _page_title(self, index: int) -> str:
        """Fenstertitel je Seite, damit oben immer steht, wo man ist."""
        name = self._page_name(index)
        return f"Opening Trainer — {name}" if name else "Opening Trainer"

    def _home_index(self) -> int:
        """»Zuhause« ist der Start-Hub (Verteiler-Seite). Gilt für App-Start UND
        den »Zurück«-Fallback ohne Historie."""
        return 12

    def _go_to(self, target: int) -> None:
        """Zu einer Seite springen, ohne die Historie zu erweitern (für Zurück/Heim)."""
        if target == self.stack.currentIndex():
            if target == 11:
                self._refresh_due_overview()
            elif target == 12:
                self._refresh_home()
            return
        self._nav_suppress = True
        self.stack.setCurrentIndex(target)

    def _go_home(self) -> None:
        self._go_to(self._home_index())

    def _go_back(self) -> None:
        """Zur zuletzt besuchten Seite zurück; ohne Historie nach »Zuhause«."""
        target = self._nav_history.pop() if self._nav_history else self._home_index()
        self._go_to(target)

    def _build_train_page(self) -> QtWidgets.QWidget:
        # Lineares Training entfernt; Seite 0 ist leerer Platzhalter (Indizes
        # unverändert). Training läuft komplett über das Positionsmodell.
        return QtWidgets.QWidget()

    def _build_library_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        outer = QtWidgets.QVBoxLayout(page)
        outer.setContentsMargins(26, 22, 26, 22)
        outer.setSpacing(12)

        header = QtWidgets.QHBoxLayout()
        back = QtWidgets.QPushButton(t("‹  Zurück", "‹  Back"))
        back.setObjectName("more")
        back.clicked.connect(self._go_back)
        title = QtWidgets.QLabel(t("Deine Eröffnungen", "Your openings"))
        title.setObjectName("name")
        self.stats_btn = QtWidgets.QPushButton(self._amp(t("Trefferquote & Fehler", "Accuracy & mistakes")))
        self.stats_btn.setObjectName("more")
        self.stats_btn.clicked.connect(self._open_stats)
        self.load_btn = QtWidgets.QPushButton(t("PGN laden …", "Load PGN …"))
        self.load_btn.clicked.connect(self._load_pgn_dialog)
        self.load_folder_btn = QtWidgets.QPushButton(t("Ordner laden …", "Load folder …"))
        self.load_folder_btn.clicked.connect(self._load_folder_dialog)
        header.addWidget(back, 0, QtCore.Qt.AlignLeft)
        header.addStretch(1)
        header.addWidget(self.stats_btn, 0, QtCore.Qt.AlignRight)
        header.addWidget(self.load_btn, 0, QtCore.Qt.AlignRight)
        header.addWidget(self.load_folder_btn, 0, QtCore.Qt.AlignRight)
        outer.addLayout(header)

        self.lib_title = QtWidgets.QLabel(t("Deine Eröffnungen", "Your openings"))
        self.lib_title.setObjectName("name")
        outer.addWidget(self.lib_title)

        self.lib_sub = QtWidgets.QLabel(t(
            "Klick eine Eröffnung an (markiert sie) — dann unten „Üben“ oder zuordnen. Doppelklick übt sofort.",
            "Click an opening to select it — then ‘Train’ below, or assign it. Double-click trains right away.",
        ))
        self.lib_sub.setObjectName("hint")
        outer.addWidget(self.lib_sub)

        filter_row = QtWidgets.QHBoxLayout()
        self.side_group = QtWidgets.QButtonGroup(self)
        self._side_buttons = {}
        for key, label in [(None, t("Alle", "All")), ("white", t("Weiß", "White")),
                           ("black", t("Schwarz", "Black")), ("none", t("Ohne Zuordnung", "Unassigned"))]:
            btn = QtWidgets.QPushButton(label)
            btn.setObjectName("seg")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _checked=False, k=key: self._set_side_filter(k))
            self.side_group.addButton(btn)
            self._side_buttons[key] = btn
            filter_row.addWidget(btn)
        self._side_buttons[None].setChecked(True)
        filter_row.addStretch(1)
        self.train_side_btn = QtWidgets.QPushButton(t("Repertoire üben", "Train repertoire"))
        self.train_side_btn.setObjectName("primary")
        self.train_side_btn.clicked.connect(self._train_side)
        self.train_side_btn.hide()
        filter_row.addWidget(self.train_side_btn)
        outer.addLayout(filter_row)

        self.search_field = QtWidgets.QLineEdit()
        self.search_field.setObjectName("search")
        self.search_field.setPlaceholderText(t(
            "Suche nach Eröffnung …  (z. B. Sizilianisch, Najdorf, Caro)",
            "Search openings …  (e.g. Sicilian, Najdorf, Caro)",
        ))
        self.search_field.setClearButtonEnabled(True)
        self.search_field.textChanged.connect(self._on_search)
        outer.addWidget(self.search_field)

        self.library_empty = self._empty_state(
            "Noch keine Eröffnungen geladen.\n\nOben rechts »PGN laden …« (oder »Ordner laden …«) — "
            "oder hol dir die Beispiel-Eröffnungen über »Start« (⌘1).",
            "No openings loaded yet.\n\nUse »Load PGN …« (or »Load folder …«) at the top right — "
            "or grab the sample openings from »Home« (⌘1).",
        )
        self.library_empty.setVisible(False)
        outer.addWidget(self.library_empty, 1)

        self.library_list = QtWidgets.QListWidget()
        self.library_list.setObjectName("library")
        self.library_list.setSpacing(2)
        self.library_list.itemActivated.connect(self._train_from_library)  # Doppelklick / Enter
        self.library_list.itemSelectionChanged.connect(self._on_library_selection)
        outer.addWidget(self.library_list, 1)

        action_bar = QtWidgets.QHBoxLayout()
        self.assign_white_btn = QtWidgets.QPushButton(t("→ Weiß-Repertoire", "→ White repertoire"))
        self.assign_white_btn.clicked.connect(lambda: self._assign_selected("white"))
        self.assign_black_btn = QtWidgets.QPushButton(t("→ Schwarz-Repertoire", "→ Black repertoire"))
        self.assign_black_btn.clicked.connect(lambda: self._assign_selected("black"))
        self.assign_none_btn = QtWidgets.QPushButton(t("Zuordnung lösen", "Unassign"))
        self.assign_none_btn.setToolTip(t(
            "Entfernt nur die Weiß/Schwarz-Zuordnung. Die Eröffnung bleibt geladen.",
            "Removes only the White/Black assignment. The opening stays loaded."))
        self.assign_none_btn.clicked.connect(lambda: self._assign_selected("none"))
        self.note_btn = QtWidgets.QPushButton(t("📝 Notiz", "📝 Note"))
        self.note_btn.setToolTip(t(
            "Persönlichen Merktext zu dieser Eröffnung hinterlegen (erscheint 📝 in der Liste).",
            "Add a personal note to this opening (shown as 📝 in the list)."))
        self.note_btn.clicked.connect(self._edit_note_selected)
        self.train_one_btn = QtWidgets.QPushButton(t("Üben", "Train"))
        self.train_one_btn.setObjectName("primary")
        self.train_one_btn.clicked.connect(self._train_selected_library)
        for btn in (self.assign_white_btn, self.assign_black_btn, self.assign_none_btn, self.note_btn, self.train_one_btn):
            btn.setEnabled(False)
        action_bar.addWidget(self.assign_white_btn)
        action_bar.addWidget(self.assign_black_btn)
        action_bar.addWidget(self.assign_none_btn)
        action_bar.addWidget(self.note_btn)
        action_bar.addStretch(1)
        action_bar.addWidget(self.train_one_btn)
        outer.addLayout(action_bar)
        return page

    def _build_stats_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        outer = QtWidgets.QVBoxLayout(page)
        outer.setContentsMargins(26, 22, 26, 22)
        outer.setSpacing(12)

        header = QtWidgets.QHBoxLayout()
        back = QtWidgets.QPushButton(t("‹  Zurück", "‹  Back"))
        back.setObjectName("more")
        back.clicked.connect(self._go_back)
        header.addWidget(back, 0, QtCore.Qt.AlignLeft)
        header.addStretch(1)
        # Navigation zu Fortschritt / Partien / Repertoire-Prüfung steckt jetzt im
        # Menü „Gehe zu" (⌘4/⌘5/⌘6) — keine doppelten Knöpfe mehr hier.
        outer.addLayout(header)

        title = QtWidgets.QLabel(t("Trefferquote & Fehler", "Accuracy & mistakes"))
        title.setObjectName("name")
        outer.addWidget(title)

        self.stats_overview = QtWidgets.QLabel("")
        self.stats_overview.setObjectName("status")
        self.stats_overview.setWordWrap(True)
        outer.addWidget(self.stats_overview)

        self.stats_sub = QtWidgets.QLabel("")
        self.stats_sub.setObjectName("hint")
        self.stats_sub.setWordWrap(True)
        outer.addWidget(self.stats_sub)

        # Alle offenen Fehler am Stück üben (gedeckelt) — statt nur einzeln klicken.
        self.stats_drill_all = QtWidgets.QPushButton(t("▶  Alle üben", "▶  Drill all"))
        self.stats_drill_all.setObjectName("primary")
        self.stats_drill_all.clicked.connect(self._start_weak_session)
        outer.addWidget(self.stats_drill_all, 0, QtCore.Qt.AlignLeft)

        self.stats_empty = self._empty_state(
            "Noch keine Trainingsdaten. Übe ein paar Eröffnungen — hier siehst du dann deinen Stand.",
            "No training data yet. Practice a few openings — your stats will appear here.")
        outer.addWidget(self.stats_empty, 1)

        self.stats_list = QtWidgets.QListWidget()
        self.stats_list.setObjectName("library")
        self.stats_list.setSpacing(2)
        self.stats_list.itemClicked.connect(self._drill_one_from_item)
        outer.addWidget(self.stats_list, 1)
        return page

    # ---- Repertoire-Prüfung (Stockfish) ---------------------------------
    def _build_tuv_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        outer = QtWidgets.QVBoxLayout(page)
        outer.setContentsMargins(26, 22, 26, 22)
        outer.setSpacing(12)

        header = QtWidgets.QHBoxLayout()
        back = QtWidgets.QPushButton(t("‹  Zurück", "‹  Back"))
        back.setObjectName("more")
        back.clicked.connect(self._go_back)
        header.addWidget(back, 0, QtCore.Qt.AlignLeft)
        header.addStretch(1)
        outer.addLayout(header)

        title = QtWidgets.QLabel(t("Repertoire-Prüfung", "Repertoire check"))
        title.setObjectName("name")
        outer.addWidget(title)

        sub = QtWidgets.QLabel(t(
            "Stockfish prüft jede zugeordnete Linie und meldet verdächtige Züge "
            "deiner Seite — damit du dir keine Patzer einprägst. "
            "Klick einen Fund an, um die Linie sofort zu üben.",
            "Stockfish checks every assigned line and flags suspicious moves on "
            "your side — so you don't memorize blunders. "
            "Click a finding to train that line right away.",
        ))
        sub.setObjectName("hint")
        sub.setWordWrap(True)
        outer.addWidget(sub)

        row = QtWidgets.QHBoxLayout()
        self.tuv_start_btn = QtWidgets.QPushButton(t("Prüfung starten", "Start check"))
        self.tuv_start_btn.setObjectName("primary")
        self.tuv_start_btn.clicked.connect(self._start_tuv)
        row.addWidget(self.tuv_start_btn, 0, QtCore.Qt.AlignLeft)
        self.tuv_cancel_btn = QtWidgets.QPushButton(t("Abbrechen", "Cancel"))
        self.tuv_cancel_btn.clicked.connect(self._cancel_tuv)
        self.tuv_cancel_btn.setVisible(False)
        row.addWidget(self.tuv_cancel_btn, 0, QtCore.Qt.AlignLeft)
        row.addStretch(1)
        outer.addLayout(row)

        self.tuv_status = self._plain_label(t("Noch nicht geprüft.", "Not checked yet."))
        self.tuv_status.setObjectName("status")
        self.tuv_status.setWordWrap(True)
        self.tuv_status.setToolTip(t(
            "Bewertungen aus Sicht von Weiß: + bedeutet Vorteil Weiß, − Vorteil Schwarz "
            "(in Bauerneinheiten, z. B. −1.3 = ein Bauer und etwas Schwarz-Vorteil).",
            "Evaluations from White's view: + means White is better, − Black is better "
            "(in pawns, e.g. −1.3 ≈ a pawn-and-a-bit for Black)."))
        outer.addWidget(self.tuv_status)

        self.tuv_list = QtWidgets.QListWidget()
        self.tuv_list.setObjectName("library")
        self.tuv_list.setSpacing(2)
        self.tuv_list.itemClicked.connect(self._train_from_tuv)
        outer.addWidget(self.tuv_list, 1)

        self._tuv_thread = None
        self._tuv_worker = None
        return page

    def _open_tuv(self) -> None:
        self.stack.setCurrentIndex(3)

    def _tuv_jobs(self) -> list:
        # Eine Variante (Wurzel-zu-Blatt-Pfad) pro Job -> die Prüfung deckt auch
        # Nebenvarianten ab, nicht nur lineare Hauptlinien.
        from opening_trainer.tree_session import tree_check_paths
        jobs = []
        for color, side_name in ((chess.WHITE, "white"), (chess.BLACK, "black")):
            for name, moves, tree in tree_check_paths(self.tree_store.by_side(side_name), color):
                jobs.append((_TuvPath(name, moves, tree), color))
        return jobs

    def _start_tuv(self) -> None:
        if self._tuv_thread is not None:
            return
        jobs = self._tuv_jobs()
        if not jobs:
            self.tuv_status.setText(t(
                "Keine zugeordneten Eröffnungen. Ordne erst Eröffnungen einem Repertoire zu.",
                "No assigned openings. First assign some openings to a repertoire.",
            ))
            return
        self.tuv_list.clear()
        self.tuv_start_btn.setEnabled(False)
        self.tuv_cancel_btn.setVisible(True)
        self.tuv_status.setText(t(f"Starte Prüfung von {len(jobs)} Varianten …", f"Checking {len(jobs)} variations …"))

        self._tuv_thread = QtCore.QThread(self)
        self._tuv_worker = _TuvWorker(jobs)
        self._tuv_worker.moveToThread(self._tuv_thread)
        self._tuv_thread.started.connect(self._tuv_worker.run)
        self._tuv_worker.progress.connect(self._on_tuv_progress)
        self._tuv_worker.finished.connect(self._on_tuv_finished)
        self._tuv_worker.failed.connect(self._on_tuv_failed)
        self._tuv_thread.start()

    def _cancel_tuv(self) -> None:
        if self._tuv_worker is not None:
            self._tuv_worker.cancel()
            self.tuv_status.setText(t("Wird abgebrochen …", "Cancelling …"))

    def _on_tuv_progress(self, done: int, total: int, name: str) -> None:
        self.tuv_status.setText(t(f"Prüfe {done}/{total}:  {name}", f"Checking {done}/{total}:  {name}"))

    def _teardown_tuv_thread(self) -> None:
        if self._tuv_thread is not None:
            self._tuv_thread.quit()
            self._tuv_thread.wait()
            self._tuv_thread = None
        self._tuv_worker = None
        self.tuv_start_btn.setEnabled(True)
        self.tuv_cancel_btn.setVisible(False)

    def _on_tuv_failed(self, msg: str) -> None:
        self._teardown_tuv_thread()
        if msg == "nostockfish":
            self.tuv_status.setText(t(
                "Stockfish nicht gefunden. Installiere es einmalig im Terminal mit "
                "»brew install stockfish« — danach läuft die Prüfung.",
                "Stockfish not found. Install it once in the Terminal with "
                "»brew install stockfish« — then the check will run.",
            ))
        else:
            self.tuv_status.setText(t(f"Prüfung fehlgeschlagen: {msg}", f"Check failed: {msg}"))

    def _on_tuv_finished(self, results: list) -> None:
        self._teardown_tuv_thread()
        self.tuv_list.clear()
        total_issues = sum(len(r["issues"]) for r in results)
        if not results:
            self.tuv_status.setText(t(
                "Geprüft — keine Auffälligkeiten. Dein Repertoire ist sauber. ✓",
                "Checked — nothing suspicious. Your repertoire is clean. ✓",
            ))
            return
        patzer = sum(1 for r in results for i in r["issues"] if i.severity == "patzer")
        self.tuv_status.setText(t(
            f"{len(results)} Varianten mit Auffälligkeiten ({total_issues} insgesamt, "
            f"davon {patzer} Patzer). Klick eine Variante zum Üben.",
            f"{len(results)} variations with findings ({total_issues} total, "
            f"{patzer} blunders). Click a variation to train it.",
        ))
        for r in results:
            line = r["line"]
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.UserRole, line)
            row = self._tuv_row(line, r["issues"])
            item.setSizeHint(row.sizeHint())
            self.tuv_list.addItem(item)
            self.tuv_list.setItemWidget(item, row)

    def _tuv_row(self, line, issues: list) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        widget.setObjectName("libraryrow")
        box = QtWidgets.QVBoxLayout(widget)
        box.setContentsMargins(14, 9, 14, 9)
        box.setSpacing(2)
        name = self._plain_label(self._display_name(line))
        name.setObjectName("rowname")
        box.addWidget(name)
        for it in issues:
            mark = (t("⛔ Patzer", "⛔ Blunder") if it.severity == "patzer"
                    else t("⚠ Ungenau", "⚠ Inaccuracy"))
            ev = it.eval_after_cp / 100
            text = t(
                f"{mark} · Zug {it.move_number}: {it.san} — "
                f"besser {it.best_san}  (Stellung danach {ev:+.1f})",
                f"{mark} · move {it.move_number}: {it.san} — "
                f"better {it.best_san}  (eval after {ev:+.1f})",
            )
            lbl = QtWidgets.QLabel(text)
            lbl.setObjectName("rowsub")
            box.addWidget(lbl)
        return widget

    def _train_from_tuv(self, item: QtWidgets.QListWidgetItem) -> None:
        path = item.data(QtCore.Qt.UserRole)
        tree = getattr(path, "tree", None)
        if tree is None or tree.id not in self.tree_store.trees:
            return
        self._start_tree_drill(tree)

    # ---- Sparring (gegen Stockfish weiterspielen) -----------------------
    _SPAR_LEVELS = ["anfaenger", "mittel", "stark"]

    def _spar_level_label(self, key: str) -> str:
        return {
            "anfaenger": t("Anfänger", "Beginner"),
            "mittel": t("Mittel", "Medium"),
            "stark": t("Stark", "Strong"),
        }[key]

    def _build_sparring_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(page)
        layout.setContentsMargins(26, 26, 26, 26)
        layout.setSpacing(30)

        self.spar_board = BoardView(square_size=74)
        self.spar_board.moveRequested.connect(self._sparring_user_move)
        self.spar_eval = EvalBar(height=self.spar_board.board_pixels())
        self._add_board_with_eval(layout, self.spar_board, self.spar_eval)

        side = QtWidgets.QVBoxLayout()
        side.setSpacing(12)
        eyebrow = QtWidgets.QLabel("SPARRING")
        eyebrow.setObjectName("eyebrow")
        title = QtWidgets.QLabel(t("Gegen Stockfish weiterspielen", "Play on against Stockfish"))
        title.setObjectName("name")
        title.setWordWrap(True)
        hint = QtWidgets.QLabel(t(
            "Spiel die Stellung aus deiner Eröffnung gegen Stockfish aus. "
            "Wähl eine Stärke — voller Stockfish wäre unschlagbar.",
            "Play out your opening position against Stockfish. "
            "Pick a strength — full Stockfish would be unbeatable.",
        ))
        hint.setObjectName("hint")
        hint.setWordWrap(True)

        level_row = QtWidgets.QHBoxLayout()
        self._spar_level_buttons = {}
        for key in self._SPAR_LEVELS:
            btn = QtWidgets.QPushButton(self._spar_level_label(key))
            btn.setObjectName("seg")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _=False, k=key: self._set_spar_level(k))
            level_row.addWidget(btn)
            self._spar_level_buttons[key] = btn
        level_row.addStretch(1)

        self.spar_status = QtWidgets.QLabel("")
        self.spar_status.setObjectName("status")
        self.spar_status.setWordWrap(True)
        self.spar_status.setMinimumHeight(48)

        self.spar_undo_btn = QtWidgets.QPushButton(t("‹  Zug zurück", "‹  Take back"))
        self.spar_undo_btn.clicked.connect(self._spar_undo)
        self.spar_undo_btn.setEnabled(False)
        self.spar_reset_btn = QtWidgets.QPushButton(t("Neu ab Eröffnung", "Restart from opening"))
        self.spar_reset_btn.clicked.connect(self._spar_reset)
        back = QtWidgets.QPushButton(t("‹  Zurück", "‹  Back"))
        back.setObjectName("more")
        back.clicked.connect(self._go_back)

        action_row = QtWidgets.QHBoxLayout()
        action_row.addWidget(self.spar_undo_btn)
        action_row.addWidget(self.spar_reset_btn)
        action_row.addStretch(1)

        side.addWidget(eyebrow)
        side.addWidget(title)
        side.addWidget(hint)
        side.addSpacing(6)
        side.addWidget(QtWidgets.QLabel(t("Stärke:", "Strength:")))
        side.addLayout(level_row)
        side.addWidget(self.spar_status)
        side.addStretch(1)
        side.addLayout(action_row)
        side.addWidget(back, 0, QtCore.Qt.AlignLeft)

        side_widget = QtWidgets.QWidget()
        side_widget.setLayout(side)
        side_widget.setFixedWidth(340)
        layout.addWidget(side_widget, 1)
        return page

    def _open_sparring(self) -> None:
        # Auch ohne laufendes Training nutzbar (Menü-Einstieg): dann ab Grundstellung.
        if self.training is not None:
            self._spar_board = self.training.board.copy()
            self._spar_color = (
                self._train_color_for(self.current_line) if self.current_line else chess.WHITE
            )
        else:
            self._spar_board = chess.Board()
            self._spar_color = chess.WHITE
        self.spar_board.train_color = self._spar_color
        self.spar_board.set_flipped(self._spar_color == chess.BLACK)
        self.spar_eval.set_flipped(self._spar_color == chess.BLACK)
        self.spar_eval.clear()
        self.spar_board.set_board(self._spar_board, last_move=None)
        self._spar_thinking = False
        self._spar_prev_eval = None
        self._spar_judge = False
        engine_first = self._spar_board.turn != self._spar_color
        self._spar_floor_plies = len(self._spar_board.move_stack) + (1 if engine_first else 0)
        self._update_spar_level_buttons()
        self.stack.setCurrentIndex(4)
        self._spar_update_status()
        self._update_spar_buttons()
        if engine_first:
            self._spar_engine_move()
        else:
            self._spar_evaluate()   # Leiste + Ausgangsbewertung füllen

    def _set_spar_level(self, level: str) -> None:
        self._spar_level = level
        self._eval_settings.setValue("spar_level", level)
        self._update_spar_level_buttons()

    def _update_spar_level_buttons(self) -> None:
        for key, btn in self._spar_level_buttons.items():
            btn.setChecked(key == self._spar_level)

    def _ensure_spar_worker(self) -> None:
        if self._spar_thread is not None:
            return
        self._spar_thread = QtCore.QThread(self)
        self._spar_worker = _SparringWorker()
        self._spar_worker.moveToThread(self._spar_thread)
        self._sparRequested.connect(self._spar_worker.play)
        self._sparEvalRequested.connect(self._spar_worker.evaluate)
        self._spar_worker.played.connect(self._on_spar_played)
        self._spar_worker.evaluated.connect(self._on_spar_evaluated)
        self._spar_worker.game_over.connect(self._on_spar_game_over)
        self._spar_worker.failed.connect(self._on_spar_failed)
        self._spar_thread.start()

    def _spar_evaluate(self) -> None:
        if self._spar_board is None:
            return
        self._ensure_spar_worker()
        self._sparEvalRequested.emit(self._spar_board.fen())

    def _update_spar_buttons(self) -> None:
        can_undo = (
            self._spar_board is not None
            and not self._spar_thinking
            and len(self._spar_board.move_stack) >= self._spar_floor_plies + 2
        )
        self.spar_undo_btn.setEnabled(can_undo)

    def _spar_engine_move(self) -> None:
        if self._spar_board is None or self._spar_board.is_game_over():
            self._spar_update_status()
            return
        self._ensure_spar_worker()
        self._spar_thinking = True
        self.spar_status.setText(t("Stockfish denkt …", "Stockfish is thinking …"))
        self._update_spar_buttons()
        skill, movetime = sparring_strength(self._spar_level)
        self._sparRequested.emit(self._spar_board.fen(), skill, movetime)

    def _sparring_user_move(self, from_square: int, to_square: int) -> None:
        if self._spar_board is None or self._spar_thinking:
            return
        if self._spar_board.turn != self._spar_color:
            return
        try:
            move = self._spar_board.find_move(from_square, to_square)
        except Exception:  # noqa: BLE001  (ungültiger Zug)
            self.spar_board.flash_wrong(to_square)
            return
        self._spar_board.push(move)
        self.spar_board.set_board(
            self._spar_board, last_move=(move.from_square, move.to_square)
        )
        if self._spar_board.is_game_over():
            self._spar_update_status()
            self._update_spar_buttons()
            return
        self._spar_judge = True   # nächste Antwort beurteilt diesen Zug
        self._spar_engine_move()

    def _on_spar_played(self, req_fen: str, uci: str, e1: int, e2_cp: int, e2_mate: int) -> None:
        if self._spar_board is None or self._spar_board.fen() != req_fen:
            return  # veraltet (Stellung hat sich geändert)
        try:
            move = chess.Move.from_uci(uci)
        except ValueError:
            return
        nudge = (
            self._spar_judge
            and self._spar_prev_eval is not None
            and is_blunder_move(self._spar_prev_eval, e1, self._spar_color == chess.WHITE)
        )
        self._spar_judge = False
        self._spar_board.push(move)
        self._spar_thinking = False
        self.spar_board.set_board(
            self._spar_board, last_move=(move.from_square, move.to_square)
        )
        self.spar_eval.set_eval(e2_cp, e2_mate)
        self._spar_prev_eval = (e2_mate * 10000) if e2_mate else e2_cp
        if self._spar_board.is_game_over():
            self._spar_update_status()
        elif nudge:
            self.spar_status.setText(t(
                "⚠ Das schwächt deine Stellung — »Zug zurück« für einen neuen Versuch.",
                "⚠ That weakens your position — »Take back« for another try.",
            ))
        else:
            self._spar_update_status()
        self._update_spar_buttons()

    def _on_spar_evaluated(self, fen: str, cp: int, mate: int) -> None:
        if self._spar_board is not None and self._spar_board.fen() == fen:
            self.spar_eval.set_eval(cp, mate)
            self._spar_prev_eval = (mate * 10000) if mate else cp

    def _spar_undo(self) -> None:
        if self._spar_board is None or self._spar_thinking:
            return
        if len(self._spar_board.move_stack) < self._spar_floor_plies + 2:
            return
        self._spar_board.pop()   # Stockfishs Antwort
        self._spar_board.pop()   # Achims Zug
        last = None
        if self._spar_board.move_stack:
            m = self._spar_board.move_stack[-1]
            last = (m.from_square, m.to_square)
        self.spar_board.set_board(self._spar_board, last_move=last)
        self.spar_status.setText(t("Zurückgenommen — du bist wieder am Zug.", "Taken back — your move again."))
        self._spar_evaluate()
        self._update_spar_buttons()

    def _on_spar_game_over(self, req_fen: str) -> None:
        self._spar_thinking = False
        self._spar_update_status()
        self._update_spar_buttons()

    def _on_spar_failed(self, msg: str) -> None:
        self._spar_thinking = False
        self._update_spar_buttons()
        if msg == "nostockfish":
            self.spar_status.setText(t(
                "Stockfish nicht gefunden. Installiere es mit »brew install stockfish«.",
                "Stockfish not found. Install it with »brew install stockfish«.",
            ))
        else:
            self.spar_status.setText(t(f"Fehler: {msg}", f"Error: {msg}"))

    def _spar_reset(self) -> None:
        self._open_sparring()

    def _spar_update_status(self) -> None:
        board = self._spar_board
        if board is None:
            return
        if board.is_game_over():
            outcome = board.outcome(claim_draw=True)
            if outcome is None or outcome.winner is None:
                reason = {
                    chess.Termination.STALEMATE: t("Patt", "stalemate"),
                    chess.Termination.INSUFFICIENT_MATERIAL: t("zu wenig Material", "insufficient material"),
                    chess.Termination.FIVEFOLD_REPETITION: t("Stellungswiederholung", "repetition"),
                    chess.Termination.THREEFOLD_REPETITION: t("Stellungswiederholung", "repetition"),
                    chess.Termination.FIFTY_MOVES: t("50-Züge-Regel", "fifty-move rule"),
                    chess.Termination.SEVENTYFIVE_MOVES: t("75-Züge-Regel", "seventy-five-move rule"),
                }.get(getattr(outcome, "termination", None), t("Remis", "draw"))
                self.spar_status.setText(t(
                    f"Remis ({reason}). »Neu ab Eröffnung« für nochmal.",
                    f"Draw ({reason}). »Restart from opening« to try again.",
                ))
            elif outcome.winner == self._spar_color:
                self.spar_status.setText(t("Schachmatt — gewonnen! ✓  Stark gespielt.", "Checkmate — you won! ✓  Well played."))
            else:
                self.spar_status.setText(t(
                    "Schachmatt — verloren. »Neu ab Eröffnung« für nochmal.",
                    "Checkmate — you lost. »Restart from opening« to try again.",
                ))
            return
        if board.turn == self._spar_color:
            check = t("  (Schach!)", "  (Check!)") if board.is_check() else ""
            self.spar_status.setText(t(f"Du bist am Zug.{check}", f"Your move.{check}"))
        else:
            self.spar_status.setText(t("Stockfish denkt …", "Stockfish is thinking …"))

    # ---- Fortschritt (Lernstand je Eröffnung) --------------------------
    def _build_progress_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        outer = QtWidgets.QVBoxLayout(page)
        outer.setContentsMargins(26, 22, 26, 22)
        outer.setSpacing(12)

        header = QtWidgets.QHBoxLayout()
        back = QtWidgets.QPushButton(t("‹  Zurück", "‹  Back"))
        back.setObjectName("more")
        back.clicked.connect(self._go_back)
        header.addWidget(back, 0, QtCore.Qt.AlignLeft)
        header.addStretch(1)
        outer.addLayout(header)

        title = QtWidgets.QLabel(t("Fortschritt", "Progress"))
        title.setObjectName("name")
        outer.addWidget(title)

        sub = QtWidgets.QLabel(t(
            "So steht dein Repertoire: 🟢 sitzt (Trefferquote ≥ 85 %) · "
            "🟡 wackelt · ⚪ noch nie geübt. Klick eine Eröffnung zum Üben.",
            "How your repertoire stands: 🟢 solid (accuracy ≥ 85%) · "
            "🟡 shaky · ⚪ never trained. Click an opening to train it.",
        ))
        sub.setObjectName("hint")
        sub.setWordWrap(True)
        outer.addWidget(sub)

        self.progress_bar = MasteryBar(height=26)
        outer.addWidget(self.progress_bar)

        self.progress_counts = QtWidgets.QLabel("")
        self.progress_counts.setObjectName("status")
        self.progress_counts.setWordWrap(True)
        outer.addWidget(self.progress_counts)

        # Filter: welche Kategorien in der Liste zeigen
        filter_row = QtWidgets.QHBoxLayout()
        filter_row.addWidget(QtWidgets.QLabel(t("Zeigen:", "Show:")))
        self._progress_filter_buttons = {}
        for key, label in [("alle", t("Alle", "All")), ("sitzt", t("🟢 sitzt", "🟢 solid")),
                           ("wackelt", t("🟡 wackelt", "🟡 shaky")), ("neu", t("⚪ neu", "⚪ new"))]:
            btn = QtWidgets.QPushButton(label)
            btn.setObjectName("seg")
            btn.setCheckable(True)
            btn.setChecked(key == self._progress_filter)
            btn.clicked.connect(lambda _=False, k=key: self._set_progress_filter(k))
            filter_row.addWidget(btn)
            self._progress_filter_buttons[key] = btn
        filter_row.addStretch(1)
        outer.addLayout(filter_row)

        self.progress_list = QtWidgets.QListWidget()
        self.progress_list.setObjectName("library")
        self.progress_list.setSpacing(2)
        self.progress_list.itemClicked.connect(self._train_from_progress)
        outer.addWidget(self.progress_list, 1)
        return page

    def _open_progress(self) -> None:
        self._refresh_progress()
        self.stack.setCurrentIndex(5)

    def _refresh_progress(self) -> None:
        # Positions-basiert: pro Eröffnung (Baum) der zugeordneten Seite die
        # aggregierte Statistik über ihre eigenen Stellungen.
        from opening_trainer.tree_session import tree_progress_rows
        self._progress_rows = []
        for color, side_name in ((chess.WHITE, "white"), (chess.BLACK, "black")):
            for r in tree_progress_rows(self.tree_store.by_side(side_name), color, self.stats_store):
                r = dict(r)
                r["bucket"] = mastery_bucket(r["attempts"], r["accuracy"])
                self._progress_rows.append(r)
        assigned = self._progress_rows
        # Ohne zugeordnete Eröffnungen bleibt der Balken ein leerer grauer Streifen.
        self.progress_bar.setVisible(bool(assigned))
        if not assigned:
            self.progress_counts.setText(t(
                "Noch keine Eröffnung einem Repertoire zugeordnet — ordne sie unter "
                "»Alle Eröffnungen« Weiß oder Schwarz zu.",
                "No opening assigned to a repertoire yet — assign them to White or Black "
                "under »All openings«."))
            self._render_progress_list()
            return
        counts = summarize_mastery([(r["attempts"], r["accuracy"]) for r in assigned])
        self.progress_bar.set_counts(counts["sitzt"], counts["wackelt"], counts["neu"])
        self.progress_counts.setText(t(
            f"🟢 {counts['sitzt']} sitzen · 🟡 {counts['wackelt']} wackeln · "
            f"⚪ {counts['neu']} neu   (von {len(assigned)} zugeordneten Eröffnungen)",
            f"🟢 {counts['sitzt']} solid · 🟡 {counts['wackelt']} shaky · "
            f"⚪ {counts['neu']} new   (of {len(assigned)} assigned openings)",
        ))
        self._render_progress_list()

    def _set_progress_filter(self, key: str) -> None:
        self._progress_filter = key
        for k, btn in self._progress_filter_buttons.items():
            btn.setChecked(k == key)
        self._render_progress_list()

    def _render_progress_list(self) -> None:
        self.progress_list.clear()
        rows = getattr(self, "_progress_rows", [])
        if not rows:
            self._add_progress_note(t(
                "Noch keine Eröffnung einem Repertoire zugeordnet.",
                "No opening assigned to a repertoire yet.",
            ))
            return
        f = self._progress_filter
        show_wackelt = f in ("alle", "wackelt")
        show_neu = f in ("alle", "neu")
        show_sitzt = f in ("alle", "sitzt")
        shown = 0
        if show_wackelt:
            for r in sorted((r for r in rows if r["bucket"] == "wackelt"), key=lambda r: r["accuracy"]):
                self._add_progress_row(r["tree"], t(
                    f"🟡 wackelt · Trefferquote {round(r['accuracy'] * 100)} % · "
                    f"{r['positions_trained']}/{r['positions_total']} Stellungen geübt",
                    f"🟡 shaky · accuracy {round(r['accuracy'] * 100)}% · "
                    f"{r['positions_trained']}/{r['positions_total']} positions trained",
                ))
                shown += 1
        if show_neu:
            for r in (r for r in rows if r["bucket"] == "neu"):
                self._add_progress_row(r["tree"], t(
                    f"⚪ neu · noch nie geübt · {r['positions_total']} Stellungen",
                    f"⚪ new · never trained · {r['positions_total']} positions"))
                shown += 1
        if show_sitzt:
            for r in sorted((r for r in rows if r["bucket"] == "sitzt"), key=lambda r: -r["accuracy"]):
                self._add_progress_row(r["tree"], t(
                    f"🟢 sitzt · Trefferquote {round(r['accuracy'] * 100)} % · "
                    f"{r['positions_trained']}/{r['positions_total']} Stellungen geübt",
                    f"🟢 solid · accuracy {round(r['accuracy'] * 100)}% · "
                    f"{r['positions_trained']}/{r['positions_total']} positions trained",
                ))
                shown += 1
        if shown == 0:
            self._add_progress_note(t("Keine Eröffnung in dieser Kategorie.", "No opening in this category."))

    def _add_progress_note(self, text: str) -> None:
        item = QtWidgets.QListWidgetItem()
        item.setFlags(QtCore.Qt.NoItemFlags)
        label = QtWidgets.QLabel(text)
        label.setObjectName("hint")
        label.setContentsMargins(14, 10, 14, 10)
        item.setSizeHint(label.sizeHint())
        self.progress_list.addItem(item)
        self.progress_list.setItemWidget(item, label)

    def _add_progress_row(self, tree, sub_text: str) -> None:
        item = QtWidgets.QListWidgetItem()
        item.setData(QtCore.Qt.UserRole, tree)
        widget = QtWidgets.QWidget()
        widget.setObjectName("libraryrow")
        box = QtWidgets.QVBoxLayout(widget)
        box.setContentsMargins(14, 9, 14, 9)
        box.setSpacing(2)
        name = self._plain_label(self._tname(tree.name))
        name.setObjectName("rowname")
        sub = QtWidgets.QLabel(sub_text)
        sub.setObjectName("rowsub")
        box.addWidget(name)
        box.addWidget(sub)
        item.setSizeHint(widget.sizeHint())
        self.progress_list.addItem(item)
        self.progress_list.setItemWidget(item, widget)

    def _train_from_progress(self, item: QtWidgets.QListWidgetItem) -> None:
        tree = item.data(QtCore.Qt.UserRole)
        if tree is None or tree.id not in self.tree_store.trees:
            return
        self._start_tree_drill(tree)

    # ---- Lichess-Eröffnungsexplorer ------------------------------------
    def _build_explorer_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(page)
        layout.setContentsMargins(26, 26, 26, 26)
        layout.setSpacing(28)

        self.explorer_board = BoardView(square_size=66)
        layout.addWidget(self.explorer_board, 0, QtCore.Qt.AlignTop)

        side = QtWidgets.QVBoxLayout()
        side.setSpacing(10)
        eyebrow = QtWidgets.QLabel("LICHESS-EXPLORER")
        eyebrow.setObjectName("eyebrow")
        self.explorer_opening = self._plain_label("—")
        self.explorer_opening.setObjectName("name")
        self.explorer_opening.setWordWrap(True)
        hint = QtWidgets.QLabel(t(
            "Was in echten Partien gespielt wird. Klick einen Zug, um weiterzugehen.",
            "What is played in real games. Click a move to go deeper.",
        ))
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        self.explorer_status = QtWidgets.QLabel("")
        self.explorer_status.setObjectName("status")
        self.explorer_status.setWordWrap(True)

        self.explorer_list = QtWidgets.QListWidget()
        self.explorer_list.setObjectName("library")
        self.explorer_list.setSpacing(2)
        self.explorer_list.itemClicked.connect(self._explorer_play)

        nav = QtWidgets.QHBoxLayout()
        self.explorer_undo_btn = QtWidgets.QPushButton(t("‹  Zug zurück", "‹  Take back"))
        self.explorer_undo_btn.clicked.connect(self._explorer_undo)
        reset = QtWidgets.QPushButton(t("Neu ab Grundstellung", "Restart from move 1"))
        reset.clicked.connect(self._explorer_reset)
        token_btn = QtWidgets.QPushButton(t("🔑 Lichess-Token", "🔑 Lichess token"))
        token_btn.setObjectName("more")
        token_btn.clicked.connect(self._edit_lichess_token)
        nav.addWidget(self.explorer_undo_btn)
        nav.addWidget(reset)
        nav.addStretch(1)
        nav.addWidget(token_btn)

        back = QtWidgets.QPushButton(t("‹  Zurück", "‹  Back"))
        back.setObjectName("more")
        back.clicked.connect(self._go_back)

        side.addWidget(eyebrow)
        side.addWidget(self.explorer_opening)
        side.addWidget(hint)
        side.addWidget(self.explorer_status)
        side.addWidget(self.explorer_list, 1)
        side.addLayout(nav)
        side.addWidget(back, 0, QtCore.Qt.AlignLeft)
        layout.addLayout(side, 1)
        return page

    def _open_explorer(self) -> None:
        # Auch ohne laufendes Training nutzbar (Menü-Einstieg): dann ab Grundstellung.
        self._explorer_board = self.training.board.copy() if self.training is not None else chess.Board()
        self._explorer_seed_plies = len(self._explorer_board.move_stack)
        color = self._train_color_for(self.current_line) if self.current_line else chess.WHITE
        self.explorer_board.set_flipped(color == chess.BLACK)
        self.explorer_board.set_board(self._explorer_board, last_move=None)
        self.stack.setCurrentIndex(6)
        self._explorer_update_nav()
        self._explorer_fetch(self._explorer_board.fen())

    # Direktlink zur Lichess-Token-Erstellung: Beschreibung vorausgefüllt, KEINE
    # Berechtigungen (scopes leer) → der Token kann nichts im Namen des Nutzers
    # tun, dient nur zur Identifikation beim Explorer-Abruf.
    _LICHESS_TOKEN_URL = (
        "https://lichess.org/account/oauth/token/create?description=Opening+Trainer"
    )

    def _edit_lichess_token(self) -> None:
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle(t("Lichess-Token", "Lichess token"))
        lay = QtWidgets.QVBoxLayout(dlg)

        info = QtWidgets.QLabel(t(
            "Der Lichess-Explorer braucht einen kostenlosen API-Token "
            "(beginnt mit »lip_…«). Er wird nur lokal gespeichert.\n\n"
            "1. Unten auf »Token bei Lichess erstellen« klicken — die Seite öffnet "
            "sich im Browser, schon richtig vorausgefüllt (keine Berechtigungen "
            "nötig). Dort einfach auf »Create« klicken.\n"
            "2. Den angezeigten Token kopieren.\n"
            "3. Hier unten einfügen und auf OK klicken.",
            "The Lichess explorer needs a free API token (starts with “lip_…”). "
            "It is stored only locally.\n\n"
            "1. Click “Create token on Lichess” below — the page opens in your "
            "browser, already filled in correctly (no permissions needed). Just "
            "click “Create” there.\n"
            "2. Copy the token it shows you.\n"
            "3. Paste it below and click OK.",
        ))
        info.setWordWrap(True)
        lay.addWidget(info)

        create_btn = QtWidgets.QPushButton(
            t("🔗  Token bei Lichess erstellen", "🔗  Create token on Lichess")
        )
        create_btn.clicked.connect(
            lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(self._LICHESS_TOKEN_URL))
        )
        lay.addWidget(create_btn)

        field = QtWidgets.QLineEdit(self._lichess_token)
        field.setPlaceholderText("lip_…")
        lay.addWidget(field)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        lay.addWidget(buttons)
        field.setFocus()

        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        self._lichess_token = field.text().strip()
        self._eval_settings.setValue("lichess_token", self._lichess_token)
        self._explorer_cache.clear()
        if self._explorer_board is not None:
            self._explorer_fetch(self._explorer_board.fen())

    def _explorer_nam_instance(self):
        if self._explorer_nam is None:
            self._explorer_nam = QtNetwork.QNetworkAccessManager(self)
            self._explorer_nam.finished.connect(self._on_explorer_reply)
        return self._explorer_nam

    def _explorer_fetch(self, fen: str) -> None:
        cached = self._explorer_cache.get(fen)
        if cached is not None:
            self._render_explorer(fen, cached)
            return
        if not QtNetwork.QSslSocket.supportsSsl():
            self.explorer_status.setText(t(
                "TLS/SSL ist in dieser App nicht verfügbar — der Explorer kann "
                "Lichess nicht sicher erreichen. (Verschlüsselungs-Backend fehlt.)",
                "TLS/SSL is not available in this app — the explorer can't reach "
                "Lichess securely. (Encryption backend missing.)",
            ))
            self.explorer_list.clear()
            return
        self.explorer_status.setText(t("Lädt von Lichess …", "Loading from Lichess …"))
        self.explorer_list.clear()
        url = QtCore.QUrl("https://explorer.lichess.ovh/lichess")
        q = QtCore.QUrlQuery()
        q.addQueryItem("fen", fen)
        q.addQueryItem("moves", "12")
        q.addQueryItem("topGames", "0")
        q.addQueryItem("recentGames", "0")
        url.setQuery(q)
        req = QtNetwork.QNetworkRequest(url)
        req.setRawHeader(b"User-Agent", b"OpeningTrainer/1.0 (personal use)")
        req.setAttribute(QtNetwork.QNetworkRequest.Attribute.Http2AllowedAttribute, False)
        if self._lichess_token:
            req.setRawHeader(b"Authorization", b"Bearer " + self._lichess_token.encode("ascii", "ignore"))
        reply = self._explorer_nam_instance().get(req)
        reply.setProperty("fen", fen)

    def _on_explorer_reply(self, reply) -> None:
        fen = reply.property("fen")
        err = reply.error()
        err_text = reply.errorString()
        http = reply.attribute(QtNetwork.QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        raw = bytes(reply.readAll().data())
        reply.deleteLater()
        current = self._explorer_board.fen() if self._explorer_board is not None else None
        if err != QtNetwork.QNetworkReply.NetworkError.NoError:
            if fen == current:
                if http == 401:
                    if self._lichess_token:
                        self.explorer_status.setText(t(
                            "Lichess hat den Token abgelehnt — stimmt er noch? "
                            "Über »🔑 Lichess-Token« neu eintragen.",
                            "Lichess rejected the token — is it still valid? "
                            "Re-enter it via »🔑 Lichess token«.",
                        ))
                    else:
                        self.explorer_status.setText(t(
                            "Lichess verlangt einen (kostenlosen) Token. "
                            "Klick »🔑 Lichess-Token« und trag deinen lip_…-Token ein.",
                            "Lichess requires a (free) token. "
                            "Click »🔑 Lichess token« and enter your lip_… token.",
                        ))
                else:
                    detail = f"{err_text}" + (f" (HTTP {http})" if http else f" [{int(err)}]")
                    self.explorer_status.setText(t(f"Lichess nicht erreichbar: {detail}", f"Lichess not reachable: {detail}"))
            return
        try:
            result = parse_explorer_response(json.loads(raw.decode("utf-8")))
        except Exception:  # noqa: BLE001
            if fen == current:
                self.explorer_status.setText(t("Antwort von Lichess unlesbar.", "Lichess response unreadable."))
            return
        self._explorer_cache[fen] = result
        if fen == current:
            self._render_explorer(fen, result)

    def _render_explorer(self, fen: str, result) -> None:
        self.explorer_list.clear()
        self.explorer_opening.setText(result.opening_name or t("Eröffnungs-Explorer", "Opening explorer"))
        total = result.total
        if total <= 0:
            self.explorer_status.setText(t(
                "Keine Partien zu dieser Stellung in der Lichess-Datenbank.",
                "No games for this position in the Lichess database.",
            ))
            self._explorer_update_nav()
            return
        games = f"{total:,}".replace(",", ".")
        self.explorer_status.setText(t(
            f"{games} Partien · Weiß {percent(result.white, total)} % · "
            f"Remis {percent(result.draws, total)} % · Schwarz {percent(result.black, total)} %",
            f"{games} games · White {percent(result.white, total)}% · "
            f"Draw {percent(result.draws, total)}% · Black {percent(result.black, total)}%",
        ))
        for m in result.moves:
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.UserRole, m.uci)
            row = self._explorer_row(m, total)
            item.setSizeHint(row.sizeHint())
            self.explorer_list.addItem(item)
            self.explorer_list.setItemWidget(item, row)
        self._explorer_update_nav()

    def _explorer_row(self, move, position_total: int) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        widget.setObjectName("libraryrow")
        box = QtWidgets.QHBoxLayout(widget)
        box.setContentsMargins(12, 7, 12, 7)
        box.setSpacing(10)
        san = QtWidgets.QLabel(move.san)
        san.setObjectName("rowname")
        san.setFixedWidth(64)
        share = QtWidgets.QLabel(
            f"{percent(move.total, position_total)} %  ·  "
            + t(f"{f'{move.total:,}'.replace(',', '.')} Partien", f"{move.total:,} games")
        )
        share.setObjectName("rowsub")
        bar = WdlBar(width=160, height=16)
        bar.set_wdl(move.white, move.draws, move.black)
        box.addWidget(san)
        box.addWidget(share, 1)
        box.addWidget(bar)
        return widget

    def _explorer_play(self, item: QtWidgets.QListWidgetItem) -> None:
        uci = item.data(QtCore.Qt.UserRole)
        if not uci or self._explorer_board is None:
            return
        try:
            move = chess.Move.from_uci(uci)
        except ValueError:
            return
        if move not in self._explorer_board.legal_moves:
            return
        self._explorer_board.push(move)
        self.explorer_board.set_board(
            self._explorer_board, last_move=(move.from_square, move.to_square)
        )
        self._explorer_update_nav()
        self._explorer_fetch(self._explorer_board.fen())

    def _explorer_reset(self) -> None:
        """Zurück auf die Grundstellung (Zug 1) — frei vom Trainings-Kontext, damit
        »Neu ab Eröffnung« aus jeder Stellung verlässlich zum Anfang führt."""
        self._explorer_board = chess.Board()
        self._explorer_seed_plies = 0
        self.explorer_board.set_board(self._explorer_board, last_move=None)
        self._explorer_update_nav()
        self._explorer_fetch(self._explorer_board.fen())

    def _explorer_undo(self) -> None:
        if self._explorer_board is None or not self._explorer_board.move_stack:
            return
        self._explorer_board.pop()
        last = None
        if self._explorer_board.move_stack:
            m = self._explorer_board.move_stack[-1]
            last = (m.from_square, m.to_square)
        self.explorer_board.set_board(self._explorer_board, last_move=last)
        self._explorer_update_nav()
        self._explorer_fetch(self._explorer_board.fen())

    def _explorer_update_nav(self) -> None:
        can_undo = (
            self._explorer_board is not None
            and len(self._explorer_board.move_stack) > 0
        )
        self.explorer_undo_btn.setEnabled(can_undo)

    # ---- Echte Partien auswerten (Repertoire-Abgleich) -----------------
    def _build_game_review_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        outer = QtWidgets.QVBoxLayout(page)
        outer.setContentsMargins(26, 22, 26, 22)
        outer.setSpacing(12)

        header = QtWidgets.QHBoxLayout()
        back = QtWidgets.QPushButton(t("‹  Zurück", "‹  Back"))
        back.setObjectName("more")
        back.clicked.connect(self._go_back)
        header.addWidget(back, 0, QtCore.Qt.AlignLeft)
        header.addStretch(1)
        outer.addLayout(header)

        title = QtWidgets.QLabel(t("Partien auswerten", "Review games"))
        title.setObjectName("name")
        outer.addWidget(title)

        hint = QtWidgets.QLabel(t(
            "Lade eine PGN-Datei deiner gespielten Partien (Lichess: Profil → "
            "»Partien exportieren«; chess.com: Archiv-Download). Die App zeigt pro "
            "Partie, wo du von deinem Repertoire abgewichen bist. Klick eine "
            "Abweichung, um die richtige Linie zu üben.",
            "Load a PGN file of your played games (Lichess: profile → "
            "»Export games«; chess.com: archive download). For each game the app "
            "shows where you left your repertoire. Click a deviation to train the "
            "right line.",
        ))
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        outer.addWidget(hint)

        row = QtWidgets.QHBoxLayout()
        self.games_name_btn = QtWidgets.QPushButton("")
        self.games_name_btn.setObjectName("more")
        self.games_name_btn.clicked.connect(self._set_player_name)
        load_btn = QtWidgets.QPushButton(t("Partien laden …", "Load games …"))
        load_btn.setObjectName("primary")
        load_btn.clicked.connect(self._load_games_dialog)
        row.addWidget(self.games_name_btn, 0, QtCore.Qt.AlignLeft)
        row.addWidget(load_btn, 0, QtCore.Qt.AlignLeft)
        row.addStretch(1)
        outer.addLayout(row)

        self.games_status = QtWidgets.QLabel("")
        self.games_status.setObjectName("status")
        self.games_status.setWordWrap(True)
        outer.addWidget(self.games_status)

        self.games_list = QtWidgets.QListWidget()
        self.games_list.setObjectName("library")
        self.games_list.setSpacing(2)
        self.games_list.itemClicked.connect(self._train_from_game_review)
        outer.addWidget(self.games_list, 1)
        return page

    def _open_game_review(self) -> None:
        self._update_games_name_btn()
        if self.games_list.count() == 0 and self._player_name.strip():
            path = self._eval_settings.value("games_pgn_path", "", type=str)
            if path and Path(path).exists():
                self._load_games_from_path(path, interactive=False)
        # Ohne zugeordnetes Repertoire ist der Abgleich sinnlos (alles „ungedeckt") ->
        # actionable Hinweis statt irreführender Zähler. Zuletzt setzen, damit das
        # Auto-Laden ihn nicht überschreibt.
        if not (self.tree_store.by_side("white") or self.tree_store.by_side("black")):
            self.games_status.setText(t(
                "Tipp: Ordne zuerst Eröffnungen einem Repertoire zu (Weiß/Schwarz, unter "
                "»Alle Eröffnungen«) — sonst kann ich deine Partien nicht mit deinem "
                "Repertoire abgleichen.",
                "Tip: assign some openings to a repertoire (White/Black, under »All openings«) "
                "first — otherwise I can't compare your games against your repertoire."))
        self.stack.setCurrentIndex(7)

    def _update_games_name_btn(self) -> None:
        name = self._player_name.strip()
        self.games_name_btn.setText(
            t(f"Spielername: {name}", f"Player name: {name}") if name
            else t("Spielername eintragen …", "Enter player name …")
        )

    def _set_player_name(self) -> None:
        text, ok = QtWidgets.QInputDialog.getText(
            self,
            t("Spielername", "Player name"),
            t(
                "Dein Benutzername (Lichess/chess.com), damit die App pro Partie weiß,\n"
                "welche Farbe du gespielt hast:",
                "Your username (Lichess/chess.com), so the app knows which colour\n"
                "you played in each game:",
            ),
            QtWidgets.QLineEdit.EchoMode.Normal,
            self._player_name,
        )
        if not ok:
            return
        self._player_name = text.strip()
        self._eval_settings.setValue("player_name", self._player_name)
        self._update_games_name_btn()

    def _load_games_dialog(self) -> None:
        if not self._player_name.strip():
            self.games_status.setText(t("Bitte zuerst deinen Spielernamen eintragen.", "Please enter your player name first."))
            return
        # Dialog im Ordner der zuletzt benutzten Datei öffnen (dort liegen die PGNs).
        saved = self._eval_settings.value("games_pgn_path", "", type=str)
        start_dir = str(Path(saved).parent) if saved else ""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, t("PGN deiner Partien laden", "Load your games PGN"), start_dir,
            t("PGN-Dateien (*.pgn);;Alle Dateien (*)", "PGN files (*.pgn);;All files (*)")
        )
        if not path:
            return
        self._eval_settings.setValue("games_pgn_path", path)
        self._load_games_from_path(path)

    def _load_games_from_path(self, path: str, interactive: bool = True) -> None:
        if not self._player_name.strip() or not Path(path).exists():
            return
        # Varianten-bewusstes Buch aus den Repertoire-Bäumen: eine korrekt
        # gespielte Nebenvariante gilt nicht mehr als Abweichung.
        white_book = build_san_book(self.tree_store.by_side("white"), chess.WHITE)
        black_book = build_san_book(self.tree_store.by_side("black"), chess.BLACK)
        uname = self._player_name.strip().lower()
        results = []
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                while True:
                    game = chess.pgn.read_game(fh)
                    if game is None:
                        break
                    results.append(self._review_one_game(game, uname, white_book, black_book))
        except PermissionError:
            # macOS blockt geschützte Ordner (Downloads/Schreibtisch/Dokumente). Beim
            # automatischen Nachladen still bleiben; bei manueller Auswahl erklären.
            if interactive:
                self.games_status.setText(t(
                    "macOS hat den Zugriff auf diese Datei verweigert (geschützter Ordner "
                    "wie Downloads/Schreibtisch/Dokumente). Erlaube »Opening Trainer« den "
                    "Zugriff unter Systemeinstellungen → Datenschutz & Sicherheit → "
                    "»Festplattenvollzugriff« — oder verschiebe die PGN in einen anderen Ordner.",
                    "macOS denied access to this file (a protected folder such as Downloads/"
                    "Desktop/Documents). Allow »Opening Trainer« access under System Settings "
                    "→ Privacy & Security → »Full Disk Access« — or move the PGN to another folder."))
            return
        except Exception as exc:  # noqa: BLE001
            self.games_status.setText(t(f"Konnte die PGN nicht lesen: {exc}", f"Could not read the PGN: {exc}"))
            return
        self._render_game_reviews(results)

    def _review_one_game(self, game, uname: str, white_book, black_book) -> dict:
        white = (game.headers.get("White", "") or "").strip()
        black = (game.headers.get("Black", "") or "").strip()
        result = game.headers.get("Result", "") or ""
        if white.lower() == uname:
            color, book, opp = chess.WHITE, white_book, (black or "?")
        elif black.lower() == uname:
            color, book, opp = chess.BLACK, black_book, (white or "?")
        else:
            return {"status": "unknown"}
        moves = [m.uci() for m in game.mainline_moves()]
        review = review_game(moves, book, color)
        return {
            "status": review.status, "review": review, "opp": opp, "result": result,
            "moves": moves, "color": color,
        }

    def _render_game_reviews(self, results: list) -> None:
        self.games_list.clear()
        recognized = [r for r in results if r["status"] != "unknown"]
        unknown = len(results) - len(recognized)
        dev = [r for r in recognized if r["status"] == "deviated"]
        oob = [r for r in recognized if r["status"] == "out_of_book"]
        fol = [r for r in recognized if r["status"] == "followed"]
        if not recognized:
            extra = (t(f" ({unknown} Partien ohne Namenstreffer)", f" ({unknown} games with no name match)")
                     if unknown else "")
            self.games_status.setText(t(
                f"Keine Partie mit »{self._player_name}« gefunden{extra}. "
                "Stimmt der Spielername genau?",
                f"No game found for »{self._player_name}«{extra}. "
                "Is the player name exactly right?",
            ))
            return
        parts = [
            t(f"{len(recognized)} Partien als {self._player_name}", f"{len(recognized)} games as {self._player_name}"),
            t(f"⚠ {len(dev)} abgewichen", f"⚠ {len(dev)} deviated"),
            t(f"○ {len(oob)} Eröffnung ungedeckt", f"○ {len(oob)} opening uncovered"),
            t(f"✓ {len(fol)} gefolgt", f"✓ {len(fol)} followed"),
        ]
        if unknown:
            parts.append(t(f"{unknown} übersprungen", f"{unknown} skipped"))
        self.games_status.setText("   ·   ".join(parts))

        for r in dev:
            d = r["review"].deviation
            expected = ", ".join(d.expected_sans)
            self._add_game_row(
                self._game_row_title(r),
                t(
                    f"⚠ Abgewichen bei Zug {d.move_number}: du spieltest {d.played_san} — "
                    f"Repertoire: {expected}   · klick zum Ansehen",
                    f"⚠ Deviated at move {d.move_number}: you played {d.played_san} — "
                    f"repertoire: {expected}   · click to view",
                ),
                r,
            )
        for r in oob:
            self._add_game_row(
                self._game_row_title(r),
                t(
                    "○ Eröffnung (noch) nicht in deinem Repertoire   · klick zum Ansehen",
                    "○ Opening not (yet) in your repertoire   · click to view",
                ),
                r,
            )
        for r in fol:
            booked = r["review"].booked_plies
            self._add_game_row(
                self._game_row_title(r),
                t(
                    f"✓ Repertoire gefolgt ({booked} eigene Züge)   · klick zum Ansehen",
                    f"✓ Followed repertoire ({booked} of your moves)   · click to view",
                ),
                r,
            )

    def _game_row_title(self, r: dict) -> str:
        cw = self._tcolor(r.get("color"))
        return t(f"Als {cw} gegen {r['opp']}   ({r['result']})", f"As {cw} against {r['opp']}   ({r['result']})")

    def _add_game_row(self, title: str, sub_text: str, result: dict) -> None:
        item = QtWidgets.QListWidgetItem()
        item.setData(QtCore.Qt.UserRole, result)
        widget = QtWidgets.QWidget()
        widget.setObjectName("libraryrow")
        box = QtWidgets.QVBoxLayout(widget)
        box.setContentsMargins(14, 9, 14, 9)
        box.setSpacing(2)
        name = self._plain_label(title)
        name.setObjectName("rowname")
        sub = QtWidgets.QLabel(sub_text)
        sub.setObjectName("rowsub")
        box.addWidget(name)
        box.addWidget(sub)
        item.setSizeHint(widget.sizeHint())
        self.games_list.addItem(item)
        self.games_list.setItemWidget(item, widget)

    def _train_from_game_review(self, item: QtWidgets.QListWidgetItem) -> None:
        result = item.data(QtCore.Qt.UserRole)
        if isinstance(result, dict) and result.get("moves"):
            self._open_game_viewer(result)

    # ---- Partie-Betrachter (gespielte Partie durchblättern) ------------
    def _build_game_viewer_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(page)
        layout.setContentsMargins(26, 26, 26, 26)
        layout.setSpacing(28)

        self.viewer_board = BoardView(square_size=70)
        layout.addWidget(self.viewer_board, 0, QtCore.Qt.AlignTop)

        side = QtWidgets.QVBoxLayout()
        side.setSpacing(10)
        eyebrow = QtWidgets.QLabel(t("PARTIE ANSEHEN", "VIEW GAME"))
        eyebrow.setObjectName("eyebrow")
        self.viewer_title = self._plain_label("—")
        self.viewer_title.setObjectName("name")
        self.viewer_title.setWordWrap(True)
        self.viewer_status = QtWidgets.QLabel("")
        self.viewer_status.setObjectName("status")
        self.viewer_status.setWordWrap(True)
        self.viewer_status.setMinimumHeight(72)
        self.viewer_status.setToolTip(t(
            "Bewertungen aus Sicht von Weiß: + bedeutet Vorteil Weiß, − Vorteil Schwarz "
            "(in Bauerneinheiten).",
            "Evaluations from White's view: + means White is better, − Black is better "
            "(in pawns)."))

        step = QtWidgets.QHBoxLayout()
        self.viewer_prev_btn = QtWidgets.QPushButton(t("‹ Zurück", "‹ Back"))
        self.viewer_prev_btn.clicked.connect(self._viewer_prev)
        self.viewer_next_btn = QtWidgets.QPushButton(t("Weiter ›", "Next ›"))
        self.viewer_next_btn.clicked.connect(self._viewer_next)
        step.addWidget(self.viewer_prev_btn)
        step.addWidget(self.viewer_next_btn)
        step.addStretch(1)

        self.viewer_analyze_btn = QtWidgets.QPushButton(t("🔍 Mit Stockfish prüfen", "🔍 Check with Stockfish"))
        self.viewer_analyze_btn.clicked.connect(self._viewer_analyze)
        self.viewer_blunder_btn = QtWidgets.QPushButton(t("⛔ nächster Patzer", "⛔ next blunder"))
        self.viewer_blunder_btn.setObjectName("more")
        self.viewer_blunder_btn.clicked.connect(self._viewer_next_blunder)
        self.viewer_blunder_btn.setVisible(False)

        self.viewer_train_btn = QtWidgets.QPushButton(t("Diese Stellung üben", "Drill this position"))
        self.viewer_train_btn.setObjectName("primary")
        self.viewer_train_btn.clicked.connect(self._viewer_train)

        back = QtWidgets.QPushButton(t("‹  Zurück zu den Partien", "‹  Back to games"))
        back.setObjectName("more")
        back.clicked.connect(lambda: self.stack.setCurrentIndex(7))

        side.addWidget(eyebrow)
        side.addWidget(self.viewer_title)
        side.addWidget(self.viewer_status)
        side.addLayout(step)
        side.addWidget(self.viewer_analyze_btn, 0, QtCore.Qt.AlignLeft)
        side.addWidget(self.viewer_blunder_btn, 0, QtCore.Qt.AlignLeft)
        side.addWidget(self.viewer_train_btn, 0, QtCore.Qt.AlignLeft)
        side.addStretch(1)
        side.addWidget(back, 0, QtCore.Qt.AlignLeft)
        side_widget = QtWidgets.QWidget()
        side_widget.setLayout(side)
        side_widget.setFixedWidth(360)
        layout.addWidget(side_widget, 1)
        return page

    def _open_game_viewer(self, payload: dict) -> None:
        self._viewer_moves = payload.get("moves", [])
        self._viewer_color = payload.get("color", chess.WHITE)
        review = payload.get("review")
        self._viewer_dev = review.deviation if (review and review.status == "deviated") else None
        # „Diese Stellung üben" nur, wenn die Abweichungs-Stellung im Repertoire
        # liegt -> dann lenkt der Knopf auf den Baum-Drill dieser Stellung.
        self._viewer_drill_fen = self._deviation_fen() if self._viewer_dev else None
        self.viewer_board.set_flipped(self._viewer_color == chess.BLACK)
        color_word = self._tcolor(self._viewer_color)
        me = self._player_name.strip() or t("Du", "You")
        self.viewer_title.setText(t(
            f"{me} ({color_word})  gegen  {payload.get('opp', '?')}     ·     {payload.get('result', '')}",
            f"{me} ({color_word})  against  {payload.get('opp', '?')}     ·     {payload.get('result', '')}",
        ))
        self.viewer_train_btn.setVisible(
            self._viewer_drill_fen is not None and self._locate_in_trees(self._viewer_drill_fen) is not None)
        self._viewer_issues = {}
        self.viewer_blunder_btn.setVisible(False)
        self.viewer_analyze_btn.setEnabled(True)
        self.viewer_analyze_btn.setVisible(True)
        # Startpunkt: an der Abweichung (Stellung davor), sonst Anfang
        self._viewer_pos = self._viewer_dev.ply if self._viewer_dev else 0
        self.stack.setCurrentIndex(8)
        self._viewer_render()

    def _viewer_render(self) -> None:
        board = chess.Board()
        last = None
        for i in range(self._viewer_pos):
            try:
                mv = chess.Move.from_uci(self._viewer_moves[i])
            except (ValueError, IndexError):
                break
            if i == self._viewer_pos - 1:
                last = (mv.from_square, mv.to_square)
            board.push(mv)
        self.viewer_board.set_board(board, last_move=last)
        n = len(self._viewer_moves)
        self.viewer_prev_btn.setEnabled(self._viewer_pos > 0)
        self.viewer_next_btn.setEnabled(self._viewer_pos < n)
        dev = self._viewer_dev
        issue = self._viewer_issues.get(self._viewer_pos - 1)
        if issue is not None:
            mark = t("⛔ Patzer", "⛔ Blunder") if issue.severity == "patzer" else t("⚠ Ungenau", "⚠ Inaccuracy")
            ev = issue.eval_after_cp / 100
            self.viewer_status.setText(t(
                f"{mark} · Zug {issue.move_number}: du spieltest {issue.san} — "
                f"besser {issue.best_san} (−{issue.loss_cp / 100:.1f}, Stellung danach {ev:+.1f}).",
                f"{mark} · move {issue.move_number}: you played {issue.san} — "
                f"better {issue.best_san} (−{issue.loss_cp / 100:.1f}, eval after {ev:+.1f}).",
            ))
        elif dev is not None and self._viewer_pos == dev.ply:
            self.viewer_status.setText(t(
                f"⚠ Hier bist du abgewichen (Zug {dev.move_number}).\n"
                f"Dein Repertoire: {', '.join(dev.expected_sans)} — "
                f"gespielt hast du: {dev.played_san}.\n"
                "»Weiter« zeigt deinen tatsächlichen Zug.",
                f"⚠ This is where you deviated (move {dev.move_number}).\n"
                f"Your repertoire: {', '.join(dev.expected_sans)} — "
                f"you played: {dev.played_san}.\n"
                "»Next« shows the move you actually played.",
            ))
        elif self._viewer_pos == 0:
            self.viewer_status.setText(t(
                "Startstellung. Mit »Weiter« durch die Partie blättern.",
                "Starting position. Use »Next« to step through the game.",
            ))
        else:
            self.viewer_status.setText(t(f"Halbzug {self._viewer_pos} von {n}.", f"Half-move {self._viewer_pos} of {n}."))

    def _viewer_prev(self) -> None:
        if self._viewer_pos > 0:
            self._viewer_pos -= 1
            self._viewer_render()

    def _viewer_next(self) -> None:
        if self._viewer_pos < len(self._viewer_moves):
            self._viewer_pos += 1
            self._viewer_render()

    def _deviation_fen(self) -> str | None:
        """FEN der Stellung, in der der Nutzer in dieser Partie abgewichen ist
        (die Stellung VOR seinem abweichenden Zug)."""
        dev = self._viewer_dev
        if dev is None:
            return None
        board = chess.Board()
        for i in range(dev.ply):
            try:
                board.push(chess.Move.from_uci(self._viewer_moves[i]))
            except (ValueError, IndexError):
                return None
        return board.fen()

    def _viewer_train(self) -> None:
        if self._viewer_drill_fen is not None:
            self._drill_positions_for_fens(
                [self._viewer_drill_fen], t("STELLUNG ÜBEN", "DRILL POSITION"))

    def _viewer_analyze(self) -> None:
        if self._viewer_anal_thread is not None or not self._viewer_moves:
            return
        self.viewer_analyze_btn.setEnabled(False)
        self.viewer_status.setText(t(
            "Stockfish prüft deine Züge dieser Partie …",
            "Stockfish is checking your moves in this game …",
        ))
        self._viewer_anal_thread = QtCore.QThread(self)
        self._viewer_anal_worker = _GameAnalysisWorker(list(self._viewer_moves), self._viewer_color)
        self._viewer_anal_worker.moveToThread(self._viewer_anal_thread)
        self._viewer_anal_thread.started.connect(self._viewer_anal_worker.run)
        self._viewer_anal_worker.done.connect(self._on_viewer_analysis)
        self._viewer_anal_worker.failed.connect(self._on_viewer_analysis_failed)
        self._viewer_anal_thread.start()

    def _teardown_viewer_analysis(self) -> None:
        if self._viewer_anal_thread is not None:
            self._viewer_anal_thread.quit()
            self._viewer_anal_thread.wait(2000)
            self._viewer_anal_thread = None
        self._viewer_anal_worker = None

    def _on_viewer_analysis(self, issues: list) -> None:
        self._teardown_viewer_analysis()
        self._viewer_issues = {it.ply: it for it in issues}
        self.viewer_analyze_btn.setVisible(False)
        patzer = sum(1 for it in issues if it.severity == "patzer")
        ungenau = len(issues) - patzer
        if not issues:
            self.viewer_status.setText(t(
                "Stockfish: keine Patzer in deinen Zügen — sauber gespielt! ✓",
                "Stockfish: no blunders in your moves — clean game! ✓",
            ))
            return
        self.viewer_blunder_btn.setVisible(True)
        self.viewer_status.setText(t(
            f"Stockfish: {patzer} Patzer, {ungenau} Ungenauigkeit(en) in deinen Zügen. "
            "Mit »⛔ nächster Patzer« hinspringen.",
            f"Stockfish: {patzer} blunder(s), {ungenau} inaccuracy(ies) in your moves. "
            "Use »⛔ next blunder« to jump there.",
        ))

    def _on_viewer_analysis_failed(self, msg: str) -> None:
        self._teardown_viewer_analysis()
        self.viewer_analyze_btn.setEnabled(True)
        if msg == "nostockfish":
            self.viewer_status.setText(t(
                "Stockfish nicht gefunden. Installiere es einmalig im Terminal mit "
                "»brew install stockfish« — danach läuft die Analyse.",
                "Stockfish not found. Install it once in the Terminal with "
                "»brew install stockfish« — then the analysis will run.",
            ))
        else:
            self.viewer_status.setText(t(f"Prüfung fehlgeschlagen: {msg}", f"Analysis failed: {msg}"))

    def _viewer_next_blunder(self) -> None:
        if not self._viewer_issues:
            return
        # nächste markierte Stelle nach der aktuellen Position (Stellung NACH dem Fund-Zug)
        targets = sorted(ply + 1 for ply in self._viewer_issues)
        nxt = next((p for p in targets if p > self._viewer_pos), targets[0])
        self._viewer_pos = nxt
        self._viewer_render()

    def _open_stats(self) -> None:
        self._refresh_stats()
        self.stack.setCurrentIndex(2)

    def _stats_error_row(self, problem: dict) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        widget.setObjectName("libraryrow")
        box = QtWidgets.QVBoxLayout(widget)
        box.setContentsMargins(14, 9, 14, 9)
        box.setSpacing(2)
        name = self._plain_label(self._tname(problem["name"]))
        name.setObjectName("rowname")
        played = problem.get("played") or "?"
        count = problem["count"]
        sub = QtWidgets.QLabel(t(
            f"richtig wäre: {problem['expected_san']}    ·    du spieltest: {played}    ·    {count}× verpasst",
            f"correct: {problem['expected_san']}    ·    you played: {played}    ·    missed {count}×",
        ))
        sub.setObjectName("rowsub")
        box.addWidget(name)
        box.addWidget(sub)
        return widget

    def _drill_one_from_item(self, item: QtWidgets.QListWidgetItem) -> None:
        problem = item.data(QtCore.Qt.UserRole)
        if not problem:
            return
        self._drill_positions_for_fens([problem["fen"]], t("STELLUNG ÜBEN", "DRILL POSITION"))

    def _refresh_stats(self) -> None:
        overview = overall_progress(self.stats_store.events)
        problems = self._collect_error_problems()
        self.stats_list.clear()

        if overview.session_count == 0:
            self.stats_overview.setText("")
            self.stats_sub.setText("")
            self.stats_empty.setVisible(True)
            self.stats_list.setVisible(False)
            self.stats_drill_all.setVisible(False)
            return
        self.stats_empty.setVisible(False)
        self.stats_list.setVisible(True)

        text = t(
            f"Trefferquote gesamt {round(overview.accuracy * 100)} %      {overview.attempts} Züge geübt",
            f"Overall accuracy {round(overview.accuracy * 100)}%      {overview.attempts} moves trained",
        )
        if overview.session_count >= 2 and overview.first_accuracy is not None and overview.last_accuracy is not None:
            if overview.last_accuracy > overview.first_accuracy:
                arrow = "↗"
            elif overview.last_accuracy < overview.first_accuracy:
                arrow = "↘"
            else:
                arrow = "→"
            text += t(
                f"      Tendenz {round(overview.first_accuracy * 100)} % {arrow} {round(overview.last_accuracy * 100)} %",
                f"      Trend {round(overview.first_accuracy * 100)}% {arrow} {round(overview.last_accuracy * 100)}%",
            )
        self.stats_overview.setText(text)

        if not problems:
            self.stats_sub.setText(t(
                "Keine offenen Fehler — stark! 💪  Alle bisher verpassten Züge sitzen wieder.",
                "No open mistakes — great! 💪  All previously missed moves are back.",
            ))
            self.stats_drill_all.setVisible(False)
            return
        self.stats_sub.setText(t(
            f"Diese {len(problems)} Stellungen sitzen noch nicht — klick eine an, um sie gezielt zu üben:",
            f"These {len(problems)} positions aren't solid yet — click one to drill it:",
        ))
        this_round = min(len(problems), WEAK_SESSION_LIMIT)
        self.stats_drill_all.setText(t(
            f"▶  Alle üben  ({this_round})", f"▶  Drill all  ({this_round})"))
        self.stats_drill_all.setVisible(True)
        for problem in problems:
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.UserRole, problem)
            row = self._stats_error_row(problem)
            item.setSizeHint(row.sizeHint())
            self.stats_list.addItem(item)
            self.stats_list.setItemWidget(item, row)

    # --- Trainings-Loop --------------------------------------------------

    def _train_color_for(self, line):
        """Farbe, in der eine Eröffnung geübt wird: aus ihrer Repertoire-Seite.
        Ohne Zuordnung gilt die globale Voreinstellung."""
        side = self._side_of_line(line)
        if side == "white":
            return chess.WHITE
        if side == "black":
            return chess.BLACK
        return self.train_color

    def _collect_error_problems(self) -> list:
        """Alle offenen Fehlerstellungen (letzter Versuch falsch) über das
        Repertoire beider Seiten, häufigste zuerst — positions-basiert und
        varianten-bewusst (transpositions-dedupliziert)."""
        from opening_trainer.tree_session import open_error_positions
        problems = []
        for color, side_name in ((chess.WHITE, "white"), (chess.BLACK, "black")):
            problems += open_error_positions(
                self.tree_store.by_side(side_name), color, self.stats_store)
        problems.sort(key=lambda p: -p["count"])
        return problems

    def _library_row(self, line) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        widget.setObjectName("libraryrow")
        box = QtWidgets.QVBoxLayout(widget)
        box.setContentsMargins(14, 9, 14, 9)
        box.setSpacing(2)
        has_note = self.line_notes.has_note(line.source_name, line.name)
        name = self._plain_label(f"📝  {self._display_name(line)}" if has_note else self._display_name(line))
        name.setObjectName("rowname")
        if has_note:
            name.setToolTip(self.line_notes.note_of(line.source_name, line.name))
        # Fälligkeit/Trefferquote stehen jetzt positions-genau auf »Heute fällig«
        # und »Fortschritt« — die Bibliothek ist reine Browse-/Zuordnungs-Fläche.
        parts = []
        group = self._group_text_for_line(line)
        if group:
            parts.append(group)
        side = self._side_of_line(line)
        if side:
            parts.append(t("Weiß", "White") if side == "white" else t("Schwarz", "Black"))
        sub = QtWidgets.QLabel("  ·  ".join(parts))
        sub.setObjectName("rowsub")
        box.addWidget(name)
        if parts:
            box.addWidget(sub)
        return widget

    def _editor_tree_row(self, tree) -> QtWidgets.QWidget:
        """Zeile für einen Editor-eigenen Baum (kein PGN-Linien-Pendant)."""
        widget = QtWidgets.QWidget()
        widget.setObjectName("libraryrow")
        box = QtWidgets.QVBoxLayout(widget)
        box.setContentsMargins(14, 9, 14, 9)
        box.setSpacing(2)
        name = self._plain_label(self._tname(tree.name) or t("(ohne Namen)", "(unnamed)"))
        name.setObjectName("rowname")
        box.addWidget(name)
        if tree.side in ("white", "black"):
            sub = QtWidgets.QLabel(t("Weiß", "White") if tree.side == "white" else t("Schwarz", "Black"))
            sub.setObjectName("rowsub")
            box.addWidget(sub)
        return widget

    def _editor_own_trees(self) -> list:
        """Editor-eigene Bäume (ohne ``_auto``-Marke), gefiltert nach Seiten-Tab
        und Suche — sie haben kein PGN-Linien-Pendant und fehlten der Bibliothek."""
        trees = [tr for tr in self.tree_store.all() if tr.headers.get("_auto") != "1"]
        if self._side_filter in ("white", "black"):
            trees = [tr for tr in trees if tr.side == self._side_filter]
        elif self._side_filter == "none":
            trees = [tr for tr in trees if tr.side not in ("white", "black")]
        if self.search_query:
            trees = [tr for tr in trees
                     if all(tok in self._tname(tr.name).casefold() for tok in self.search_query.split())]
        return sorted(trees, key=lambda tr: self._tname(tr.name).casefold())

    # Reihenfolge der Spalten nach erstem Zug — sprachunabhängig per Zug-UCI
    # (nicht per Etikett, das je nach Sprache 1.Sf3/1.Nf3 heißt). Unbekannte erste
    # Züge sortieren ans Ende, werden aber trotzdem unter „Weiß ▸ 1.x" gruppiert.
    _FIRST_ORDER_UCI = {
        "e2e4": 0, "d2d4": 1, "c2c4": 2, "g1f3": 3, "g2g3": 4,
        "b2b3": 5, "f2f4": 6, "b1c3": 7, "b2b4": 8, "f2f3": 9,
        "d2d3": 10, "e2e3": 11, "g1h3": 12, "b1a3": 13,
    }

    def _first_move_uci(self, line) -> str:
        """Erster Halbzug der Linie als UCI (z. B. »e2e4«) – sprachunabhängiger
        Schlüssel für Sortierung."""
        return line.moves_uci[0] if line.moves_uci else ""

    def _first_move_label(self, line) -> str:
        """Erster (Weiß-)Zug der Linie als Etikett, z. B. „1.e4", „1.Sf3"."""
        if not line.moves_uci:
            return "—"
        board = chess.Board()
        try:
            san = board.san(chess.Move.from_uci(line.moves_uci[0]))
        except Exception:  # noqa: BLE001
            return "?"
        if i18n.language() == "de":
            san = san.translate(str.maketrans({"N": "S", "B": "L", "R": "T", "Q": "D"}))
        return f"1.{san}"

    def _system_label(self, line) -> str | None:
        """Nur für Weiß ▸ 1.d4: das gewählte System (Damengambit / London /
        Katalanisch) – dort gruppieren wir nach System statt nach Familie."""
        if self._side_of_line(line) != "white" or not line.moves_uci or line.moves_uci[0] != "d2d4":
            return None
        nm = line.name.lower()
        if "london" in nm:
            return t("London-System", "London System")
        if "katalan" in nm or "catalan" in nm:
            return t("Katalanisch", "Catalan")
        return t("Damengambit", "Queen's Gambit")

    def _family_label(self, line) -> str:
        """Eröffnungs-Familie aus dem Namen (Sizilianisch, Caro-Kann …)."""
        nm = line.name.lower()
        for keyword, family in _FAMILY_KEYWORDS:
            if keyword in nm:
                return t(family, _FAMILY_EN.get(family, family))
        return t("Sonstige", "Other")

    def _subgroup_label(self, line) -> str:
        """Unter-Überschrift: bei Weiß ▸ 1.d4 das System, sonst die Familie."""
        return self._system_label(line) or self._family_label(line)

    def _group_label(self, line) -> str:
        """Haupt-Überschrift: Weiß ▸ 1.e4 / Schwarz ▸ gegen 1.e4."""
        move = self._first_move_label(line)
        side = self._side_of_line(line)
        if side == "white":
            return t(f"Weiß  ▸  {move}", f"White  ▸  {move}")
        if side == "black":
            return t(f"Schwarz  ▸  gegen {move}", f"Black  ▸  vs {move}")
        return t(f"Ohne Zuordnung  ▸  {move}", f"Unassigned  ▸  {move}")

    def _category_sort_key(self, line):
        side = self._side_of_line(line)
        side_rank = {"white": 0, "black": 1}.get(side, 2)
        move_rank = self._FIRST_ORDER_UCI.get(self._first_move_uci(line), 99)
        return (side_rank, move_rank, self._first_move_uci(line), self._subgroup_label(line), line.name)

    def _add_library_header(self, text: str, level: int = 1) -> None:
        item = QtWidgets.QListWidgetItem()
        item.setFlags(QtCore.Qt.NoItemFlags)  # Überschrift: nicht wählbar/klickbar
        label = QtWidgets.QLabel(text)
        label.setObjectName("cathead" if level == 1 else "subhead")
        height = 48 if level == 1 else 36
        label.setMinimumHeight(height - 2)
        item.setSizeHint(QtCore.QSize(200, height))
        self.library_list.addItem(item)
        self.library_list.setItemWidget(item, label)

    def _refresh_library(self) -> None:
        self.library_list.clear()
        editor_trees = self._editor_own_trees()
        if not self.tree_store.all():
            self.library_empty.setVisible(True)
            self.library_list.setVisible(False)
            return
        self.library_empty.setVisible(False)
        self.library_list.setVisible(True)
        lines = sorted(self._filtered_lines(), key=self._category_sort_key)
        if not lines and not editor_trees and self.search_query:
            self._add_library_header(t("Keine Eröffnung gefunden — Suche anpassen.", "No opening found — adjust your search."), level=1)
            return
        group_counts: dict[str, int] = {}
        sub_counts: dict[tuple, int] = {}
        for line in lines:
            g = self._group_label(line)
            group_counts[g] = group_counts.get(g, 0) + 1
            key = (g, self._subgroup_label(line))
            sub_counts[key] = sub_counts.get(key, 0) + 1
        current_group = None
        current_sub = None
        for line in lines:
            group = self._group_label(line)
            sub = self._subgroup_label(line)
            if group != current_group:
                current_group = group
                current_sub = None
                self._add_library_header(f"{group}    ({group_counts[group]})", level=1)
            if sub != current_sub:
                current_sub = sub
                self._add_library_header(f"{sub}    ({sub_counts[(group, sub)]})", level=2)
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.UserRole, line)
            row = self._library_row(line)
            item.setSizeHint(row.sizeHint())
            self.library_list.addItem(item)
            self.library_list.setItemWidget(item, row)

        # Editor-eigene Bäume (kein PGN-Linien-Pendant) als eigene Sektion.
        if editor_trees:
            self._add_library_header(
                t(f"Repertoire-Bäume (Editor)    ({len(editor_trees)})",
                  f"Repertoire trees (editor)    ({len(editor_trees)})"), level=1)
            for tree in editor_trees:
                item = QtWidgets.QListWidgetItem()
                item.setData(QtCore.Qt.UserRole, tree)
                row = self._editor_tree_row(tree)
                item.setSizeHint(row.sizeHint())
                self.library_list.addItem(item)
                self.library_list.setItemWidget(item, row)

    def _migrate_sides_from_groups(self, lines) -> None:
        """Übernimmt einmalig die vorhandene Gruppen-Zuordnung (Tkinter-Daten) in
        das Pro-Eröffnung-Modell, damit das bestehende Repertoire erhalten bleibt.
        ``lines`` sind die einmalig geparsten Legacy-Linien (kein Dauerzustand)."""
        if self.opening_sides.sides:
            return
        rep = self.repertoire_store.repertoire
        white = {(l.source_name, l.name) for l in rep.lines_for_side(SIDE_WHITE, lines)}
        black = {(l.source_name, l.name) for l in rep.lines_for_side(SIDE_BLACK, lines)}
        changed = False
        for line in lines:
            key = (line.source_name, line.name)
            if key in white:
                self.opening_sides.set_side(line.source_name, line.name, "white")
                changed = True
            elif key in black:
                self.opening_sides.set_side(line.source_name, line.name, "black")
                changed = True
        if changed:
            self.opening_sides.save(self.sides_path)

    def _assign_side_for_file(self, source_name: str, side: str) -> int:
        """Ordnet allen geladenen Eröffnungen DIESER Datei die Spielerfarbe zu –
        aber nur, wo noch KEINE Zuordnung besteht (bestehende bleiben unangetastet).
        Gibt die Zahl der neu zugeordneten Eröffnungen zurück."""
        if side not in ("white", "black"):
            return 0
        count = 0
        for line in self._catalog():
            if line.source_name != source_name:
                continue
            if self.opening_sides.side_of(line.source_name, line.name) is None:
                self.opening_sides.set_side(line.source_name, line.name, side)
                count += 1
        if count:
            self.opening_sides.save(self.sides_path)
            self._sync_auto_trees()
            self._refresh_library()
        return count

    def _auto_fill_sides_by_filename(self) -> int:
        """Füllt fehlende Seiten-Zuordnungen automatisch aus dem Dateinamen jeder
        Quelle (»Weiss …« → Weiß, »Schwarz …« → Schwarz). Bestehende Zuordnungen
        und mehrdeutige Namen bleiben unberührt. Gibt die Zahl der Treffer zurück."""
        count = 0
        for line in self._catalog():
            if self.opening_sides.side_of(line.source_name, line.name) is not None:
                continue
            guess = side_from_name(line.source_name)
            if guess in ("white", "black"):
                self.opening_sides.set_side(line.source_name, line.name, guess)
                count += 1
        if count:
            self.opening_sides.save(self.sides_path)
            self._sync_auto_trees()
            self._refresh_library()
        return count

    def _side_of_line(self, line) -> str | None:
        # Seite PRO Eröffnung aus der Zuordnung (nicht die Datei-Mehrheit des Baums) —
        # so zeigt die Bibliothek gemischte Dateien korrekt (z. B. die Beispiele:
        # Italienisch=Weiß, Caro/Damengambit=Schwarz).
        side = self.opening_sides.side_of(line.source_name, line.name)
        return side if side in ("white", "black") else None

    def _on_search(self, text: str) -> None:
        self.search_query = text.strip().casefold()
        self._refresh_library()

    def _filtered_lines(self) -> list:
        catalog = self._catalog()
        if self._side_filter is None:
            lines = catalog
        elif self._side_filter in ("white", "black"):
            lines = [l for l in catalog if self._side_of_line(l) == self._side_filter]
        else:
            lines = [l for l in catalog if self._side_of_line(l) is None]
        if self.search_query:
            lines = [l for l in lines if self._matches_search(l)]
        return lines

    def _matches_search(self, line) -> bool:
        """Sucht in Name, Familie und Gruppen-Überschrift (z. B. „1.e4")."""
        parts = [
            line.name or "",
            self._display_name(line),   # auch der übersetzte Name (Englisch-Modus)
            self._subgroup_label(line),
            self._group_label(line),
        ]
        haystack = "  ".join(parts).casefold()
        return all(token in haystack for token in self.search_query.split())

    def _group_text_for_line(self, line) -> str:
        names = [c.name for c in self.repertoire_store.repertoire.categories if c.contains(line)]
        return names[0] if names else ""

    def _set_side_filter(self, key) -> None:
        self._side_filter = key
        self._side_buttons[key].setChecked(True)
        titles = {
            None: t("Deine Eröffnungen", "Your openings"),
            "white": t("Weiß-Repertoire", "White repertoire"),
            "black": t("Schwarz-Repertoire", "Black repertoire"),
            "none": t("Noch keinem Repertoire zugeordnet", "Not assigned to a repertoire yet"),
        }
        self.lib_title.setText(titles[key])
        trainable = [l for l in self._filtered_lines() if l.moves_uci]
        if key in ("white", "black"):
            side = t("Weiß", "White") if key == "white" else t("Schwarz", "Black")
            self.train_side_btn.setText(t(f"{side}-Repertoire üben  ({len(trainable)})", f"Train {side} repertoire  ({len(trainable)})"))
            self.train_side_btn.setVisible(bool(trainable))
            self.lib_sub.setText(t(f"{len(trainable)} Eröffnungen in deinem {side}-Repertoire.", f"{len(trainable)} openings in your {side} repertoire."))
        elif key == "none":
            self.train_side_btn.hide()
            self.lib_sub.setText(t(
                "Noch keinem Repertoire zugeordnet. Wähle eine aus und ordne sie unten zu.",
                "Not assigned to a repertoire yet. Pick one and assign it below.",
            ))
        else:
            self.train_side_btn.hide()
            self.lib_sub.setText(t(
                "Wähle eine Eröffnung, dann unten zuordnen oder „Üben“. (Doppelklick übt direkt.)",
                "Pick an opening, then assign it below or ‘Train’. (Double-click trains directly.)",
            ))
        self._refresh_library()

    def _train_side(self) -> None:
        # Stellungs-basiert: fällige/neue Stellungen dieser Repertoire-Seite.
        if self._side_filter in ("white", "black"):
            self._start_due_session(only_side=self._side_filter)

    def _open_library(self) -> None:
        self._refresh_library()
        self.stack.setCurrentIndex(1)

    def _close_library(self) -> None:
        self._go_home()

    def _is_tree_item(self, data) -> bool:
        return data is not None and hasattr(data, "id") and data.id in self.tree_store.trees

    def _train_from_library(self, item: QtWidgets.QListWidgetItem) -> None:
        data = item.data(QtCore.Qt.UserRole)
        if self._is_tree_item(data):           # Editor-eigener Baum -> direkt drillen
            self._start_tree_drill(data)
            return
        if data is None or not getattr(data, "moves_uci", None):
            return
        side = self._side_of_line(data)
        if side not in ("white", "black"):
            return                    # ohne Seiten-Zuordnung kein Baum-Drill (erst zuordnen)
        from opening_trainer.tree_session import tree_for_moves
        color = chess.WHITE if side == "white" else chess.BLACK
        tree = tree_for_moves(self.tree_store.by_side(side), data.moves_uci, color)
        if tree is not None:
            self._start_tree_drill(tree)

    def _selected_library_line(self):
        """Die ausgewählte LINIE (für Seiten-Zuordnung). Editor-Baum-Zeilen
        zählen nicht — die werden im Editor zugeordnet."""
        items = self.library_list.selectedItems()
        if not items:
            return None
        data = items[0].data(QtCore.Qt.UserRole)
        return None if self._is_tree_item(data) else data

    def _on_library_selection(self) -> None:
        items = self.library_list.selectedItems()
        data = items[0].data(QtCore.Qt.UserRole) if items else None
        is_tree = self._is_tree_item(data)
        is_line = data is not None and not is_tree
        for btn in (self.assign_white_btn, self.assign_black_btn, self.assign_none_btn, self.note_btn):
            btn.setEnabled(is_line)                 # Zuordnung + Notiz nur für Linien
        self.train_one_btn.setEnabled(is_line or is_tree)   # üben für beides

    def _edit_note_selected(self) -> None:
        """Persönliche Notiz zur ausgewählten Eröffnung anlegen/ändern (📝 in der Liste)."""
        line = self._selected_library_line()
        if line is None:
            return
        current = self.line_notes.note_of(line.source_name, line.name)
        label = t(f"Notiz zu »{self._display_name(line)}«:",
                  f"Note on »{self._display_name(line)}«:")
        text, ok = QtWidgets.QInputDialog.getMultiLineText(
            self, t("Notiz", "Note"), label, current)
        if not ok:
            return
        self.line_notes.set_note(line.source_name, line.name, text.strip())
        self.line_notes.save(self.notes_path)
        self._refresh_library()

    def _train_selected_library(self) -> None:
        items = self.library_list.selectedItems()
        if items:
            self._train_from_library(items[0])

    def _assign_selected(self, side: str) -> None:
        line = self._selected_library_line()
        if line is None:
            return
        self.opening_sides.set_side(line.source_name, line.name, side)
        self.opening_sides.save(self.sides_path)
        self._sync_auto_trees()                    # Auto-Baum-Seite an die Zuordnung angleichen
        self._set_side_filter(self._side_filter)  # Liste, Titel und Zähler auffrischen

    # Seiten der mitgelieferten Beispiele: Italienisch übt man als Weiß,
    # Caro-Kann und Damengambit-Abgelehnt als Schwarz.
    _SAMPLE_SIDES = {
        "Italienische Partie — Hauptvariante": "white",
        "Caro-Kann — Klassische Variante": "black",
        "Damengambit Abgelehnt — Klassisches System": "black",
    }

    def _load_sample_lines(self) -> None:
        path = sample_pgn_path()
        if not path.exists():
            QtWidgets.QMessageBox.warning(
                self, t("Beispiele fehlen", "Samples missing"),
                t("Die Beispiel-Datei wurde nicht gefunden.", "The sample file was not found."),
            )
            return
        try:
            lines = load_pgn_file(path)
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.warning(self, t("Laden fehlgeschlagen", "Loading failed"), str(exc))
            return
        # Die Beispiel-Datei als saubere Einzeldatei-Quelle eintragen (NICHT über
        # last_pgn_folder=Eltern-Ordner — der enthält dieselbe Datei und würde sie
        # ein zweites Mal laden, also Dubletten erzeugen).
        self.settings_store.update(
            pgn_sources=(str(path),),
            last_pgn_path=str(path),
            last_pgn_kind="file",
        )
        self.settings_store.save(self.settings_path)
        for line in lines:
            side = self._SAMPLE_SIDES.get(line.name)
            if side and self.opening_sides.side_of(line.source_name, line.name) is None:
                self.opening_sides.set_side(line.source_name, line.name, side)
        self.opening_sides.save(self.sides_path)
        self._sync_auto_trees()
        pass
        self._refresh_library()
        pass

    def _load_pgn_dialog(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, t("PGN-Datei laden", "Load PGN file"), "",
            t("PGN-Dateien (*.pgn);;Alle Dateien (*)", "PGN files (*.pgn);;All files (*)")
        )
        if not path:
            return
        try:
            lines = load_pgn_file(Path(path))
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.warning(self, t("Laden fehlgeschlagen", "Loading failed"), str(exc))
            return
        if not lines:
            QtWidgets.QMessageBox.information(
                self, t("Keine Eröffnungen", "No openings"),
                t("Die Datei enthält keine trainierbaren Eröffnungen.", "The file contains no trainable openings."),
            )
            return
        added = self._add_pgn_source(path)   # HINZUFÜGEN statt ersetzen
        self._ask_and_assign_side(Path(path).name)
        self._open_library()                 # Ergebnis sichtbar machen (Feedback am richtigen Ort)
        self.lib_sub.setText(t(
            f"{added} Eröffnungen hinzugefügt — {len(self._catalog())} insgesamt. Klick eine an, um sie zu üben.",
            f"Added {added} openings — {len(self._catalog())} in total. Click one to train it."))
        self._show_tree_report(source=path)  # Bericht + »Jetzt diese Datei üben«

    def _tree_report_lines(self) -> list:
        """Eine Zeile je Seite mit Repertoire: »N Linien → 1 Baum mit B
        Verzweigungen« bzw. »rein linear«. Rein (kein Dialog) -> testbar."""
        from opening_trainer.tree_session import merge_stats
        parts = []
        for side_name, color, label in (
            ("white", chess.WHITE, t("Weiß", "White")),
            ("black", chess.BLACK, t("Schwarz", "Black")),
        ):
            st = merge_stats(self.tree_store.by_side(side_name), color)
            if st["lines"] == 0:
                continue
            if st["branches"] > 0:
                parts.append(t(
                    f"{label}: {st['lines']} Linien → 1 Baum mit {st['branches']} Verzweigungen.",
                    f"{label}: {st['lines']} lines → 1 tree with {st['branches']} branches."))
            else:
                parts.append(t(
                    f"{label}: {st['lines']} Linien — rein linear, keine Verzweigungen.",
                    f"{label}: {st['lines']} lines — purely linear, no branches."))
        return parts

    def _show_tree_report(self, source: str | None = None) -> None:
        """Kurzer Bericht nach dem Laden — mit Direkt-Knöpfen: die gerade geladene
        Datei sofort üben, oder im Repertoire-Baum ansehen."""
        parts = self._tree_report_lines()
        if not parts:
            return
        box = QtWidgets.QMessageBox(self)
        box.setWindowTitle(t("Baum-Struktur", "Tree structure"))
        box.setText("\n".join(parts))
        box.setInformativeText(t(
            "Gleiche Stellungen verschiedener Linien werden zu einem Baum zusammengeführt.",
            "Identical positions across lines are merged into one tree."))
        train_btn = None
        if source:
            train_btn = box.addButton(t("▶  Jetzt diese Datei üben", "▶  Train this file now"),
                                      QtWidgets.QMessageBox.ButtonRole.AcceptRole)
        view_btn = box.addButton(t("Im Repertoire-Baum ansehen", "View repertoire tree"),
                                 QtWidgets.QMessageBox.ButtonRole.AcceptRole)
        box.addButton(t("Schließen", "Close"), QtWidgets.QMessageBox.ButtonRole.RejectRole)
        # Nicht-modal (show statt exec): blockiert weder die App noch Tests.
        box.setModal(False)
        box.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self._tree_report_box = box                      # Referenz halten (sonst GC)

        def on_click(b):
            if b is view_btn:
                self._open_repertoire_tree()
            elif train_btn is not None and b is train_btn:
                self._train_source(source)
        box.buttonClicked.connect(on_click)
        box.show()

    def _ask_and_assign_side(self, source_name: str) -> None:
        """Fragt beim Laden einer Datei einmal nach der Spielerfarbe (Vorschlag aus
        dem Dateinamen) und ordnet alle noch nicht zugeordneten Eröffnungen dieser
        Datei der gewählten Seite zu. Sind bereits alle zugeordnet, wird nicht gefragt."""
        file_lines = [l for l in self._catalog() if l.source_name == source_name]
        if file_lines and all(
            self.opening_sides.side_of(l.source_name, l.name) is not None for l in file_lines
        ):
            return
        items = [t("Weiß", "White"), t("Schwarz", "Black"), t("Überspringen", "Skip")]
        guess = side_from_name(source_name)
        default = {"white": 0, "black": 1}.get(guess, 0)
        choice, ok = QtWidgets.QInputDialog.getItem(
            self, t("Spielerfarbe", "Player color"),
            t(f"Welche Farbe spielst du in »{source_name}«?\n"
              "(So werden die Eröffnungen unter »Weiß ▸ 1.e4« bzw. »Schwarz ▸ gegen 1.e4« gruppiert.)",
              f"Which color do you play in »{source_name}«?\n"
              "(This groups the openings under »White ▸ 1.e4« or »Black ▸ vs 1.e4«.)"),
            items, default, False)
        if not ok:
            return
        side = {items[0]: "white", items[1]: "black", items[2]: "none"}[choice]
        self._assign_side_for_file(source_name, side)

    def _load_folder_dialog(self) -> None:
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, t("Ordner mit PGN-Dateien laden", "Load folder of PGN files"))
        if not folder:
            return
        try:
            lines = load_pgn_folder(Path(folder))
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.warning(self, t("Laden fehlgeschlagen", "Loading failed"), str(exc))
            return
        if not lines:
            QtWidgets.QMessageBox.information(
                self, t("Keine Eröffnungen", "No openings"),
                t("Im Ordner wurden keine trainierbaren Eröffnungen (.pgn) gefunden.", "No trainable openings (.pgn) found in the folder."),
            )
            return
        added = self._add_pgn_source(folder)   # HINZUFÜGEN statt ersetzen
        assigned = self._auto_fill_sides_by_filename()   # je Datei aus dem Namen (Weiss…/Schwarz…)
        catalog = self._catalog()
        unassigned = sum(1 for l in catalog if self._side_of_line(l) is None)
        msg_de = f"{added} Eröffnungen aus dem Ordner hinzugefügt — {len(catalog)} insgesamt."
        msg_en = f"Added {added} openings from the folder — {len(catalog)} in total."
        if assigned:
            msg_de += f" {assigned} automatisch zugeordnet."
            msg_en += f" {assigned} auto-assigned."
        if unassigned:
            msg_de += (f" {unassigned} ohne Farbe — wähle sie über den Filter »Ohne Zuordnung« "
                       "und ordne sie Weiß/Schwarz zu.")
            msg_en += (f" {unassigned} without a color — pick them via the »Unassigned« filter "
                       "and assign them to White/Black.")
        self._open_library()                  # Ergebnis sichtbar machen (Feedback am richtigen Ort)
        self.lib_sub.setText(t(msg_de, msg_en))
        self._show_tree_report(source=folder)  # Bericht + »Jetzt diesen Ordner üben«
