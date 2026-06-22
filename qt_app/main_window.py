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
from qt_app.board_view import (
    BoardView, EvalBar, MasteryBar, WdlBar, BOARD_THEMES, set_board_theme,
)
from qt_app import i18n
from qt_app.i18n import t
from opening_trainer.mastery import mastery_bucket, summarize_mastery
from opening_trainer.explorer import parse_explorer_response, percent
from opening_trainer.game_review import build_repertoire_book, review_game
from opening_trainer.opening_names_en import to_english
from qt_app.paths import data_dir, sample_pgn_path

STYLE = """
QWidget { background: #f6f6f3; color: #23241f; font-family: -apple-system, 'Helvetica Neue', Arial, sans-serif; font-size: 14px; }
QLabel#eyebrow { color: #8a8f80; font-size: 12px; font-weight: 600; }
QLabel#name    { font-size: 23px; font-weight: 600; color: #23241f; }
QLabel#hint    { color: #6b7066; font-size: 14px; }
QLabel#note    { color: #6b6f66; font-size: 13px; font-style: italic; }
QLabel#status  { font-size: 15px; color: #3a3d35; }
QLabel#due     { color: #8a8f80; font-size: 13px; }
QLabel#empty   { color: #9a9f90; font-size: 16px; }
QPushButton { background: #ffffff; border: 1px solid #c2cdb0; border-radius: 9px; padding: 9px 15px; color: #4f6a38; font-weight: 600; }
QPushButton:hover { background: #eef2e8; border-color: #779556; }
QPushButton:pressed { background: #e2e6d8; }
QPushButton:disabled { background: #f2f2ee; color: #bcbcb3; border-color: #e8e8e1; }
QPushButton#primary { background: #779556; border: none; color: white; font-weight: 600; }
QPushButton#primary:hover { background: #6b8a4c; }
QPushButton#primary:disabled { background: #cdd6c0; color: #eef2e8; }
QPushButton#more { background: #ffffff; border: 1px solid #c2cdb0; border-radius: 9px; padding: 9px 15px; color: #4f6a38; font-weight: 600; }
QPushButton#more:hover { background: #eef2e8; border-color: #779556; }
QPushButton#more:pressed { background: #e2e6d8; }
QPushButton#more:disabled { background: #f2f2ee; color: #bcbcb3; border-color: #e8e8e1; }
QLabel { background: transparent; }
QLabel#rowname { font-size: 15px; font-weight: 600; color: #23241f; }
QLabel#rowsub  { font-size: 12px; color: #8a8f80; }
QWidget#libraryrow { background: transparent; }
QListWidget#library { background: transparent; border: none; }
QListWidget#library::item { background: transparent; border: none; margin: 2px 0; }
QListWidget#library::item:enabled { background: #ffffff; border: 1px solid #e4e5dd; border-radius: 8px; }
QListWidget#library::item:hover:enabled { background: #f0f2ea; }
QListWidget#library::item:selected { background: #eef3e8; border: 1px solid #779556; }
QPushButton#seg { background: #ffffff; border: 1px solid #dadbd2; border-radius: 8px; padding: 7px 14px; color: #3a3d35; }
QPushButton#seg:hover { background: #eef0e8; }
QPushButton#seg:checked { background: #779556; border: 1px solid #779556; color: white; font-weight: 600; }
QLabel#cathead { color: #2f3a25; font-size: 18px; font-weight: 800; padding: 14px 4px 6px 4px; }
QLabel#subhead { color: #5b6b48; font-size: 14px; font-weight: 700; padding: 8px 4px 3px 22px; }
QLineEdit#search {
    font-size: 15px; padding: 9px 12px; margin: 2px 0 6px 0;
    border: 1px solid #d9d9cf; border-radius: 9px; background: #ffffff;
}
QLineEdit#search:focus { border-color: #6f8a4f; }
"""


APP_VERSION = "1.0.4"
REPO_URL = "https://github.com/vancoeur/chess-opening-trainer"

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


class _TuvWorker(QtCore.QObject):
    """Läuft im Hintergrund-Thread: prüft jede zugeordnete Linie mit Stockfish."""

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


class _EvalBarWorker(QtCore.QObject):
    """Bewertet im Hintergrund-Thread fortlaufend die aktuelle Stellung für die
    Bewertungs-Leiste. Eigene Stockfish-Instanz, damit es die Prüfung/Übe-Eval nicht
    stört. Veraltete Anfragen filtert der Hauptthread per FEN-Abgleich heraus."""

    evaluated = QtCore.Signal(str, int, int)   # fen, cp (Weiß-Sicht), mate (signiert)

    def __init__(self) -> None:
        super().__init__()
        self._engine = None
        self._broken = False

    @QtCore.Slot(str)
    def evaluate(self, fen: str) -> None:
        if self._broken:
            return
        import chess
        import chess.engine
        if self._engine is None:
            from qt_app.engine import find_stockfish
            sf = find_stockfish()
            if sf is None:
                self._broken = True
                return
            try:
                self._engine = chess.engine.SimpleEngine.popen_uci(str(sf))
            except Exception:  # noqa: BLE001
                self._broken = True
                return
        try:
            info = self._engine.analyse(chess.Board(fen), chess.engine.Limit(depth=12))
            score = info["score"].white()
            mate = score.mate() or 0
            cp = 0 if mate else (score.score() or 0)
            self.evaluated.emit(fen, int(cp), int(mate))
        except Exception:  # noqa: BLE001
            pass

    @QtCore.Slot()
    def shutdown(self) -> None:
        if self._engine is not None:
            try:
                self._engine.quit()
            except Exception:  # noqa: BLE001
                pass
            self._engine = None


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
    _evalRequested = QtCore.Signal(str)
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
        self.lines = self._load_lines()
        self._migrate_sides_from_groups()
        self.train_color = chess.BLACK if self.settings_store.settings.train_color == "black" else chess.WHITE

        # Repertoire-Bäume (neue, baum-basierte Datenhaltung): einmalige, idempotente
        # Migration der linearen Bestandsdaten, danach laden. ADDITIV — die bisherige
        # lineare Trainingslogik bleibt vorerst aktiv (Umstellung folgt separat).
        self.trees_path = data / "repertoire_trees.json"
        self.position_schedule_path = data / "position_schedule.json"
        try:
            run_migration(data, self.lines)
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
        self._due_session = False      # True: „Heute fällig (Bäume)"-Sitzung läuft
        self._due_queue: list = []     # offene fällige Stellungen (tree, node_id, color)
        self._due_total = 0
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
        self._show_eval_bar = self._eval_settings.value("show_eval_bar", True, type=bool)
        from qt_app.engine import find_stockfish
        self._stockfish_available = find_stockfish() is not None
        self._eval_bar_thread = None
        self._eval_bar_worker = None

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
        self._viewer_line = None
        self._viewer_color = chess.WHITE
        self._viewer_issues: dict = {}   # ply -> MoveIssue (Stockfish-Patzer der Partie)
        self._viewer_anal_thread = None
        self._viewer_anal_worker = None

        self._threads_stopped = False
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
        self._refill_queue()
        self._start_next()

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
        reset_act = file_menu.addAction(t("Repertoire leeren …", "Clear repertoire …"))
        reset_act.triggered.connect(self._reset_repertoire)

        go_menu = self.menuBar().addMenu(t("Gehe zu", "Go"))
        for label_de, label_en, shortcut, slot in [
            ("Start", "Home", "Ctrl+1", lambda: self.stack.setCurrentIndex(0)),
            ("Alle Eröffnungen", "All openings", "Ctrl+2", self._open_library),
            ("Auswertung", "Analysis", "Ctrl+3", self._open_stats),
            ("Fortschritt", "Progress", "Ctrl+4", self._open_progress),
            ("Partien auswerten", "Review games", "Ctrl+5", self._open_game_review),
            ("Repertoire-Prüfung", "Repertoire check", "Ctrl+6", self._open_tuv),
        ]:
            act = go_menu.addAction(t(label_de, label_en))
            act.setShortcut(QtGui.QKeySequence(shortcut))
            act.triggered.connect(lambda _=False, s=slot: s())
        go_menu.addSeparator()
        editor_act = go_menu.addAction(t("Repertoire-Editor", "Repertoire editor"))
        editor_act.setShortcut(QtGui.QKeySequence("Ctrl+E"))
        editor_act.triggered.connect(self._open_editor)
        due_act = go_menu.addAction(t("Heute fällig (Bäume)", "Due today (trees)"))
        due_act.setShortcut(QtGui.QKeySequence("Ctrl+D"))
        due_act.triggered.connect(self._start_due_session)
        drill_act = go_menu.addAction(t("Bäume üben", "Train trees"))
        drill_act.setShortcut(QtGui.QKeySequence("Ctrl+T"))
        drill_act.triggered.connect(self._open_tree_drill)
        go_menu.addSeparator()
        spar_act = go_menu.addAction(t("Gegen Stockfish spielen", "Play vs Stockfish"))
        spar_act.triggered.connect(self._open_sparring)
        expl_act = go_menu.addAction(t("Eröffnungs-Explorer (Lichess)", "Opening explorer (Lichess)"))
        expl_act.triggered.connect(self._open_explorer)

        view_menu = self.menuBar().addMenu(t("Ansicht", "View"))
        self._eval_bar_action = view_menu.addAction(t("Bewertungs-Leiste anzeigen", "Show evaluation bar"))
        self._eval_bar_action.setCheckable(True)
        self._eval_bar_action.setChecked(self._show_eval_bar and self._stockfish_available)
        self._eval_bar_action.setEnabled(self._stockfish_available)
        if not self._stockfish_available:
            self._eval_bar_action.setToolTip(t("Stockfish nicht gefunden.", "Stockfish not found."))
        self._eval_bar_action.toggled.connect(self._toggle_eval_bar)

        theme_menu = view_menu.addMenu(t("Brettfarbe", "Board color"))
        theme_group = QtGui.QActionGroup(self)
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
        QtWidgets.QMessageBox.information(
            self,
            t("Sprache geändert", "Language changed"),
            t(
                "Die Sprache wird beim nächsten Start von Opening Trainer übernommen.",
                "The language will take effect the next time you start Opening Trainer.",
            ),
        )

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

    def _toggle_eval_bar(self, on: bool) -> None:
        self._show_eval_bar = on
        self._eval_settings.setValue("show_eval_bar", on)
        self.eval_bar.setVisible(on and self._stockfish_available)
        if on:
            self._request_eval()
        else:
            self.eval_bar.clear()

    def _ensure_eval_worker(self) -> None:
        if self._eval_bar_thread is not None:
            return
        self._eval_bar_thread = QtCore.QThread(self)
        self._eval_bar_worker = _EvalBarWorker()
        self._eval_bar_worker.moveToThread(self._eval_bar_thread)
        self._evalRequested.connect(self._eval_bar_worker.evaluate)
        self._eval_bar_worker.evaluated.connect(self._on_eval_result)
        self._eval_bar_thread.start()

    def _request_eval(self) -> None:
        """Aktuelle Stellung im Hintergrund bewerten lassen (für die Leiste)."""
        if not self._show_eval_bar or self.training is None:
            return
        self._ensure_eval_worker()
        self._evalRequested.emit(self.training.board.fen())

    def _on_eval_result(self, fen: str, cp: int, mate: int) -> None:
        if not self._show_eval_bar or self.training is None:
            return
        # Nur anzeigen, wenn das Ergebnis zur aktuell gezeigten Stellung passt.
        if self.training.board.fen() == fen:
            self.eval_bar.set_eval(cp, mate)

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
        layout.setContentsMargins(20, 20, 20, 20)
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

        back = QtWidgets.QPushButton(t("‹  Zurück zum Training", "‹  Back to training"))
        back.setObjectName("more")
        back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
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
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(24)

        self.tree_drill_board = BoardView(square_size=70)
        self.tree_drill_board.moveRequested.connect(self._tree_drill_on_move)
        layout.addWidget(self.tree_drill_board, 0, QtCore.Qt.AlignTop)

        side = QtWidgets.QVBoxLayout()
        side.setSpacing(12)
        self.drill_eyebrow = QtWidgets.QLabel(t("BAUM ÜBEN", "TRAIN TREE"))
        self.drill_eyebrow.setObjectName("eyebrow")
        side.addWidget(self.drill_eyebrow)
        self.tree_drill_combo = QtWidgets.QComboBox()
        self.tree_drill_combo.currentIndexChanged.connect(self._drill_combo_changed)
        side.addWidget(self.tree_drill_combo)
        self.drill_manual_check = QtWidgets.QCheckBox(
            t("Gegnerzüge selbst spielen", "Play the opponent's moves myself"))
        self.drill_manual_check.toggled.connect(self._drill_toggle_manual)
        side.addWidget(self.drill_manual_check)
        self.tree_drill_name = self._plain_label("—")
        self.tree_drill_name.setObjectName("name")
        self.tree_drill_name.setWordWrap(True)
        side.addWidget(self.tree_drill_name)
        self.tree_drill_status = self._plain_label("")
        self.tree_drill_status.setObjectName("status")
        self.tree_drill_status.setWordWrap(True)
        self.tree_drill_status.setMinimumHeight(48)
        side.addWidget(self.tree_drill_status)

        btns = QtWidgets.QHBoxLayout()
        sol = QtWidgets.QPushButton(t("Lösung zeigen", "Show solution"))
        sol.clicked.connect(self._tree_drill_solution)
        again = QtWidgets.QPushButton(t("Neu", "Restart"))
        again.clicked.connect(self._tree_drill_restart)
        btns.addWidget(sol)
        btns.addWidget(again)
        side.addLayout(btns)
        side.addStretch(1)

        self._drill_back_index = 9
        self.drill_back_btn = QtWidgets.QPushButton(t("‹  Zurück zum Editor", "‹  Back to editor"))
        self.drill_back_btn.setObjectName("more")
        self.drill_back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(self._drill_back_index))
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
        self._due_session = False
        self.drill_eyebrow.setText(t("BAUM ÜBEN", "TRAIN TREE"))
        self._drill_back_index = 9
        self.drill_back_btn.setText(t("‹  Zurück zum Editor", "‹  Back to editor"))
        self.tree_drill_combo.setVisible(True)
        self.drill_manual_check.setVisible(True)
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

    # ---- „Heute fällig (Bäume)": Spaced Repetition über das ganze Repertoire ----
    def _start_due_session(self) -> None:
        from opening_trainer.tree_session import due_drill_items
        today = date.today()
        items: list = []
        for side_name, color in (("white", chess.WHITE), ("black", chess.BLACK)):
            trees = self.tree_store.by_side(side_name)
            for tree, node_id in due_drill_items(trees, color, self.position_schedule, today):
                items.append((tree, node_id, color))
        self._due_queue = items
        self._due_total = len(items)
        self._due_session = True
        self._drill_manual = False
        self.drill_eyebrow.setText(t("HEUTE FÄLLIG", "DUE TODAY"))
        self._drill_back_index = 0
        self.drill_back_btn.setText(t("‹  Zurück zum Training", "‹  Back to training"))
        self.tree_drill_combo.setVisible(False)
        self.drill_manual_check.setVisible(False)
        self.stack.setCurrentIndex(10)
        self._due_present_current()

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
        self.tree_drill_status.setText(t(
            f"Heute fällig — Stellung {done + 1} von {self._due_total}. Du bist am Zug.",
            f"Due today — position {done + 1} of {self._due_total}. Your move."))

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

    def _tree_drill_on_move(self, from_square: int, to_square: int) -> None:
        tr = self._tree_trainer
        if tr is None or tr.is_finished():
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
            hint = ("  " + t("Richtig wäre:", "Correct would be:") + " " + result.expected_san) if result.expected_san else ""
            self.tree_drill_status.setText(t("Noch nicht.", "Not yet.") + hint)
            return

        if result.kind == "correct":
            passed = not self._tree_drill_wrong
            today = date.today()
            card = self.position_schedule.card_for(epd_before)
            self.position_schedule.set_card(epd_before, schedule_review(card, passed, today))
            self.position_schedule.save(self.position_schedule_path)
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

    def _tree_drill_restart(self) -> None:
        if self._due_session:
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
            "eigene Varianten — oder importierst sie über »Datei → PGN als Repertoire-Bäume "
            "importieren«. Üben: »Bäume üben« (⌘T) oder die Tagessitzung »Heute fällig "
            "(Bäume)« (⌘D).</li>"
            "<li><b>Sprache:</b> Menü »Ansicht → Sprache« (gilt nach Neustart).</li>"
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
            "(“Go → Repertoire editor”, ⌘E) — or import them via “File → Import PGN as "
            "repertoire trees”. Practise with “Train trees” (⌘T) or the daily “Due today "
            "(trees)” session (⌘D).</li>"
            "<li><b>Language:</b> “View → Language” menu (takes effect after restart).</li>"
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
        for keys, slot in [
            (QtGui.QKeySequence(QtCore.Qt.Key_Return), self._kbd_next),
            (QtGui.QKeySequence(QtCore.Qt.Key_Enter), self._kbd_next),
            (QtGui.QKeySequence("L"), self._kbd_solution),
        ]:
            QtGui.QShortcut(keys, self).activated.connect(slot)

    def _kbd_next(self) -> None:
        if self.stack.currentIndex() == 0:
            self._skip()

    def _kbd_solution(self) -> None:
        if self.stack.currentIndex() == 0:
            self._show_solution()

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
            ("_eval_bar_thread", "_eval_bar_worker"),
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

        for attr in ("_tuv_thread", "_eval_bar_thread", "_spar_thread", "_viewer_anal_thread"):
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
        srcs = self._effective_sources()
        path = str(Path(path))
        if path not in srcs:
            srcs.append(path)
        self.settings_store.update(pgn_sources=tuple(srcs))
        self.settings_store.save(self.settings_path)
        before = len(self.lines)
        self.lines = self._load_lines()
        self._migrate_sides_from_groups()
        self._sync_auto_trees()
        self._refill_queue()
        self._refresh_library()
        self._start_next()
        return max(0, len(self.lines) - before)

    def _reset_repertoire(self) -> None:
        if QtWidgets.QMessageBox.question(
            self, t("Repertoire leeren", "Clear repertoire"),
            t("Alle geladenen PGN-Quellen aus der App entfernen? Deine PGN-Dateien "
              "auf der Platte bleiben unberührt — nur die Auswahl in der App wird geleert.",
              "Remove all loaded PGN sources from the app? Your PGN files on disk stay "
              "untouched — only the app's selection is cleared."),
        ) != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        self.settings_store.update(pgn_sources=(), last_pgn_path="", last_pgn_folder="", last_pgn_kind="")
        self.settings_store.save(self.settings_path)
        self.lines = []
        self._sync_auto_trees()
        self._refill_queue()
        self._refresh_library()
        self._start_next()

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
        self.lines = self._load_lines()
        self._sync_auto_trees()
        self._refill_queue()
        self._refresh_library()
        self._start_next()

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

        btns = QtWidgets.QHBoxLayout()
        remove = QtWidgets.QPushButton(t("Ausgewählte entfernen", "Remove selected"))
        remove.clicked.connect(do_remove)
        close = QtWidgets.QPushButton(t("Schließen", "Close"))
        close.clicked.connect(dlg.accept)
        btns.addWidget(remove)
        btns.addStretch(1)
        btns.addWidget(close)
        lay.addLayout(btns)
        dlg.resize(480, 340)
        dlg.exec()

    def _refill_queue(self) -> None:
        due = self.schedule_store.due_lines(self.lines, date.today())
        # Wenn nichts fällig ist, darf man trotzdem üben (alle trainierbaren).
        self._queue = due or [line for line in self.lines if line.moves_uci]

    # --- UI --------------------------------------------------------------

    def _build_ui(self) -> None:
        self.stack = QtWidgets.QStackedWidget()
        self.setCentralWidget(self.stack)
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
        self.setStyleSheet(STYLE)
        self.resize(1000, 700)

    def _build_train_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(page)
        layout.setContentsMargins(26, 26, 26, 26)
        layout.setSpacing(30)

        self.board = BoardView(square_size=74)
        self.board.train_color = self.train_color
        self.board.set_flipped(self.train_color == chess.BLACK)
        self.board.moveRequested.connect(self._on_move)

        self.eval_bar = EvalBar(height=self.board.board_pixels())
        self.eval_bar.setToolTip(t("Stellungsbewertung durch Stockfish.",
                                   "Position evaluation by Stockfish."))
        self.eval_bar.set_flipped(self.train_color == chess.BLACK)
        # Ohne Stockfish bliebe nur ein leerer grauer Streifen -> dann ausblenden.
        self.eval_bar.setVisible(self._show_eval_bar and self._stockfish_available)
        self._add_board_with_eval(layout, self.board, self.eval_bar)

        side = QtWidgets.QVBoxLayout()
        side.setSpacing(12)

        self.eyebrow = QtWidgets.QLabel(t("HEUTE DRAN", "DUE TODAY"))
        self.eyebrow.setObjectName("eyebrow")
        self.name_label = self._plain_label("—")
        self.name_label.setObjectName("name")
        self.name_label.setWordWrap(True)
        self.hint = QtWidgets.QLabel(t(
            "Spiel die Züge deiner Eröffnung auf dem Brett.",
            "Play the moves of your opening on the board.",
        ))
        self.hint.setObjectName("hint")
        self.hint.setWordWrap(True)

        # Nur sichtbar, solange keine Eröffnungen geladen sind (Erst-Start).
        self.sample_btn = QtWidgets.QPushButton(
            t("🎁  Beispiel-Eröffnungen ausprobieren", "🎁  Try the sample openings")
        )
        self.sample_btn.clicked.connect(self._load_sample_lines)
        self.sample_btn.hide()

        self.status = self._plain_label("")
        self.status.setObjectName("status")
        self.status.setWordWrap(True)
        self.status.setMinimumHeight(48)

        # Persönliche Notiz zur aktuellen Eröffnung
        note_row = QtWidgets.QHBoxLayout()
        self.note_label = self._plain_label("")
        self.note_label.setObjectName("note")
        self.note_label.setWordWrap(True)
        self.note_btn = QtWidgets.QPushButton(t("✏ Notiz", "✏ Note"))
        self.note_btn.setObjectName("more")
        self.note_btn.clicked.connect(self._edit_line_note)
        self.note_btn.setEnabled(False)
        note_row.addWidget(self.note_label, 1)
        note_row.addWidget(self.note_btn, 0, QtCore.Qt.AlignTop)

        btn_row = QtWidgets.QHBoxLayout()
        self.solution_btn = QtWidgets.QPushButton(t("Lösung zeigen", "Show solution"))
        self.solution_btn.setToolTip(t("Tastenkürzel: L", "Shortcut: L"))
        self.solution_btn.clicked.connect(self._show_solution)
        self.next_btn = QtWidgets.QPushButton(t("Diese Eröffnung überspringen", "Skip this opening"))
        self.next_btn.setToolTip(t("Tastenkürzel: Eingabetaste", "Shortcut: Enter"))
        self.next_btn.clicked.connect(self._skip)
        btn_row.addWidget(self.solution_btn)
        btn_row.addWidget(self.next_btn)

        self.due_label = QtWidgets.QLabel("")
        self.due_label.setObjectName("due")

        self.fehler_btn = QtWidgets.QPushButton(t("Fehler üben", "Drill mistakes"))
        self.fehler_btn.setObjectName("more")
        self.fehler_btn.clicked.connect(self._start_drill)
        self.fehler_btn.hide()

        self.spar_open_btn = QtWidgets.QPushButton(
            t("♟  Gegen Stockfish weiterspielen", "♟  Play on against Stockfish")
        )
        self.spar_open_btn.setObjectName("more")
        self.spar_open_btn.clicked.connect(self._open_sparring)
        self.spar_open_btn.setEnabled(False)

        self.explorer_open_btn = QtWidgets.QPushButton(
            t("🔎  Im Lichess-Explorer ansehen", "🔎  Open in Lichess explorer")
        )
        self.explorer_open_btn.setObjectName("more")
        self.explorer_open_btn.clicked.connect(self._open_explorer)
        self.explorer_open_btn.setEnabled(False)

        more_btn = QtWidgets.QPushButton(t("Alle Eröffnungen ansehen …", "Browse all openings …"))
        more_btn.setObjectName("more")
        more_btn.clicked.connect(self._open_library)

        side.addWidget(self.eyebrow)
        side.addWidget(self.name_label)
        side.addWidget(self.hint)
        side.addWidget(self.sample_btn, 0, QtCore.Qt.AlignLeft)
        side.addSpacing(8)
        side.addLayout(btn_row)
        side.addWidget(self.status)
        side.addLayout(note_row)
        side.addStretch(1)
        side.addWidget(self.due_label)
        side.addWidget(self.spar_open_btn, 0, QtCore.Qt.AlignLeft)
        side.addWidget(self.explorer_open_btn, 0, QtCore.Qt.AlignLeft)
        side.addWidget(self.fehler_btn, 0, QtCore.Qt.AlignLeft)
        side.addWidget(more_btn, 0, QtCore.Qt.AlignLeft)

        side_widget = QtWidgets.QWidget()
        side_widget.setLayout(side)
        side_widget.setFixedWidth(340)
        layout.addWidget(side_widget, 1)
        return page

    def _build_library_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        outer = QtWidgets.QVBoxLayout(page)
        outer.setContentsMargins(26, 22, 26, 22)
        outer.setSpacing(12)

        header = QtWidgets.QHBoxLayout()
        back = QtWidgets.QPushButton(t("‹  Zurück zum Training", "‹  Back to training"))
        back.setObjectName("more")
        back.clicked.connect(self._close_library)
        title = QtWidgets.QLabel(t("Deine Eröffnungen", "Your openings"))
        title.setObjectName("name")
        self.stats_btn = QtWidgets.QPushButton(t("Auswertung", "Analysis"))
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
        self.train_one_btn = QtWidgets.QPushButton(t("Üben", "Train"))
        self.train_one_btn.setObjectName("primary")
        self.train_one_btn.clicked.connect(self._train_selected_library)
        for btn in (self.assign_white_btn, self.assign_black_btn, self.assign_none_btn, self.train_one_btn):
            btn.setEnabled(False)
        action_bar.addWidget(self.assign_white_btn)
        action_bar.addWidget(self.assign_black_btn)
        action_bar.addWidget(self.assign_none_btn)
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
        back = QtWidgets.QPushButton(t("‹  Zurück zum Training", "‹  Back to training"))
        back.setObjectName("more")
        back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        header.addWidget(back, 0, QtCore.Qt.AlignLeft)
        header.addStretch(1)
        # Navigation zu Fortschritt / Partien / Repertoire-Prüfung steckt jetzt im
        # Menü „Gehe zu" (⌘4/⌘5/⌘6) — keine doppelten Knöpfe mehr hier.
        outer.addLayout(header)

        title = QtWidgets.QLabel(t("Auswertung", "Analysis"))
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
        back = QtWidgets.QPushButton(t("‹  Zurück zur Auswertung", "‹  Back to analysis"))
        back.setObjectName("more")
        back.clicked.connect(lambda: self.stack.setCurrentIndex(2))
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
        jobs = []
        for line in self.lines:
            if not getattr(line, "moves_uci", None):
                continue
            side = self._side_of_line(line)
            if side == "white":
                jobs.append((line, chess.WHITE))
            elif side == "black":
                jobs.append((line, chess.BLACK))
        return jobs

    def _start_tuv(self) -> None:
        if self._tuv_thread is not None:
            return
        jobs = self._tuv_jobs()
        if not jobs:
            self.tuv_status.setText(t(
                "Keine zugeordneten Linien. Ordne erst Eröffnungen einem Repertoire zu.",
                "No assigned lines. First assign some openings to a repertoire.",
            ))
            return
        self.tuv_list.clear()
        self.tuv_start_btn.setEnabled(False)
        self.tuv_cancel_btn.setVisible(True)
        self.tuv_status.setText(t(f"Starte Prüfung von {len(jobs)} Linien …", f"Checking {len(jobs)} lines …"))

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
            f"{len(results)} Linien mit Auffälligkeiten ({total_issues} insgesamt, "
            f"davon {patzer} Patzer). Klick eine Linie zum Üben.",
            f"{len(results)} lines with findings ({total_issues} total, "
            f"{patzer} blunders). Click a line to train it.",
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
        line = item.data(QtCore.Qt.UserRole)
        if line is None or not getattr(line, "moves_uci", None):
            return
        self.stack.setCurrentIndex(0)
        self._load_line(line)
        self.eyebrow.setText(t("ÜBEN", "TRAIN"))

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
        back = QtWidgets.QPushButton(t("‹  Zurück zum Training", "‹  Back to training"))
        back.setObjectName("more")
        back.clicked.connect(lambda: self.stack.setCurrentIndex(0))

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
        back = QtWidgets.QPushButton(t("‹  Zurück zur Auswertung", "‹  Back to analysis"))
        back.setObjectName("more")
        back.clicked.connect(lambda: self.stack.setCurrentIndex(2))
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
        assigned = [
            l for l in self.lines
            if l.moves_uci and self._side_of_line(l) in ("white", "black")
        ]
        self._progress_rows = []
        for line in assigned:
            s = self.stats_store.stats_for_line(source_name=line.source_name, line_name=line.name)
            self._progress_rows.append(
                (line, s.attempts, s.accuracy, mastery_bucket(s.attempts, s.accuracy))
            )
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
        counts = summarize_mastery([(a, acc) for _, a, acc, _ in self._progress_rows])
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
            for line, attempts, accuracy, _ in sorted(
                (r for r in rows if r[3] == "wackelt"), key=lambda r: r[2]
            ):
                self._add_progress_row(line, t(
                    f"🟡 wackelt · Trefferquote {round(accuracy * 100)} % · {attempts} Versuche",
                    f"🟡 shaky · accuracy {round(accuracy * 100)}% · {attempts} attempts",
                ))
                shown += 1
        if show_neu:
            for line, _, _, _ in (r for r in rows if r[3] == "neu"):
                self._add_progress_row(line, t("⚪ neu · noch nie geübt", "⚪ new · never trained"))
                shown += 1
        if show_sitzt:
            for line, attempts, accuracy, _ in sorted(
                (r for r in rows if r[3] == "sitzt"), key=lambda r: -r[2]
            ):
                self._add_progress_row(line, t(
                    f"🟢 sitzt · Trefferquote {round(accuracy * 100)} % · {attempts} Versuche",
                    f"🟢 solid · accuracy {round(accuracy * 100)}% · {attempts} attempts",
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

    def _add_progress_row(self, line, sub_text: str) -> None:
        item = QtWidgets.QListWidgetItem()
        item.setData(QtCore.Qt.UserRole, line)
        widget = QtWidgets.QWidget()
        widget.setObjectName("libraryrow")
        box = QtWidgets.QVBoxLayout(widget)
        box.setContentsMargins(14, 9, 14, 9)
        box.setSpacing(2)
        name = self._plain_label(self._display_name(line))
        name.setObjectName("rowname")
        sub = QtWidgets.QLabel(sub_text)
        sub.setObjectName("rowsub")
        box.addWidget(name)
        box.addWidget(sub)
        item.setSizeHint(widget.sizeHint())
        self.progress_list.addItem(item)
        self.progress_list.setItemWidget(item, widget)

    def _train_from_progress(self, item: QtWidgets.QListWidgetItem) -> None:
        line = item.data(QtCore.Qt.UserRole)
        if line is None or not getattr(line, "moves_uci", None):
            return
        self.stack.setCurrentIndex(0)
        self._load_line(line)
        self.eyebrow.setText(t("ÜBEN", "TRAIN"))

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
        reset = QtWidgets.QPushButton(t("Neu ab Eröffnung", "Restart from opening"))
        reset.clicked.connect(self._open_explorer)
        token_btn = QtWidgets.QPushButton(t("🔑 Lichess-Token", "🔑 Lichess token"))
        token_btn.setObjectName("more")
        token_btn.clicked.connect(self._edit_lichess_token)
        nav.addWidget(self.explorer_undo_btn)
        nav.addWidget(reset)
        nav.addStretch(1)
        nav.addWidget(token_btn)

        back = QtWidgets.QPushButton(t("‹  Zurück zum Training", "‹  Back to training"))
        back.setObjectName("more")
        back.clicked.connect(lambda: self.stack.setCurrentIndex(0))

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

    def _explorer_undo(self) -> None:
        if self._explorer_board is None:
            return
        if len(self._explorer_board.move_stack) <= self._explorer_seed_plies:
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
            and len(self._explorer_board.move_stack) > self._explorer_seed_plies
        )
        self.explorer_undo_btn.setEnabled(can_undo)

    # ---- Echte Partien auswerten (Repertoire-Abgleich) -----------------
    def _build_game_review_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        outer = QtWidgets.QVBoxLayout(page)
        outer.setContentsMargins(26, 22, 26, 22)
        outer.setSpacing(12)

        header = QtWidgets.QHBoxLayout()
        back = QtWidgets.QPushButton(t("‹  Zurück zur Auswertung", "‹  Back to analysis"))
        back.setObjectName("more")
        back.clicked.connect(lambda: self.stack.setCurrentIndex(2))
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
                self._load_games_from_path(path)
        # Ohne zugeordnetes Repertoire ist der Abgleich sinnlos (alles „ungedeckt") ->
        # actionable Hinweis statt irreführender Zähler. Zuletzt setzen, damit das
        # Auto-Laden ihn nicht überschreibt.
        if not any(self._side_of_line(l) for l in self.lines):
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
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, t("PGN deiner Partien laden", "Load your games PGN"), "",
            t("PGN-Dateien (*.pgn);;Alle Dateien (*)", "PGN files (*.pgn);;All files (*)")
        )
        if not path:
            return
        self._eval_settings.setValue("games_pgn_path", path)
        self._load_games_from_path(path)

    def _load_games_from_path(self, path: str) -> None:
        if not self._player_name.strip() or not Path(path).exists():
            return
        white_book = build_repertoire_book(
            [l.moves_uci for l in self.lines if l.moves_uci and self._side_of_line(l) == "white"],
            chess.WHITE,
        )
        black_book = build_repertoire_book(
            [l.moves_uci for l in self.lines if l.moves_uci and self._side_of_line(l) == "black"],
            chess.BLACK,
        )
        uname = self._player_name.strip().lower()
        results = []
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                while True:
                    game = chess.pgn.read_game(fh)
                    if game is None:
                        break
                    results.append(self._review_one_game(game, uname, white_book, black_book))
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
        line = None
        if review.status == "deviated":
            line = self._find_line_through_deviation(moves, review.deviation.ply, color)
        return {
            "status": review.status, "review": review, "opp": opp, "result": result,
            "line": line, "moves": moves, "color": color,
        }

    def _find_line_through_deviation(self, moves: list[str], ply: int, color: chess.Color):
        board = chess.Board()
        for i in range(ply):
            try:
                board.push(chess.Move.from_uci(moves[i]))
            except ValueError:
                return None
        target = board.epd()
        side_str = "white" if color == chess.WHITE else "black"
        for line in self.lines:
            if not line.moves_uci or self._side_of_line(line) != side_str:
                continue
            bb = chess.Board()
            for uci in line.moves_uci:
                if bb.turn == color and bb.epd() == target:
                    return line
                try:
                    bb.push(chess.Move.from_uci(uci))
                except ValueError:
                    break
        return None

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

        self.viewer_train_btn = QtWidgets.QPushButton(t("Diese Linie üben", "Train this line"))
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
        self._viewer_line = payload.get("line")
        self.viewer_board.set_flipped(self._viewer_color == chess.BLACK)
        color_word = self._tcolor(self._viewer_color)
        me = self._player_name.strip() or t("Du", "You")
        self.viewer_title.setText(t(
            f"{me} ({color_word})  gegen  {payload.get('opp', '?')}     ·     {payload.get('result', '')}",
            f"{me} ({color_word})  against  {payload.get('opp', '?')}     ·     {payload.get('result', '')}",
        ))
        self.viewer_train_btn.setVisible(self._viewer_line is not None)
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

    def _viewer_train(self) -> None:
        if self._viewer_line is None or not getattr(self._viewer_line, "moves_uci", None):
            return
        self.stack.setCurrentIndex(0)
        self._load_line(self._viewer_line)
        self.eyebrow.setText(t("ÜBEN", "TRAIN"))

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
        self._drill = True
        self._drill_queue = []  # genau diese eine Stellung
        self.stack.setCurrentIndex(0)
        self._drill_current = problem
        self._load_problem(problem)

    def _refresh_stats(self) -> None:
        overview = overall_progress(self.stats_store.events)
        problems = self._collect_error_problems()
        self.stats_list.clear()

        if overview.session_count == 0:
            self.stats_overview.setText("")
            self.stats_sub.setText("")
            self.stats_empty.setVisible(True)
            self.stats_list.setVisible(False)
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
            return
        self.stats_sub.setText(t(
            f"Diese {len(problems)} Stellungen sitzen noch nicht — klick eine an, um sie gezielt zu üben:",
            f"These {len(problems)} positions aren't solid yet — click one to drill it:",
        ))
        for problem in problems:
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.UserRole, problem)
            row = self._stats_error_row(problem)
            item.setSizeHint(row.sizeHint())
            self.stats_list.addItem(item)
            self.stats_list.setItemWidget(item, row)

    # --- Trainings-Loop --------------------------------------------------

    def _update_due_label(self) -> None:
        due = len(self.schedule_store.due_lines(self.lines, date.today()))
        self.due_label.setText(t(
            f"Heute zu wiederholen: {due} " + ("Eröffnung" if due == 1 else "Eröffnungen"),
            f"Due today: {due} " + ("opening" if due == 1 else "openings"),
        ))

    def _start_next(self) -> None:
        self._update_error_count()
        if not self.lines:
            self.eyebrow.setText("")
            self.name_label.setText(t("Noch keine Eröffnungen", "No openings yet"))
            self.hint.setText(t(
                "Lade dein eigenes Repertoire über „Alle Eröffnungen ansehen …“ → „PGN laden …“ — "
                "oder probier die App sofort mit drei Beispiel-Eröffnungen aus.",
                "Load your own repertoire via “Browse all openings …” → “Load PGN …” — "
                "or try the app right away with three sample openings.",
            ))
            self.due_label.setText("")
            self.status.setText("")
            self.solution_btn.setVisible(False)   # im Leerzustand keine funktionslosen Knöpfe
            self.next_btn.setVisible(False)
            self.sample_btn.setVisible(True)
            self.board.set_board(chess.Board())
            return
        self.sample_btn.setVisible(False)
        if not self._queue:
            self.eyebrow.setText("")
            self.name_label.setText(t("Alles erledigt 🎉", "All done 🎉"))
            self.hint.setText(t(
                "Für heute ist nichts mehr fällig. Schau morgen wieder vorbei.",
                "Nothing more is due today. Come back tomorrow.",
            ))
            self.status.setText("")
            self.solution_btn.setVisible(False)
            self.next_btn.setVisible(False)
            self.board.set_board(chess.Board())
            self._update_due_label()
            return
        self.eyebrow.setText(t("HEUTE DRAN", "DUE TODAY"))
        self._load_line(self._queue.pop(0))

    def _train_color_for(self, line):
        """Farbe, in der eine Eröffnung geübt wird: aus ihrer Repertoire-Seite.
        Ohne Zuordnung gilt die globale Voreinstellung."""
        side = self._side_of_line(line)
        if side == "white":
            return chess.WHITE
        if side == "black":
            return chess.BLACK
        return self.train_color

    def _load_line(self, line) -> None:
        # Normales Training beginnt -> evtl. laufenden Fehler-Drill beenden,
        # sonst greifen Lösung/Züge noch auf die alte Drill-Stellung zu.
        self._drill = False
        self._drill_current = None
        self._drill_board = None
        self.current_line = line
        self._had_wrong = False
        self.solution_btn.setVisible(True)
        self.next_btn.setVisible(True)
        color = self._train_color_for(line)
        self.board.train_color = color
        self.board.set_flipped(color == chess.BLACK)
        self.eval_bar.set_flipped(color == chess.BLACK)
        self.eval_bar.clear()
        self.training = TrainingState(line, train_color=color)
        last = self._parse_last(self.training.last_move_uci)
        self.board.set_board(self.training.board, last_move=last)
        self.name_label.setText(self._display_name(line))
        side = self._tcolor(color)
        self.hint.setText(t(
            f"Du spielst {side}. Zieh die richtigen Züge auf dem Brett.",
            f"You play {side}. Make the correct moves on the board.",
        ))
        self.status.setText("")
        self.next_btn.setText(t("Überspringen", "Skip"))
        self.solution_btn.setEnabled(True)
        self.spar_open_btn.setEnabled(True)
        self.explorer_open_btn.setEnabled(True)
        self._refresh_note_display()
        self._update_due_label()
        self._update_error_count()
        self._request_eval()

    def _refresh_note_display(self) -> None:
        """Zeigt die Notiz der aktuellen Eröffnung (oder einen Hinweis)."""
        line = self.current_line
        self.note_btn.setEnabled(line is not None)
        if line is None:
            self.note_label.setText("")
            return
        note = self.line_notes.note_of(line.source_name, line.name)
        self.note_label.setText(f"📝 {note}" if note else t("Keine Notiz zu dieser Eröffnung.", "No note for this opening."))

    def _edit_line_note(self) -> None:
        line = self.current_line
        if line is None:
            return
        current = self.line_notes.note_of(line.source_name, line.name)
        text, ok = QtWidgets.QInputDialog.getMultiLineText(
            self,
            t("Notiz zur Eröffnung", "Note for the opening"),
            t(f"Merktext zu »{self._display_name(line)}«:", f"Note for »{self._display_name(line)}«:"),
            current,
        )
        if not ok:
            return
        self.line_notes.set_note(line.source_name, line.name, text)
        self.line_notes.save(self.notes_path)
        self._refresh_note_display()
        if self.stack.currentIndex() == 1:
            self._refresh_library()

    @staticmethod
    def _parse_last(uci: str | None) -> tuple[int, int] | None:
        if not uci:
            return None
        try:
            move = chess.Move.from_uci(uci)
        except ValueError:
            return None
        return (move.from_square, move.to_square)

    def _on_move(self, from_square: int, to_square: int) -> None:
        if self._drill:
            self._drill_move(from_square, to_square)
            return
        if self.training is None:
            return
        fen_before = self.training.board.fen()
        result = self.training.play_user_move_uci(chess.Move(from_square, to_square).uci())
        if result.kind in ("correct", "wrong") and self.current_line is not None:
            self.stats_store.add_event(
                source_name=self.current_line.source_name,
                line_name=self.current_line.name,
                fen_before=fen_before,
                expected_san=result.expected_san,
                played_san=result.played_san,
                correct=result.kind == "correct",
            )
            self.stats_store.save(self.stats_path)
        if result.kind == "wrong":
            self._had_wrong = True
            self.board.flash_wrong(to_square)
            self._show_deviation_feedback(
                fen_before,
                result.expected_san,
                chess.Move(from_square, to_square).uci(),
            )
            return
        if result.kind == "correct":
            last = self._parse_last(result.last_move_uci)
            self.board.set_board(self.training.board, last_move=last)

            def done() -> None:
                if self.training.is_finished():
                    self._finish_line()
                else:
                    self.status.setText(t("✓ Richtig — weiter, du bist dran.",
                                          "✓ Correct — keep going, your move."))
                self._request_eval()

            if last is not None:
                self.board.animate(last[0], last[1], done)
            else:
                done()

    def _wrong_fallback(self) -> str:
        return t(
            "Nicht ganz — das war nicht der Zug aus deiner Eröffnung. "
            "Versuch's noch einmal oder „Lösung zeigen“.",
            "Not quite — that wasn't the move from your opening. "
            "Try again or use ‘Show solution’.",
        )

    def _get_eval_engine(self):
        """Persistente Stockfish-Instanz fürs Üben (einmal starten, wiederverwenden).

        Liefert ``None``, wenn Stockfish nicht gefunden wird — dann bleibt es
        bei der einfachen Rückmeldung.
        """
        state = getattr(self, "_eval_engine", "unset")
        if state != "unset":
            return state
        try:
            import chess.engine
            from qt_app.engine import find_stockfish
            sf = find_stockfish()
            self._eval_engine = (
                chess.engine.SimpleEngine.popen_uci(str(sf)) if sf is not None else None
            )
        except Exception:  # noqa: BLE001
            self._eval_engine = None
        return self._eval_engine

    def _show_deviation_feedback(self, fen_before: str, expected_san: str, played_uci: str) -> None:
        """„War mein Zug gut?" — beurteilt einen abweichenden Zug mit Stockfish."""
        engine = self._get_eval_engine()
        if engine is None or not expected_san:
            self.status.setText(self._wrong_fallback())
            return
        self.status.setText(t("Prüfe deinen Zug mit Stockfish …", "Checking your move with Stockfish …"))
        self.status.repaint()
        try:
            import chess.engine
            from qt_app.engine import judge_user_move
            verdict = judge_user_move(
                engine, fen_before, expected_san, played_uci,
                chess.engine.Limit(depth=12),
            )
        except Exception:  # noqa: BLE001
            verdict = None
        if verdict is None:
            self.status.setText(self._wrong_fallback())
            return
        x = verdict["expected_san"]
        cat = verdict["category"]
        if cat == "gleichwertig":
            self.status.setText(t(
                f"✓ Auch gut — dein Zug ist gleichwertig zu {x}. "
                f"Zum Einprägen spiel trotzdem deinen Repertoire-Zug {x}.",
                f"✓ Fine too — your move is as good as {x}. "
                f"But play your repertoire move {x} to memorize it.",
            ))
        elif cat == "ungenau":
            worse = abs(verdict["loss_cp"]) / 100
            self.status.setText(t(
                f"⚠ Etwas ungenauer als dein Repertoire-Zug {x} "
                f"(≈ {worse:.1f} schlechter). Spiel {x}.",
                f"⚠ A bit worse than your repertoire move {x} "
                f"(≈ {worse:.1f} worse). Play {x}.",
            ))
        else:
            self.status.setText(t(
                f"⛔ Das schwächt deine Stellung — {x} ist klar besser. Spiel {x}.",
                f"⛔ That weakens your position — {x} is clearly better. Play {x}.",
            ))

    def _finish_line(self) -> None:
        self.status.setText(t("Geschafft! ✓  Die ganze Eröffnung saß.", "Done! ✓  You nailed the whole opening."))
        self.solution_btn.setEnabled(False)
        self.next_btn.setText(t("Nächste Eröffnung", "Next opening"))
        if self.current_line is not None:
            card = self.schedule_store.card_for(self.current_line.source_name, self.current_line.name)
            self.schedule_store.set_card(
                self.current_line.source_name,
                self.current_line.name,
                schedule_review(card, not self._had_wrong, date.today()),
            )
            self.schedule_store.save(self.schedule_path)
        self._update_due_label()
        self._update_error_count()

    def _show_solution(self) -> None:
        if self._drill and self._drill_current is not None:
            move = chess.Move.from_uci(self._drill_current["expected_uci"])
            self.board.show_solution(move.from_square, move.to_square)
            self.status.setText(t(f"Lösung: {self._drill_current['expected_san']}", f"Solution: {self._drill_current['expected_san']}"))
            return
        if self.training is None:
            return
        sol = self.training.expected_solution()
        if sol is None:
            self.status.setText(t("Diese Eröffnung ist zu Ende.", "This opening is finished."))
            return
        self._had_wrong = True
        move = chess.Move.from_uci(sol.uci)
        self.board.show_solution(move.from_square, move.to_square)
        self.status.setText(t(f"Lösung: {sol.san} — spiel sie jetzt selbst nach (grün markiert).",
                              f"Solution: {sol.san} — now play it yourself (shown in green)."))

    def _skip(self) -> None:
        if self._drill:
            self._next_problem()
            return
        self._start_next()

    # --- Fehler-Drill ----------------------------------------------------

    def _collect_error_problems(self) -> list:
        """Alle offenen Fehlerstellungen (letzter Versuch falsch) über alle
        Eröffnungen, häufigste zuerst. Nutzt das getestete „offene Fehler"-
        Modell und prüft, dass der erwartete Zug in der Stellung spielbar ist."""
        problems = []
        seen = set()
        for line in self.lines:
            for pos in self.stats_store.error_positions_for_line(
                source_name=line.source_name, line_name=line.name
            ):
                key = (pos.fen_before, pos.expected_san)
                if key in seen or not pos.expected_san:
                    continue
                try:
                    board = chess.Board(pos.fen_before)
                except ValueError:
                    continue
                expected_uci = None
                for move in board.legal_moves:
                    if board.san(move) == pos.expected_san:
                        expected_uci = move.uci()
                        break
                if expected_uci is None:
                    continue
                seen.add(key)
                problems.append(
                    {
                        "fen": pos.fen_before,
                        "expected_uci": expected_uci,
                        "expected_san": pos.expected_san,
                        "played": pos.last_played_san,
                        "name": line.name,
                        "source": line.source_name,
                        "line": line.name,
                        "count": pos.wrong_count,
                    }
                )
        problems.sort(key=lambda p: -p["count"])
        return problems

    def _update_error_count(self) -> None:
        if not hasattr(self, "fehler_btn"):
            return
        count = len(self._collect_error_problems())
        self.fehler_btn.setText(t(f"Fehler üben  ({count})", f"Drill mistakes  ({count})"))
        self.fehler_btn.setVisible(count > 0)

    def _start_drill(self) -> None:
        problems = self._collect_error_problems()
        if not problems:
            self.status.setText(t("Keine offenen Fehler — stark! 💪", "No open mistakes — great! 💪"))
            return
        self._drill = True
        self._drill_queue = problems
        self.stack.setCurrentIndex(0)
        self._next_problem()

    def _next_problem(self) -> None:
        if not self._drill_queue:
            self._finish_drill()
            return
        self._drill_current = self._drill_queue.pop(0)
        self._load_problem(self._drill_current)

    def _load_problem(self, problem: dict) -> None:
        board = chess.Board(problem["fen"])
        self._drill_board = board
        turn = board.turn
        self.board.train_color = turn
        self.board.set_flipped(turn == chess.BLACK)
        self.board.set_board(board)
        self.eyebrow.setText(t("FEHLER ÜBEN", "DRILL MISTAKES"))
        self.name_label.setText(self._tname(problem["name"]))
        self.hint.setText(t(
            "Welcher Zug ist hier richtig? Den hattest du hier schon einmal verpasst.",
            "Which move is correct here? You missed it here once before.",
        ))
        remaining = len(self._drill_queue) + 1
        self.status.setText(t(f"Noch {remaining} Fehler", f"{remaining} mistakes left"))
        self.next_btn.setText(t("Überspringen", "Skip"))
        self.solution_btn.setEnabled(True)

    def _drill_move(self, from_square: int, to_square: int) -> None:
        problem = self._drill_current
        board = self._drill_board
        if problem is None or board is None:
            return
        move = chess.Move(from_square, to_square)
        if move not in board.legal_moves:
            promo = chess.Move(from_square, to_square, promotion=chess.QUEEN)
            if promo in board.legal_moves:
                move = promo
        if move not in board.legal_moves:
            self.board.flash_wrong(to_square)
            self.status.setText(t("Das ist hier kein gültiger Zug.", "That's not a legal move here."))
            return

        correct = move.uci() == problem["expected_uci"]
        self.stats_store.add_event(
            source_name=problem["source"],
            line_name=problem["line"],
            fen_before=problem["fen"],
            expected_san=problem["expected_san"],
            played_san=board.san(move),
            correct=correct,
        )
        self.stats_store.save(self.stats_path)

        if correct:
            board.push(move)
            self.board.set_board(board, last_move=(from_square, to_square))
            self.status.setText(t("Richtig! ✓", "Correct! ✓"))
            self.board.animate(from_square, to_square, self._next_problem)
        else:
            self.board.flash_wrong(to_square)
            self.status.setText(t("Nicht ganz — versuch's noch einmal oder „Lösung zeigen“.", "Not quite — try again or use ‘Show solution’."))

    def _finish_drill(self) -> None:
        self._drill = False
        self._drill_current = None
        self._drill_board = None
        self.board.train_color = self.train_color
        self.board.set_flipped(self.train_color == chess.BLACK)
        # zurück in den normalen Übungsfluss
        self._refill_queue()
        self._start_next()
        self.status.setText(t("Fehler-Training fertig! ✓  Gut gemacht.", "Mistake drill done! ✓  Well done."))
        self._update_error_count()

    # --- Eröffnungs-Liste („Mehr…") --------------------------------------

    def _due_text(self, line) -> str:
        if not line.moves_uci:
            return t("keine Züge", "no moves")
        card = self.schedule_store.card_for(line.source_name, line.name)
        if is_new(card):
            return t("neu", "new")
        try:
            due = date.fromisoformat(card.due)
        except ValueError:
            return t("neu", "new")
        delta = (due - date.today()).days
        if delta <= 0:
            return t("heute fällig", "due today")
        if delta == 1:
            return t("morgen fällig", "due tomorrow")
        return t(f"fällig in {delta} Tagen", f"due in {delta} days")

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
        parts = []
        group = self._group_text_for_line(line)
        if group:
            parts.append(group)
        side = self._side_of_line(line)
        if side:
            parts.append(t("Weiß", "White") if side == "white" else t("Schwarz", "Black"))
        parts.append(self._due_text(line))
        stats = self.stats_store.stats_for_line(source_name=line.source_name, line_name=line.name)
        if stats.attempts > 0:
            parts.append(t(f"Trefferquote {round(stats.accuracy * 100)} %", f"accuracy {round(stats.accuracy * 100)}%"))
        sub = QtWidgets.QLabel("  ·  ".join(parts))
        sub.setObjectName("rowsub")
        box.addWidget(name)
        box.addWidget(sub)
        return widget

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
        if not self.lines:
            self.library_empty.setVisible(True)
            self.library_list.setVisible(False)
            return
        self.library_empty.setVisible(False)
        self.library_list.setVisible(True)
        lines = sorted(self._filtered_lines(), key=self._category_sort_key)
        if not lines and self.search_query:
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

    def _migrate_sides_from_groups(self) -> None:
        """Übernimmt einmalig die vorhandene Gruppen-Zuordnung (Tkinter-Daten) in
        das Pro-Eröffnung-Modell, damit das bestehende Repertoire erhalten bleibt."""
        if self.opening_sides.sides:
            return
        rep = self.repertoire_store.repertoire
        white = {(l.source_name, l.name) for l in rep.lines_for_side(SIDE_WHITE, self.lines)}
        black = {(l.source_name, l.name) for l in rep.lines_for_side(SIDE_BLACK, self.lines)}
        changed = False
        for line in self.lines:
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
        for line in self.lines:
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
        for line in self.lines:
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
        side = self.opening_sides.side_of(line.source_name, line.name)
        return side if side in ("white", "black") else None

    def _on_search(self, text: str) -> None:
        self.search_query = text.strip().casefold()
        self._refresh_library()

    def _filtered_lines(self) -> list:
        if self._side_filter is None:
            lines = self.lines
        elif self._side_filter in ("white", "black"):
            lines = [l for l in self.lines if self._side_of_line(l) == self._side_filter]
        else:
            lines = [l for l in self.lines if self._side_of_line(l) is None]
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
        lines = [l for l in self._filtered_lines() if l.moves_uci]
        if not lines:
            return
        self._queue = list(lines)
        self.stack.setCurrentIndex(0)
        self._start_next()
        side = t("WEISS-REPERTOIRE", "WHITE REPERTOIRE") if self._side_filter == "white" else t("SCHWARZ-REPERTOIRE", "BLACK REPERTOIRE")
        self.eyebrow.setText(side)

    def _open_library(self) -> None:
        self._refresh_library()
        self.stack.setCurrentIndex(1)

    def _close_library(self) -> None:
        self.stack.setCurrentIndex(0)

    def _train_from_library(self, item: QtWidgets.QListWidgetItem) -> None:
        line = item.data(QtCore.Qt.UserRole)
        if line is None or not getattr(line, "moves_uci", None):
            return
        self.stack.setCurrentIndex(0)
        self._load_line(line)
        self.eyebrow.setText(t("ÜBEN", "TRAIN"))

    def _selected_library_line(self):
        items = self.library_list.selectedItems()
        return items[0].data(QtCore.Qt.UserRole) if items else None

    def _on_library_selection(self) -> None:
        has = self._selected_library_line() is not None
        for btn in (self.assign_white_btn, self.assign_black_btn, self.assign_none_btn, self.train_one_btn):
            btn.setEnabled(has)

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
        self.lines = lines
        self.settings_store.update(
            last_pgn_path=str(path),
            last_pgn_folder=str(path.parent),
            last_pgn_kind="file",
        )
        self.settings_store.save(self.settings_path)
        for line in lines:
            side = self._SAMPLE_SIDES.get(line.name)
            if side and self.opening_sides.side_of(line.source_name, line.name) is None:
                self.opening_sides.set_side(line.source_name, line.name, side)
        self.opening_sides.save(self.sides_path)
        self._sync_auto_trees()
        self._refill_queue()
        self._refresh_library()
        self._start_next()

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
            f"{added} Eröffnungen hinzugefügt — {len(self.lines)} insgesamt. Klick eine an, um sie zu üben.",
            f"Added {added} openings — {len(self.lines)} in total. Click one to train it."))

    def _ask_and_assign_side(self, source_name: str) -> None:
        """Fragt beim Laden einer Datei einmal nach der Spielerfarbe (Vorschlag aus
        dem Dateinamen) und ordnet alle noch nicht zugeordneten Eröffnungen dieser
        Datei der gewählten Seite zu. Sind bereits alle zugeordnet, wird nicht gefragt."""
        file_lines = [l for l in self.lines if l.source_name == source_name]
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
        unassigned = sum(1 for l in self.lines if self._side_of_line(l) is None)
        msg_de = f"{added} Eröffnungen aus dem Ordner hinzugefügt — {len(self.lines)} insgesamt."
        msg_en = f"Added {added} openings from the folder — {len(self.lines)} in total."
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
