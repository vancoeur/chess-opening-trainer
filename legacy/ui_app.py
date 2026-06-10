from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from pathlib import Path

import chess

from opening_trainer.app_mode import AppMode
from opening_trainer.board_geometry import BoardGeometry
from legacy.board_widget import BoardWidget
from opening_trainer.pgn_loader import OpeningLine, load_pgn_file, load_pgn_folder
from opening_trainer.training_state import TrainingState
from opening_trainer.stats_store import StatsStore
from opening_trainer.stats_export import export_training_events_csv
from opening_trainer.repertoire import RepertoireCategory, SIDE_BLACK, SIDE_NONE, SIDE_WHITE
from opening_trainer.repertoire_store import RepertoireStore
from opening_trainer.training_run import TrainingRun
from opening_trainer.schedule_store import ScheduleStore
from opening_trainer.scheduler import review as schedule_review, is_new
from datetime import date
from opening_trainer.error_session import (
    finished_session_message,
    loaded_session_message,
    session_index_for_selected_problem,
    session_mode_text,
    WrongMoveSession,
    solved_session_message,
    wrong_move_history_text,
)
from opening_trainer.settings_store import SettingsStore
from opening_trainer.session_log import overall_progress, summarize_training_sessions
from opening_trainer.ui_state import UiStateInput, button_states, tab_for_mode, TAB_ERRORS, TAB_LIBRARY


class OpeningTrainerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("Opening Trainer 1.0")
        self.resizable(True, True)
        self.minsize(1080, 860)

        self.stats_path = Path("data/training_stats.json")
        self.stats_store = StatsStore.load(self.stats_path)
        self.settings_path = Path("data/settings.json")
        self.settings_store = SettingsStore.load(self.settings_path)
        self.repertoire_path = Path("data/repertoire.json")
        self.repertoire_store = RepertoireStore.load(self.repertoire_path)
        self.schedule_path = Path("data/schedule.json")
        self.schedule_store = ScheduleStore.load(self.schedule_path)
        self._review_active = False

        if self.settings_store.settings.window_geometry:
            self.geometry(self.settings_store.settings.window_geometry)

        self.lines: list[OpeningLine] = []
        self.training: TrainingState | None = None
        self.current_line: OpeningLine | None = None
        self.selected_square: chess.Square | None = None
        self.train_color = chess.BLACK if self.settings_store.settings.train_color == "black" else chess.WHITE
        self.current_error_positions = []
        self.error_panel_active = False
        self.error_training_active = False
        self.active_error_position = None
        self.error_session: WrongMoveSession | None = None
        self.training_run: TrainingRun | None = None
        self._set_label = ""
        self._set_line_finished = False
        self._set_line_had_wrong = False
        self.mode = AppMode.IDLE
        self.variant_sort_column = ""
        self.variant_sort_reverse = False
        self.error_sort_column = ""
        self.error_sort_reverse = False
        self.variant_filter_var = tk.StringVar()
        self.group_filter_var = tk.StringVar()
        self.order_var = tk.StringVar(value="PGN-Reihenfolge")
        self._membership_vars: dict = {}
        self._repertoire_tree_groups: dict = {}
        self.error_filter_var = tk.StringVar()
        self.error_detail_var = tk.StringVar(value="")

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._load_last_pgn_source_on_startup)

    def _apply_style(self) -> None:
        """Ruhiger, einheitlicher Feinschliff für die ttk-Elemente (Tabellen,
        Reiter). Bewusst zurückhaltend; bricht nichts, wenn das Theme einzelne
        Optionen ignoriert."""
        accent = "#779556"  # passend zur Brettfarbe
        style = ttk.Style(self)
        try:
            style.configure("Treeview", rowheight=21, font=("Helvetica", 10))
            style.configure("Treeview.Heading", font=("Helvetica", 10, "bold"))
            style.map(
                "Treeview",
                background=[("selected", accent)],
                foreground=[("selected", "white")],
            )
            style.configure("TNotebook.Tab", padding=(14, 7))
        except tk.TclError:
            pass

    def _build_ui(self) -> None:
        self._apply_style()
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        root = tk.Frame(self, padx=12, pady=12)
        root.grid(row=0, column=0, sticky="nsew")
        root.columnconfigure(0, weight=0)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)

        left = tk.Frame(root)
        left.grid(row=0, column=0, padx=(0, 14), sticky="nw")

        right = tk.Frame(root)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)

        self.board_widget = BoardWidget(
            left,
            geometry=BoardGeometry(square_size=60, margin=26),
            on_square_click=self._on_square_click,
            on_trainable_hover=self._on_trainable_hover,
            on_drag_move=self._on_drag_move,
        )
        self.board_widget.set_hover_piece_colour(self.train_color)
        self.board_widget.set_flipped(self.train_color == chess.BLACK)
        self.board_widget.grid(row=0, column=0)

        self.current_line_var = tk.StringVar(value="Noch keine Variante ausgewählt")
        current_line_label = tk.Label(
            left,
            textvariable=self.current_line_var,
            anchor="w",
            justify="left",
            wraplength=500,
            font=("TkDefaultFont", 13, "bold"),
        )
        current_line_label.grid(row=1, column=0, sticky="w", pady=(8, 0))

        legend = tk.Label(
            left,
            text="Gelb: letzter Zug · Rot: falscher Versuch · Grün: Lösung",
            anchor="w",
        )
        legend.grid(row=2, column=0, sticky="w", pady=(4, 0))

        controls = tk.Frame(left)
        controls.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        controls.columnconfigure(0, weight=1)
        controls.columnconfigure(1, weight=1)

        self.restart_button = tk.Button(controls, text="Variante von vorn", command=self._restart)
        self.restart_button.grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=(0, 6))

        self.undo_button = tk.Button(controls, text="Zug zurück", command=self._undo)
        self.undo_button.grid(row=0, column=1, sticky="ew", pady=(0, 6))

        self.solution_button = tk.Button(controls, text="Lösung zeigen", command=self._show_solution)
        self.solution_button.grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=(0, 6))

        self.repeat_button = tk.Button(controls, text="Abschnitt wiederholen", command=self._repeat_until_here)
        self.repeat_button.grid(row=1, column=1, sticky="ew", pady=(0, 6))

        self.next_line_button = tk.Button(controls, text="Nächste Variante  (Enter)", command=self._continue_set_training)
        self.next_line_button.grid(row=2, column=0, columnspan=2, sticky="ew")

        status_box = tk.LabelFrame(left, text="Status / Fortschritt", padx=8, pady=8)
        status_box.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        status_box.columnconfigure(0, weight=1)

        self.mode_var = tk.StringVar(value="Modus: —")
        tk.Label(
            status_box, textvariable=self.mode_var, anchor="w", justify="left", wraplength=480, height=1
        ).grid(row=0, column=0, sticky="ew")

        self.status_var = tk.StringVar(value="Bitte PGN laden.")
        tk.Label(
            status_box, textvariable=self.status_var, anchor="nw", justify="left", wraplength=480, height=2
        ).grid(row=1, column=0, sticky="ew", pady=(4, 0))

        self.progress_var = tk.StringVar(value="")
        tk.Label(
            status_box, textvariable=self.progress_var, anchor="w", justify="left", wraplength=480, height=1
        ).grid(row=2, column=0, sticky="ew", pady=(4, 0))

        review_box = tk.LabelFrame(left, text="Tägliche Wiederholung", padx=8, pady=8)
        review_box.grid(row=5, column=0, sticky="ew", pady=(10, 0))
        review_box.columnconfigure(0, weight=1)

        self.due_var = tk.StringVar(value="Heute zu wiederholen: —")
        tk.Label(
            review_box, textvariable=self.due_var, anchor="w", font=("Helvetica", 12, "bold")
        ).grid(row=0, column=0, sticky="w")

        self.review_button = tk.Button(review_box, text="Wiederholung starten", command=self._start_review)
        self.review_button.grid(row=0, column=1, sticky="e", padx=(8, 0))

        self.notebook = ttk.Notebook(right)
        self.notebook.grid(row=0, column=0, sticky="nsew")

        self._library_tab = tk.Frame(self.notebook, padx=8, pady=8)
        self._repertoire_tab = tk.Frame(self.notebook, padx=8, pady=8)
        self._errors_tab = tk.Frame(self.notebook, padx=8, pady=8)
        self._progress_tab = tk.Frame(self.notebook, padx=8, pady=8)
        self.notebook.add(self._library_tab, text="Bibliothek & Training")
        self.notebook.add(self._repertoire_tab, text="Repertoire")
        self.notebook.add(self._errors_tab, text="Fehlerprotokoll")
        self.notebook.add(self._progress_tab, text="Fortschritt")
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        self._build_repertoire_tab()
        self._build_progress_tab()

        pgn_box = self._library_tab
        pgn_box.columnconfigure(0, weight=1)
        pgn_box.columnconfigure(1, weight=1)
        pgn_box.rowconfigure(4, weight=1)

        load_button = tk.Button(pgn_box, text="PGN laden", width=16, command=self._load_pgn)
        load_button.grid(row=0, column=0, sticky="w")

        folder_button = tk.Button(pgn_box, text="PGN-Ordner laden", width=18, command=self._load_pgn_folder)
        folder_button.grid(row=0, column=1, sticky="w", padx=(8, 0))

        export_button = tk.Button(pgn_box, text="Statistik exportieren", width=18, command=self._export_stats_csv)
        export_button.grid(row=1, column=1, sticky="e", padx=(8, 0), pady=(8, 0))

        colour_row = tk.Frame(pgn_box)
        colour_row.grid(row=1, column=0, sticky="w", pady=(8, 0))

        tk.Label(colour_row, text="Trainiere:").grid(row=0, column=0, sticky="w")

        initial_train_colour = "black" if self.train_color == chess.BLACK else "white"
        self.train_colour_var = tk.StringVar(value=initial_train_colour)
        white_radio = tk.Radiobutton(
            colour_row,
            text="Weiß",
            variable=self.train_colour_var,
            value="white",
            command=self._set_training_colour,
        )
        white_radio.grid(row=0, column=1, padx=(8, 0), sticky="w")

        black_radio = tk.Radiobutton(
            colour_row,
            text="Schwarz",
            variable=self.train_colour_var,
            value="black",
            command=self._set_training_colour,
        )
        black_radio.grid(row=0, column=2, padx=(8, 0), sticky="w")

        filter_row = tk.Frame(pgn_box)
        filter_row.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        filter_row.columnconfigure(1, weight=1)

        tk.Label(filter_row, text="Suche:").grid(row=0, column=0, sticky="w", padx=(0, 6))

        filter_entry = tk.Entry(filter_row, textvariable=self.variant_filter_var)
        filter_entry.grid(row=0, column=1, sticky="ew")

        clear_filter_button = tk.Button(filter_row, text="Suche löschen", command=self._clear_variant_filter)
        clear_filter_button.grid(row=0, column=2, sticky="e", padx=(8, 0))

        tk.Label(
            filter_row,
            text="zeigt nur passende Zeilen — z. B. Variantenname, Quelle oder Gruppe",
            foreground="grey",
            anchor="w",
        ).grid(row=1, column=1, columnspan=2, sticky="w", pady=(2, 0))

        self.variant_filter_var.trace_add("write", lambda *_: self._refresh_variant_table())

        category_row = tk.Frame(pgn_box)
        category_row.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        category_row.columnconfigure(0, weight=1)

        # Block 1: Zugehörigkeit der gewählten Variante als Häkchenliste.
        # Ein Haken bedeutet: Variante ist in dieser Gruppe. Setzen/Entfernen
        # wirkt sofort.
        membership_box = tk.LabelFrame(category_row, text="Gruppen der gewählten Variante", padx=6, pady=6)
        membership_box.grid(row=0, column=0, sticky="ew")
        membership_box.columnconfigure(0, weight=1)

        self.membership_canvas = tk.Canvas(membership_box, height=104, highlightthickness=0)
        self.membership_canvas.grid(row=0, column=0, sticky="ew")
        membership_scroll = ttk.Scrollbar(
            membership_box, orient="vertical", command=self.membership_canvas.yview
        )
        membership_scroll.grid(row=0, column=1, sticky="ns")
        self.membership_canvas.configure(yscrollcommand=membership_scroll.set)

        self.membership_inner = tk.Frame(self.membership_canvas)
        self._membership_window = self.membership_canvas.create_window(
            (0, 0), window=self.membership_inner, anchor="nw"
        )
        self.membership_inner.bind(
            "<Configure>",
            lambda _e: self.membership_canvas.configure(scrollregion=self.membership_canvas.bbox("all")),
        )
        self.membership_canvas.bind(
            "<Configure>",
            lambda e: self.membership_canvas.itemconfigure(self._membership_window, width=e.width),
        )

        # Gruppen anlegen/umbenennen/löschen und einem Repertoire zuordnen:
        # alles im Reiter „Repertoire".

        # Block 2: wirkt nur auf die Tabellenanzeige.
        filter_group_box = tk.LabelFrame(category_row, text="Tabelle nach Gruppe filtern", padx=6, pady=6)
        filter_group_box.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        filter_group_box.columnconfigure(0, weight=1)

        self.group_filter_combo = ttk.Combobox(
            filter_group_box, textvariable=self.group_filter_var, values=[], state="readonly"
        )
        self.group_filter_combo.grid(row=0, column=0, sticky="ew")

        clear_group_filter_button = tk.Button(
            filter_group_box,
            text="Alle Gruppen",
            command=self._clear_group_filter,
        )
        clear_group_filter_button.grid(row=0, column=1, sticky="e", padx=(8, 0))

        self.group_filter_var.trace_add("write", lambda *_: self._refresh_variant_table())

        variant_table_frame = tk.Frame(pgn_box)
        variant_table_frame.grid(row=4, column=0, columnspan=2, pady=(8, 0), sticky="nsew")
        variant_table_frame.columnconfigure(0, weight=1)
        variant_table_frame.rowconfigure(0, weight=1)

        self.variant_table = ttk.Treeview(
            variant_table_frame,
            columns=("category", "source", "variant", "due", "attempts", "wrong", "accuracy", "plies", "status"),
            show="headings",
            height=10,
            selectmode="browse",
        )
        self.variant_table.heading("category", text="Gruppe ⇅", command=lambda: self._sort_variant_table("category"))
        self.variant_table.heading("source", text="Quelle ⇅", command=lambda: self._sort_variant_table("source"))
        self.variant_table.heading("variant", text="Variante ⇅", command=lambda: self._sort_variant_table("variant"))
        self.variant_table.heading("due", text="Fällig ⇅", command=lambda: self._sort_variant_table("due"))
        self.variant_table.heading("attempts", text="Versuche ⇅", command=lambda: self._sort_variant_table("attempts"))
        self.variant_table.heading("wrong", text="Fehler ⇅", command=lambda: self._sort_variant_table("wrong"))
        self.variant_table.heading("accuracy", text="Trefferquote ⇅", command=lambda: self._sort_variant_table("accuracy"))
        self.variant_table.heading("plies", text="Halbzüge ⇅", command=lambda: self._sort_variant_table("plies"))
        self.variant_table.heading("status", text="Status ⇅", command=lambda: self._sort_variant_table("status"))

        self.variant_table.column("category", width=130, minwidth=100, stretch=False)
        self.variant_table.column("source", width=120, minwidth=90, stretch=True)
        self.variant_table.column("variant", width=240, minwidth=170, stretch=True)
        self.variant_table.column("due", width=90, minwidth=72, stretch=False, anchor="center")
        self.variant_table.column("attempts", width=75, minwidth=65, stretch=False, anchor="center")
        self.variant_table.column("wrong", width=65, minwidth=55, stretch=False, anchor="center")
        self.variant_table.column("accuracy", width=95, minwidth=85, stretch=False, anchor="center")
        self.variant_table.column("plies", width=75, minwidth=60, stretch=False, anchor="center")
        self.variant_table.column("status", width=85, minwidth=70, stretch=False, anchor="center")

        self.variant_table.grid(row=0, column=0, sticky="nsew")

        variant_scroll = ttk.Scrollbar(
            variant_table_frame,
            orient="vertical",
            command=self.variant_table.yview,
        )
        variant_scroll.grid(row=0, column=1, sticky="ns")
        self.variant_table.configure(yscrollcommand=variant_scroll.set)

        self.variant_table.bind("<<TreeviewSelect>>", self._on_variant_selection_changed)

        train_buttons = tk.LabelFrame(pgn_box, text="Trainieren", padx=6, pady=6)
        train_buttons.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        train_buttons.columnconfigure(0, weight=1)

        self.start_button = tk.Button(
            train_buttons, text="Gewählte Variante trainieren", command=self._start_training
        )
        self.start_button.grid(row=0, column=0, sticky="w")

        tk.Label(
            train_buttons,
            text="Ganze Gruppen oder Repertoires trainierst du im Reiter „Repertoire“.",
            foreground="grey",
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        self.stats_var = tk.StringVar(value="")
        stats = tk.Label(
            pgn_box,
            textvariable=self.stats_var,
            anchor="nw",
            justify="left",
            wraplength=520,
            height=3,
        )
        stats.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(6, 0))

        error_box = self._errors_tab
        error_box.columnconfigure(0, weight=1)
        error_box.rowconfigure(0, weight=0)
        error_box.rowconfigure(1, weight=1)
        error_box.rowconfigure(2, weight=0)
        error_box.rowconfigure(3, weight=0)

        error_filter_row = tk.Frame(error_box)
        error_filter_row.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        error_filter_row.columnconfigure(1, weight=1)

        tk.Label(error_filter_row, text="Suche:").grid(row=0, column=0, sticky="w", padx=(0, 6))

        error_filter_entry = tk.Entry(error_filter_row, textvariable=self.error_filter_var)
        error_filter_entry.grid(row=0, column=1, sticky="ew")

        clear_error_filter_button = tk.Button(
            error_filter_row,
            text="Suche löschen",
            command=self._clear_error_filter,
        )
        clear_error_filter_button.grid(row=0, column=2, sticky="e", padx=(8, 0))

        tk.Label(
            error_filter_row,
            text="zeigt nur passende Fehlzüge — z. B. ein Zug wie Bc4, der Typ oder ein Datum",
            foreground="grey",
            anchor="w",
        ).grid(row=1, column=1, columnspan=2, sticky="w", pady=(2, 0))

        self.error_filter_var.trace_add("write", lambda *_: self._update_stats_display())

        error_list_frame = tk.Frame(error_box)
        error_list_frame.grid(row=1, column=0, columnspan=2, sticky="nsew")
        error_list_frame.columnconfigure(0, weight=1)
        error_list_frame.rowconfigure(0, weight=1)

        self.error_list = ttk.Treeview(
            error_list_frame,
            columns=("count", "kind", "expected", "last_played", "last_timestamp"),
            show="headings",
            height=6,
            selectmode="browse",
        )
        self.error_list.heading("count", text="Anzahl ⇅", command=lambda: self._sort_error_table("count"))
        self.error_list.heading("kind", text="Typ ⇅", command=lambda: self._sort_error_table("kind"))
        self.error_list.heading("expected", text="Erwartet ⇅", command=lambda: self._sort_error_table("expected"))
        self.error_list.heading("last_played", text="Gespielt ⇅", command=lambda: self._sort_error_table("last_played"))
        self.error_list.heading("last_timestamp", text="Letzter Fehler ⇅", command=lambda: self._sort_error_table("last_timestamp"))

        self.error_list.column("count", width=80, minwidth=60, stretch=False, anchor="center")
        self.error_list.column("kind", width=120, minwidth=100, stretch=False, anchor="center")
        self.error_list.column("expected", width=150, minwidth=100, stretch=True)
        self.error_list.column("last_played", width=150, minwidth=110, stretch=True)
        self.error_list.column("last_timestamp", width=160, minwidth=120, stretch=False, anchor="center")

        self.error_list.tag_configure("active_error", background="#fff3b0")
        self.error_list.grid(row=0, column=0, sticky="nsew")

        error_scroll = ttk.Scrollbar(
            error_list_frame,
            orient="vertical",
            command=self.error_list.yview,
        )
        error_scroll.grid(row=0, column=1, sticky="ns")
        self.error_list.configure(yscrollcommand=error_scroll.set)

        self.error_list.bind("<Double-Button-1>", lambda event: self._train_selected_error_position())
        self.error_list.bind("<<TreeviewSelect>>", lambda event: self._update_error_detail())

        error_detail = tk.Label(
            error_box,
            textvariable=self.error_detail_var,
            anchor="w",
            justify="left",
            wraplength=520,
        )
        error_detail.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6, 0))

        error_buttons = tk.Frame(error_box)
        error_buttons.grid(row=3, column=0, sticky="ew", pady=(8, 0))

        error_buttons.columnconfigure(0, weight=1)
        error_buttons.columnconfigure(1, weight=1)
        error_buttons.columnconfigure(2, weight=1)

        self.wrong_session_button = tk.Button(
            error_buttons,
            text="Fehlzug-Sitzung starten",
            width=24,
            command=self._start_wrong_move_session,
        )
        self.wrong_session_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.selected_error_button = tk.Button(
            error_buttons,
            text="Sitzung ab Auswahl starten",
            width=24,
            command=self._train_selected_error_position,
        )
        self.selected_error_button.grid(row=0, column=1, sticky="ew", padx=(0, 8))

        self.session_next_button = tk.Button(
            error_buttons,
            text="Nächstes Fehlzugproblem",
            width=24,
            command=self._continue_wrong_move_session,
        )
        self.session_next_button.grid(row=0, column=2, sticky="ew")

        self._refresh_group_choices()
        self._refresh_membership()
        self._update_due_count()
        self._update_ui_state()

        self.bind("<Return>", self._on_next_line_key)
        self.bind("<KP_Enter>", self._on_next_line_key)

    def _build_repertoire_tab(self) -> None:
        tab = self._repertoire_tab
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)

        tk.Label(
            tab,
            text="Deine Repertoires — welche Gruppen zu Weiß bzw. Schwarz gehören:",
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", pady=(0, 6))

        tree_frame = tk.Frame(tab)
        tree_frame.grid(row=1, column=0, sticky="nsew")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        self.repertoire_tree = ttk.Treeview(tree_frame, show="tree", selectmode="browse")
        self.repertoire_tree.grid(row=0, column=0, sticky="nsew")
        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.repertoire_tree.yview)
        tree_scroll.grid(row=0, column=1, sticky="ns")
        self.repertoire_tree.configure(yscrollcommand=tree_scroll.set)
        self.repertoire_tree.bind("<<TreeviewSelect>>", lambda _e: self._update_tree_action_buttons())

        actions = tk.LabelFrame(tab, text="Gruppen", padx=8, pady=8)
        actions.grid(row=2, column=0, sticky="ew", pady=(8, 0))

        self.tree_new_button = tk.Button(actions, text="Neue Gruppe …", command=self._create_group)
        self.tree_new_button.grid(row=0, column=0, sticky="w")

        self.tree_rename_button = tk.Button(actions, text="Umbenennen …", command=self._rename_tree_group)
        self.tree_rename_button.grid(row=0, column=1, sticky="w", padx=(8, 0))

        self.tree_delete_button = tk.Button(actions, text="Löschen", command=self._delete_tree_group)
        self.tree_delete_button.grid(row=0, column=2, sticky="w", padx=(8, 0))

        self.tree_white_button = tk.Button(
            actions, text="→ Weiß-Repertoire", command=lambda: self._assign_selected_tree_group(SIDE_WHITE)
        )
        self.tree_white_button.grid(row=1, column=0, sticky="w", pady=(6, 0))

        self.tree_black_button = tk.Button(
            actions, text="→ Schwarz-Repertoire", command=lambda: self._assign_selected_tree_group(SIDE_BLACK)
        )
        self.tree_black_button.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(6, 0))

        self.tree_remove_button = tk.Button(
            actions, text="herausnehmen", command=lambda: self._assign_selected_tree_group(SIDE_NONE)
        )
        self.tree_remove_button.grid(row=1, column=2, sticky="w", padx=(8, 0), pady=(6, 0))

        tk.Label(
            actions,
            text="„Neue Gruppe“ legt eine leere Gruppe an. Umbenennen / Löschen / zuordnen "
            "wirken auf die im Baum gewählte Gruppe; „herausnehmen“ löst die Zuordnung.",
            foreground="grey",
            anchor="w",
            justify="left",
            wraplength=520,
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(6, 0))

        train = tk.LabelFrame(tab, text="Trainieren", padx=8, pady=8)
        train.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        train.columnconfigure(0, weight=1)
        train.columnconfigure(1, weight=1)
        train.columnconfigure(2, weight=1)

        self.tree_train_group_button = tk.Button(
            train, text="Gewählte Gruppe", command=self._start_tree_group_training
        )
        self.tree_train_group_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.tree_train_white_button = tk.Button(
            train, text="Weiß-Repertoire", command=lambda: self._start_repertoire_training(SIDE_WHITE)
        )
        self.tree_train_white_button.grid(row=0, column=1, sticky="ew", padx=(0, 6))

        self.tree_train_black_button = tk.Button(
            train, text="Schwarz-Repertoire", command=lambda: self._start_repertoire_training(SIDE_BLACK)
        )
        self.tree_train_black_button.grid(row=0, column=2, sticky="ew")

        order_row = tk.Frame(train)
        order_row.grid(row=1, column=0, columnspan=3, sticky="w", pady=(6, 0))
        tk.Label(order_row, text="Reihenfolge:").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            order_row,
            textvariable=self.order_var,
            values=["PGN-Reihenfolge", "Schwächste zuerst"],
            state="readonly",
            width=20,
        ).grid(row=0, column=1, sticky="w", padx=(8, 0))

        self._refresh_repertoire_tree()

    @staticmethod
    def _count_label(count: int, singular: str, plural: str) -> str:
        return f"{count} {singular if count == 1 else plural}"

    def _refresh_repertoire_tree(self) -> None:
        tree = getattr(self, "repertoire_tree", None)
        if tree is None:
            return

        previous = self._selected_tree_group()
        for item in tree.get_children():
            tree.delete(item)
        self._repertoire_tree_groups = {}

        repertoire = self.repertoire_store.repertoire
        sections = [
            ("Weiß-Repertoire", SIDE_WHITE),
            ("Schwarz-Repertoire", SIDE_BLACK),
            ("Noch keinem Repertoire zugeordnet", SIDE_NONE),
        ]
        for title, side in sections:
            summaries = repertoire.category_summaries_for_side(side)
            group_count = self._count_label(len(summaries), "Gruppe", "Gruppen")
            parent = tree.insert("", tk.END, text=f"{title}   ({group_count})", open=True)
            if not summaries:
                tree.insert(parent, tk.END, text="—  (leer)")
            for name, count in summaries:
                variant_count = self._count_label(count, "Variante", "Varianten")
                iid = tree.insert(parent, tk.END, text=f"{name}   ({variant_count})")
                self._repertoire_tree_groups[iid] = name

        if previous is not None:
            self._select_tree_group(previous)
        self._update_tree_action_buttons()

    def _selected_tree_group(self) -> str | None:
        tree = getattr(self, "repertoire_tree", None)
        if tree is None:
            return None
        selection = tree.selection()
        if not selection:
            return None
        return self._repertoire_tree_groups.get(selection[0])

    def _select_tree_group(self, name: str) -> None:
        tree = getattr(self, "repertoire_tree", None)
        if tree is None:
            return
        for iid, group_name in self._repertoire_tree_groups.items():
            if group_name == name:
                tree.selection_set(iid)
                tree.see(iid)
                return

    def _update_tree_action_buttons(self) -> None:
        if not hasattr(self, "tree_white_button"):
            return
        enabled = self._selected_tree_group() is not None
        state = self._tk_state(enabled)
        self.tree_white_button.configure(state=state)
        self.tree_black_button.configure(state=state)
        self.tree_remove_button.configure(state=state)
        self.tree_rename_button.configure(state=state)
        self.tree_delete_button.configure(state=state)
        if hasattr(self, "tree_train_group_button"):
            self.tree_train_group_button.configure(state=self._tk_state(enabled and bool(self.lines)))

    def _assign_selected_tree_group(self, side: str) -> None:
        name = self._selected_tree_group()
        if name is None:
            self.status_var.set("Bitte zuerst eine Gruppe im Baum auswählen (nicht die Überschrift).")
            return

        self.repertoire_store.repertoire.set_category_side(name, side)
        self.repertoire_store.save(self.repertoire_path)
        self._after_group_change()

        target = {
            SIDE_WHITE: "Weiß-Repertoire",
            SIDE_BLACK: "Schwarz-Repertoire",
            SIDE_NONE: "keinem Repertoire",
        }[side]
        self.status_var.set(f"Gruppe „{name}“ gehört jetzt zu {target}.")

    def _short_source_name(self, source_name: str) -> str:
        if not source_name:
            return "ohne Quelle"

        name = source_name
        if name.lower().endswith(".pgn"):
            name = name[:-4]

        name = name.replace("lichess_study_", "")
        name = name.replace("_namen_bereinigt", "")

        if "_by_" in name:
            name = name.split("_by_", 1)[0]

        name = name.replace("_", " ").strip()

        replacements = {
            "wei-": "weiß · ",
            "weiss-": "weiß · ",
            "weiß-": "weiß · ",
            "schwarz-": "schwarz · ",
        }

        for prefix, replacement in replacements.items():
            if name.lower().startswith(prefix):
                name = replacement + name[len(prefix):]
                break

        parts = [part[:1].upper() + part[1:] if part else part for part in name.split(" · ")]
        name = " · ".join(parts)

        name = name.replace("-system", "-System")
        name = name.replace("koenigsindisch", "Königsindisch")
        name = name.replace("königsindisch", "Königsindisch")
        name = name.replace("franzoesisch", "Französisch")
        name = name.replace("französisch", "Französisch")
        name = name.replace("sizilianisch", "Sizilianisch")
        name = name.replace("englisch", "Englisch")
        name = name.replace("london", "London")

        return name

    def _save_settings(
        self,
        *,
        last_pgn_folder: str | None = None,
        last_pgn_path: str | None = None,
        last_pgn_kind: str | None = None,
    ) -> None:
        train_color = "black" if self.train_color == chess.BLACK else "white"
        self.settings_store.update(
            train_color=train_color,
            window_geometry=self.geometry(),
            last_pgn_folder=last_pgn_folder,
            last_pgn_path=last_pgn_path,
            last_pgn_kind=last_pgn_kind,
        )
        self.settings_store.save(self.settings_path)

    def _on_close(self) -> None:
        self._save_settings()
        self.destroy()

    def _category_text_for_line(self, line: OpeningLine) -> str:
        names = [
            category.name
            for category in self.repertoire_store.repertoire.categories
            if category.contains(line)
        ]
        return ", ".join(names) if names else "–"

    def _due_text_for_line(self, line: OpeningLine) -> str:
        """Wann ist diese Variante das nächste Mal zur Wiederholung dran?"""
        if not line.moves_uci:
            return "—"
        card = self.schedule_store.card_for(line.source_name, line.name)
        if is_new(card):
            return "neu"
        try:
            due = date.fromisoformat(card.due)
        except ValueError:
            return "neu"
        delta = (due - date.today()).days
        if delta <= 0:
            return "heute"
        if delta == 1:
            return "morgen"
        return f"in {delta} Tagen"

    def _variant_table_values(self, index: int, line: OpeningLine) -> tuple:
        category = self._category_text_for_line(line)
        source = self._short_source_name(line.source_name)
        variant = line.name
        due = self._due_text_for_line(line)
        stats = self.stats_store.stats_for_line(source_name=line.source_name, line_name=line.name)
        attempts = str(stats.attempts)
        wrong = str(stats.wrong)
        accuracy = "–" if stats.attempts == 0 else f"{round(stats.accuracy * 100)} %"
        plies = str(len(line.moves_uci))
        status = "keine Züge" if not line.moves_uci else ""
        return category, source, variant, due, attempts, wrong, accuracy, plies, status

    def _line_matches_filter(self, index: int, line: OpeningLine) -> bool:
        query = self.variant_filter_var.get().strip().casefold()
        group_query = self.group_filter_var.get().strip().casefold()

        values = self._variant_table_values(index, line)
        if query:
            haystack = " ".join(values).casefold()
            if query not in haystack:
                return False

        if group_query:
            group_text = values[0].casefold()
            if group_query not in group_text:
                return False

        return True

    def _refresh_variant_table(self) -> None:
        selected = self.variant_table.selection()
        selected_id = selected[0] if selected else None

        for item in self.variant_table.get_children():
            self.variant_table.delete(item)

        for index, line in enumerate(self.lines):
            if not self._line_matches_filter(index, line):
                continue

            self.variant_table.insert(
                "",
                tk.END,
                iid=str(index),
                values=self._variant_table_values(index, line),
            )

        if self.variant_sort_column:
            self._sort_variant_table(self.variant_sort_column, keep_direction=True)

        if selected_id and self.variant_table.exists(selected_id):
            self.variant_table.selection_set(selected_id)
            self.variant_table.see(selected_id)

        self._update_ui_state()

    def _on_variant_selection_changed(self, _event=None) -> None:
        self._refresh_membership()
        self._update_ui_state()

    def _clear_variant_filter(self) -> None:
        self.variant_filter_var.set("")

    def _clear_group_filter(self) -> None:
        self.group_filter_var.set("")

    def _refresh_membership(self) -> None:
        """Baut die Häkchenliste für die aktuell gewählte Variante neu auf.

        Ein Haken pro Gruppe; gesetzt, wenn die Variante in der Gruppe ist.
        """
        if not hasattr(self, "membership_inner"):
            return

        for child in self.membership_inner.winfo_children():
            child.destroy()
        self._membership_vars = {}

        line = self._selected_line()
        if line is None:
            tk.Label(self.membership_inner, text="Keine Variante gewählt.", anchor="w").grid(
                row=0, column=0, sticky="w"
            )
            return

        repertoire = self.repertoire_store.repertoire
        names = repertoire.category_names()
        if not names:
            tk.Label(
                self.membership_inner,
                text="Noch keine Gruppen. Unten eine anlegen.",
                anchor="w",
            ).grid(row=0, column=0, sticky="w")
            return

        member = {category.name for category in repertoire.categories if category.contains(line)}
        for index, name in enumerate(names):
            var = tk.BooleanVar(value=name in member)
            self._membership_vars[name] = var
            tk.Checkbutton(
                self.membership_inner,
                text=name,
                variable=var,
                anchor="w",
                command=lambda group=name, value=var: self._toggle_membership(group, value),
            ).grid(row=index, column=0, sticky="w")

    def _toggle_membership(self, group_name: str, var: tk.BooleanVar) -> None:
        line = self._selected_line()
        if line is None:
            return

        repertoire = self.repertoire_store.repertoire
        if var.get():
            repertoire.add_line_to_category(group_name, line)
            self.status_var.set(f"Variante zur Gruppe {group_name} hinzugefügt.")
        else:
            repertoire.remove_line_from_category(group_name, line)
            self.status_var.set(f"Variante aus Gruppe {group_name} entfernt.")

        self.repertoire_store.save(self.repertoire_path)
        self._refresh_variant_table()
        self._refresh_repertoire_tree()

    def _refresh_group_choices(self) -> None:
        names = self.repertoire_store.repertoire.category_names()
        if hasattr(self, "group_filter_combo"):
            self.group_filter_combo.configure(values=names)

    def _after_group_change(self) -> None:
        """Nach Anlegen/Umbenennen/Löschen alle abhängigen Anzeigen auffrischen."""
        self._refresh_variant_table()
        self._refresh_group_choices()
        self._refresh_membership()
        self._refresh_repertoire_tree()

    # --- Gruppenpflege im Repertoire-Reiter -----------------------------

    def _create_group(self) -> None:
        name = simpledialog.askstring("Neue Gruppe", "Name der neuen Gruppe:", parent=self)
        if name is None:
            return
        name = name.strip()
        if not name:
            return

        repertoire = self.repertoire_store.repertoire
        if repertoire.category(name) is not None:
            messagebox.showinfo("Gruppe besteht", f"Die Gruppe „{name}“ gibt es bereits.", parent=self)
            return

        repertoire.categories.append(RepertoireCategory(name=name))
        self.repertoire_store.save(self.repertoire_path)
        self._after_group_change()
        self._select_tree_group(name)
        self._update_tree_action_buttons()
        self.status_var.set(f"Gruppe „{name}“ angelegt. Varianten ordnest du im Reiter „Bibliothek“ zu.")

    def _rename_tree_group(self) -> None:
        old_name = self._selected_tree_group()
        if old_name is None:
            self.status_var.set("Bitte zuerst eine Gruppe im Baum auswählen.")
            return

        new_name = simpledialog.askstring("Gruppe umbenennen", f"Neuer Name für „{old_name}“:", parent=self)
        if new_name is None:
            return
        new_name = new_name.strip()
        if not new_name or new_name == old_name:
            return

        if not self.repertoire_store.repertoire.rename_category(old_name, new_name):
            messagebox.showwarning("Umbenennen nicht möglich", f"„{new_name}“ existiert vermutlich schon.", parent=self)
            return

        self.repertoire_store.save(self.repertoire_path)
        if self.group_filter_var.get().strip() == old_name:
            self.group_filter_var.set(new_name)
        self._after_group_change()
        self._select_tree_group(new_name)
        self._update_tree_action_buttons()
        self.status_var.set(f"Gruppe „{old_name}“ in „{new_name}“ umbenannt.")

    def _delete_tree_group(self) -> None:
        name = self._selected_tree_group()
        if name is None:
            self.status_var.set("Bitte zuerst eine Gruppe im Baum auswählen.")
            return

        confirm = messagebox.askyesno(
            "Gruppe löschen",
            f"Die Gruppe „{name}“ wirklich löschen? Die Varianten selbst bleiben erhalten.",
            parent=self,
        )
        if not confirm:
            return

        self.repertoire_store.repertoire.delete_category(name)
        self.repertoire_store.save(self.repertoire_path)
        if self.group_filter_var.get().strip() == name:
            self.group_filter_var.set("")
        self._after_group_change()
        self._update_tree_action_buttons()
        self.status_var.set(f"Gruppe „{name}“ gelöscht. Die Varianten bleiben erhalten.")

    def _replace_lines(self, lines: list[OpeningLine], source_label: str) -> None:
        self.lines = lines
        self.variant_filter_var.set("")
        self._refresh_variant_table()

        self.training = None
        self.current_line = None
        self.selected_square = None
        self.error_panel_active = False
        self.current_error_positions = []
        self.board_widget.set_board(chess.Board())
        self.board_widget.clear_marks()

        self.status_var.set(f"{source_label} geladen. Varianten: {len(self.lines)}")
        self._update_progress()
        self._update_stats_display()
        self._update_due_count()
        self._update_ui_state()

    def _load_last_pgn_source_on_startup(self) -> None:
        source_path = self.settings_store.settings.last_pgn_path
        source_kind = self.settings_store.settings.last_pgn_kind

        # Backward compatibility: older settings stored only a folder path.
        if not source_path and self.settings_store.settings.last_pgn_folder:
            source_path = self.settings_store.settings.last_pgn_folder
            source_kind = "folder"

        if not source_path:
            return

        path = Path(source_path)
        if not path.exists():
            self.status_var.set("Gespeicherte PGN-Quelle wurde nicht gefunden.")
            return

        try:
            if source_kind == "file" or path.is_file():
                lines = load_pgn_file(path)
                source_label = f"PGN-Datei {path.name}"
            elif source_kind == "folder" or path.is_dir():
                lines = load_pgn_folder(path)
                source_label = f"PGN-Ordner {path}"
            else:
                self.status_var.set("Gespeicherte PGN-Quelle hat einen unbekannten Typ.")
                return
        except Exception as exc:
            self.status_var.set(f"Gespeicherte PGN-Quelle konnte nicht geladen werden: {exc}")
            return

        if not lines:
            self.status_var.set("Gespeicherte PGN-Quelle enthält keine trainierbaren Varianten.")
            return

        self._replace_lines(lines, source_label=source_label)

    def _export_stats_csv(self) -> None:
        if not self.stats_store.events:
            messagebox.showinfo("Keine Statistikdaten", "Es liegen noch keine Trainingsereignisse zum Exportieren vor.")
            return

        path = filedialog.asksaveasfilename(
            title="Statistik als CSV exportieren",
            defaultextension=".csv",
            filetypes=[("CSV-Dateien", "*.csv"), ("Alle Dateien", "*.*")],
        )
        if not path:
            return

        try:
            export_training_events_csv(self.stats_store, path)
        except Exception as exc:
            messagebox.showerror("Statistikexport fehlgeschlagen", str(exc))
            return

        self.status_var.set(f"Statistik exportiert: {Path(path).name}")
        messagebox.showinfo("Statistik exportiert", f"Die Statistik wurde exportiert:\n{path}")

    def _load_pgn(self) -> None:
        initial_dir = self.settings_store.settings.last_pgn_folder or None
        path = filedialog.askopenfilename(
            title="PGN-Datei laden",
            initialdir=initial_dir,
            filetypes=[("PGN-Dateien", "*.pgn"), ("Alle Dateien", "*.*")],
        )
        if not path:
            return

        try:
            lines = load_pgn_file(path)
        except Exception as exc:
            messagebox.showerror("PGN konnte nicht geladen werden", str(exc))
            return

        if not lines:
            messagebox.showwarning("Keine Varianten gefunden", "Die PGN-Datei enthält keine trainierbaren Varianten.")
            return

        pgn_path = Path(path)
        self._save_settings(
            last_pgn_folder=str(pgn_path.parent),
            last_pgn_path=str(pgn_path),
            last_pgn_kind="file",
        )
        self._replace_lines(lines, f"PGN-Datei {pgn_path.name}")

    def _load_pgn_folder(self) -> None:
        initial_dir = self.settings_store.settings.last_pgn_folder or None
        path = filedialog.askdirectory(
            title="PGN-Ordner laden",
            initialdir=initial_dir,
        )
        if not path:
            return

        try:
            lines = load_pgn_folder(path)
        except Exception as exc:
            messagebox.showerror("PGN-Ordner konnte nicht geladen werden", str(exc))
            return

        if not lines:
            messagebox.showwarning("Keine Varianten gefunden", "Der PGN-Ordner enthält keine trainierbaren Varianten.")
            return

        self._save_settings(
            last_pgn_folder=path,
            last_pgn_path=path,
            last_pgn_kind="folder",
        )
        self._replace_lines(lines, f"PGN-Ordner {path}")

    def _set_training_colour(self) -> None:
        if self.train_colour_var.get() == "black":
            self.train_color = chess.BLACK
            self.board_widget.set_flipped(True)
            self.board_widget.set_hover_piece_colour(self.train_color)
            self.status_var.set("Trainingsseite: Schwarz.")
            self._save_settings()
            self._update_progress()
        else:
            self.train_color = chess.WHITE
            self.board_widget.set_flipped(False)
            self.board_widget.set_hover_piece_colour(self.train_color)
            self.status_var.set("Trainingsseite: Weiß.")
            self._save_settings()
            self._update_progress()

        self.training = None
        self.current_line = None
        self.training_run = None
        self._set_line_finished = False
        self.selected_square = None
        self.board_widget.set_board(chess.Board())
        self.board_widget.clear_marks()
        self._update_stats_display()
        self._update_ui_state()

    def _display_timestamp(self, timestamp: str | None) -> str:
        if not timestamp:
            return "?"

        # ISO-Zeit lokal lesbarer anzeigen: 2026-05-24T11:10:32+00:00 -> 2026-05-24 11:10
        if "T" in timestamp:
            date_part, time_part = timestamp.split("T", 1)
            time_part = time_part.split("+", 1)[0].split(".", 1)[0]
            return f"{date_part} {time_part[:5]}"

        return timestamp

    def _display_move_text(self, move_text: str | None) -> str:
        if not move_text:
            return "?"

        # Rohes UCI-ähnliches Format lesbarer machen, z. B. d2d2 -> d2–d2 (kein Zug).
        if len(move_text) == 4 and move_text[0] in "abcdefgh" and move_text[2] in "abcdefgh":
            start = move_text[:2]
            target = move_text[2:]
            if start == target:
                return f"{start}–{target} (Eingabefehler)"
            return f"{start}–{target}"

        return move_text

    def _update_progress(self) -> None:
        if self.training is None:
            self.progress_var.set("")
        else:
            self.progress_var.set(self.training.progress_text())
        self._update_current_line_label()

    def _update_current_line_label(self) -> None:
        if not hasattr(self, "current_line_var"):
            return
        if self.current_line is None:
            self.current_line_var.set("Noch keine Variante ausgewählt")
            return
        colour = "Weiß" if self.train_color == chess.WHITE else "Schwarz"
        self.current_line_var.set(f"{self.current_line.name}  ·  Training: {colour}")

    # --- Reiter „Fortschritt“ -------------------------------------------

    def _build_progress_tab(self) -> None:
        tab = self._progress_tab
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(2, weight=1)

        self.progress_overview_var = tk.StringVar(value="")
        tk.Label(
            tab,
            textvariable=self.progress_overview_var,
            anchor="w",
            justify="left",
            wraplength=560,
            font=("TkDefaultFont", 12, "bold"),
        ).grid(row=0, column=0, sticky="ew", pady=(0, 4))

        tk.Label(
            tab,
            text="Eine Trainingseinheit ist ein zusammenhängender Übungsblock (Pause über 30 Minuten = neue Einheit). Neueste zuerst.",
            foreground="grey",
            anchor="w",
            justify="left",
            wraplength=560,
        ).grid(row=1, column=0, sticky="w", pady=(0, 4))

        table_frame = tk.Frame(tab)
        table_frame.grid(row=2, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        self.progress_table = ttk.Treeview(
            table_frame,
            columns=("session", "attempts", "correct", "wrong", "accuracy"),
            show="headings",
            selectmode="none",
        )
        self.progress_table.heading("session", text="Einheit")
        self.progress_table.heading("attempts", text="Versuche")
        self.progress_table.heading("correct", text="Richtig")
        self.progress_table.heading("wrong", text="Fehler")
        self.progress_table.heading("accuracy", text="Trefferquote")
        self.progress_table.column("session", width=230, minwidth=170, stretch=True)
        self.progress_table.column("attempts", width=80, minwidth=70, stretch=False, anchor="center")
        self.progress_table.column("correct", width=75, minwidth=65, stretch=False, anchor="center")
        self.progress_table.column("wrong", width=70, minwidth=60, stretch=False, anchor="center")
        self.progress_table.column("accuracy", width=100, minwidth=90, stretch=False, anchor="center")
        self.progress_table.grid(row=0, column=0, sticky="nsew")

        progress_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.progress_table.yview)
        progress_scroll.grid(row=0, column=1, sticky="ns")
        self.progress_table.configure(yscrollcommand=progress_scroll.set)

        self._refresh_progress_tab()

    def _session_period_text(self, started_at: str, ended_at: str) -> str:
        start = self._display_timestamp(started_at)
        end = self._display_timestamp(ended_at)
        if " " in start and " " in end:
            start_date, start_time = start.split(" ", 1)
            end_date, end_time = end.split(" ", 1)
            if start_date == end_date:
                return f"{start_date}   {start_time}–{end_time}"
        return f"{start} – {end}"

    def _refresh_progress_tab(self) -> None:
        table = getattr(self, "progress_table", None)
        if table is None:
            return

        for item in table.get_children():
            table.delete(item)

        overview = overall_progress(self.stats_store.events)
        if overview.session_count == 0:
            self.progress_overview_var.set(
                "Noch keine Trainingsdaten. Sobald du Varianten trainierst, erscheint hier dein Fortschritt."
            )
            return

        text = (
            f"{overview.session_count} Trainingseinheiten · {overview.attempts} Versuche · "
            f"Trefferquote gesamt {round(overview.accuracy * 100)} %"
        )
        if overview.session_count >= 2 and overview.first_accuracy is not None and overview.last_accuracy is not None:
            text += (
                f" · Tendenz: {round(overview.first_accuracy * 100)} % → "
                f"{round(overview.last_accuracy * 100)} %"
            )
        self.progress_overview_var.set(text)

        for summary in reversed(summarize_training_sessions(self.stats_store.events)):
            table.insert(
                "",
                tk.END,
                values=(
                    self._session_period_text(summary.started_at, summary.ended_at),
                    summary.attempts,
                    summary.correct,
                    summary.wrong,
                    f"{round(summary.accuracy * 100)} %",
                ),
            )

    def _on_tab_changed(self, _event=None) -> None:
        try:
            if self.notebook.select() == str(self._progress_tab):
                self._refresh_progress_tab()
        except tk.TclError:
            pass

    def _update_error_detail(self) -> None:
        selection = self.error_list.selection()
        if not selection:
            self.error_detail_var.set("")
            return

        try:
            index = int(selection[0])
        except ValueError:
            self.error_detail_var.set("")
            return

        if index < 0 or index >= len(self.current_error_positions):
            self.error_detail_var.set("")
            return

        item = self.current_error_positions[index]
        expected = self._display_move_text(getattr(item, "expected_san", None))
        played = self._display_move_text(getattr(item, "played_san", None))
        count = getattr(item, "count", getattr(item, "wrong_count", 0))
        timestamp = self._display_timestamp(getattr(item, "last_timestamp", None))

        self.error_detail_var.set(
            f"Ausgewählt: erwartet {expected} · gespielt {played} · protokolliert {count}× · letzter Fehler {timestamp}"
        )

    def _clear_error_filter(self) -> None:
        self.error_filter_var.set("")

    def _wrong_summary_matches_filter(self, summary) -> bool:
        query = self.error_filter_var.get().strip().casefold()
        if not query:
            return True

        expected = self._display_move_text(summary.expected_san)
        played = self._display_move_text(summary.played_san)
        count = f"{summary.count}×"

        kind = self._wrong_summary_kind(summary)
        last_timestamp = self._display_timestamp(summary.last_timestamp)
        haystack = f"{count} {kind} {expected} {played} {last_timestamp}".casefold()
        return query in haystack

    def _update_stats_display(self) -> None:
        self.error_detail_var.set("")
        for item in self.error_list.get_children():
            self.error_list.delete(item)

        if self.current_line is None:
            self.stats_var.set("")
            self.error_detail_var.set(
                "Noch keine Variante in Bearbeitung. Trainiere eine Variante im Reiter "
                "„Bibliothek & Training“ — falsche Züge erscheinen dann hier im Fehlerprotokoll."
            )
            self._update_ui_state()
            return

        stats = self.stats_store.stats_for_line(
            source_name=self.current_line.source_name,
            line_name=self.current_line.name,
        )

        wrong_summaries = self.stats_store.wrong_move_summary_for_line(
            source_name=self.current_line.source_name,
            line_name=self.current_line.name,
        )

        if not self.error_panel_active:
            self.current_error_positions = []
            trainable = [
                s for s in wrong_summaries
                if not self._is_input_error_summary(s) and self._summary_reachable(s)
            ]
            if trainable:
                self.error_detail_var.set(
                    "Diese Variante hat protokollierte Fehlzüge. Drücke unten "
                    "„Fehlzug-Sitzung starten“, um sie zu sehen und gezielt zu üben."
                )
            else:
                self.error_detail_var.set(
                    "Für diese Variante sind noch keine Fehlzüge protokolliert. "
                    "Falsche Züge beim Training erscheinen hier."
                )
            if stats.attempts == 0:
                self.stats_var.set("Statistik: noch keine Versuche")
                return

            percent = round(stats.accuracy * 100)
            self.stats_var.set(
                f"Statistik: Versuche {stats.attempts} · Richtig {stats.correct} · "
                f"Fehler {stats.wrong} · Trefferquote {percent} %"
            )
            self._update_ui_state()
            return

        visible_summaries = [
            summary
            for summary in wrong_summaries
            if self._wrong_summary_matches_filter(summary)
            and not self._is_input_error_summary(summary)
            and self._summary_reachable(summary)
        ]
        self.current_error_positions = visible_summaries

        for index, summary in enumerate(self.current_error_positions):
            expected = self._display_move_text(summary.expected_san)
            played = self._display_move_text(summary.played_san)
            kind = self._wrong_summary_kind(summary)
            last_timestamp = self._display_timestamp(summary.last_timestamp)
            self.error_list.insert(
                "",
                tk.END,
                iid=str(index),
                values=(f"{summary.count}×", kind, expected, played, last_timestamp),
            )

        if self.error_sort_column:
            self._sort_error_table(self.error_sort_column, keep_direction=True)
        else:
            self._update_error_sort_headers()

        if not self.current_error_positions:
            if self.error_filter_var.get().strip():
                self.error_detail_var.set("Kein Fehlzug passt zur Suche.")
            else:
                self.error_detail_var.set("Für diese Variante sind keine Fehlzüge protokolliert.")

        if stats.attempts == 0:
            self.stats_var.set("Statistik: noch keine Versuche")
            self._update_ui_state()
            return

        percent = round(stats.accuracy * 100)
        text = (
            f"Statistik: Versuche {stats.attempts} · Richtig {stats.correct} · "
            f"Fehler {stats.wrong} · Trefferquote {percent} %"
        )

        if self.current_error_positions:
            top = max(self.current_error_positions, key=lambda summary: summary.count)
            expected = self._display_move_text(top.expected_san)
            played = self._display_move_text(top.played_san)
            event_count = sum(summary.count for summary in self.current_error_positions)
            text += (
                f" · trainierbare Fehlzugprobleme: {len(self.current_error_positions)}"
                f" · Fehlerereignisse: {event_count}"
                f" · häufigster Fehlzug: {top.count}× · erwartet: {expected} · gespielt: {played}"
            )

        self.stats_var.set(text)
        self._update_ui_state()

    def _update_variant_sort_headers(self) -> None:
        labels = {
            "category": "Gruppe",
            "source": "Quelle",
            "variant": "Variante",
            "due": "Fällig",
            "attempts": "Versuche",
            "wrong": "Fehler",
            "accuracy": "Trefferquote",
            "plies": "Halbzüge",
            "status": "Status",
        }

        for column, label in labels.items():
            if column == self.variant_sort_column:
                arrow = "▼" if self.variant_sort_reverse else "▲"
            else:
                arrow = "⇅"

            self.variant_table.heading(
                column,
                text=f"{label} {arrow}",
                command=lambda col=column: self._sort_variant_table(col),
            )

    @staticmethod
    def _due_sort_key(text: str) -> int:
        text = text.strip()
        if text == "heute":
            return 0
        if text == "morgen":
            return 1
        if text.startswith("in ") and text.endswith("Tagen"):
            try:
                return int(text[3:-6])
            except ValueError:
                return 9000
        if text == "neu":
            return 9000   # neue Varianten ans Ende der Fälligkeit
        return 9999       # "—" (keine Züge) ganz zuletzt

    def _sort_variant_table(self, column: str, keep_direction: bool = False) -> None:
        if not keep_direction:
            if self.variant_sort_column == column:
                self.variant_sort_reverse = not self.variant_sort_reverse
            else:
                self.variant_sort_column = column
                self.variant_sort_reverse = False
        else:
            self.variant_sort_column = column

        rows = []
        for item_id in self.variant_table.get_children():
            value = self.variant_table.set(item_id, column)
            if column in {"attempts", "wrong", "plies"}:
                try:
                    key = int(value)
                except ValueError:
                    key = 0
            elif column == "accuracy":
                try:
                    key = int(value.replace("%", "").strip())
                except ValueError:
                    key = -1
            elif column == "due":
                key = self._due_sort_key(value)
            else:
                key = value.casefold()
            rows.append((key, item_id))

        rows.sort(key=lambda row: row[0], reverse=self.variant_sort_reverse)

        for position, (_, item_id) in enumerate(rows):
            self.variant_table.move(item_id, "", position)

        self._update_variant_sort_headers()

    def _selected_line(self) -> OpeningLine | None:
        selection = self.variant_table.selection()
        if not selection:
            return None

        try:
            index = int(selection[0])
        except ValueError:
            return None

        if index < 0 or index >= len(self.lines):
            return None
        return self.lines[index]

    def _select_current_line_in_table(self) -> None:
        """Markiert die gerade trainierte Variante in der Tabelle, damit man
        sieht, welche Variante läuft (besonders in der Wiederholung)."""
        if self.current_line is None:
            return
        try:
            index = self.lines.index(self.current_line)
        except ValueError:
            return
        iid = str(index)
        if self.variant_table.exists(iid):
            self.variant_table.selection_set(iid)
            self.variant_table.see(iid)

    def _set_mode(self, mode: AppMode) -> None:
        self.mode = mode
        self._refresh_mode_line()
        self._focus_tab_for_mode()

    def _focus_tab_for_mode(self) -> None:
        target = tab_for_mode(self.mode)
        if target == TAB_ERRORS:
            self.notebook.select(self._errors_tab)
        elif target == TAB_LIBRARY:
            self.notebook.select(self._library_tab)

    def _refresh_mode_line(self) -> None:
        if self.error_session is not None:
            self.mode_var.set(
                session_mode_text(
                    self.mode.value,
                    self.error_session.index,
                    self.error_session.total,
                    self.error_session.correct,
                    self.error_session.wrong,
                )
            )
        elif self.training_run is not None:
            self.mode_var.set(f"Modus: {self.mode.value} · {self.training_run.progress_text()}")
        else:
            self.mode_var.set(f"Modus: {self.mode.value}")

    @staticmethod
    def _tk_state(enabled: bool) -> str:
        return tk.NORMAL if enabled else tk.DISABLED

    def _update_ui_state(self) -> None:
        states = button_states(
            UiStateInput(
                has_selected_line=self._selected_line() is not None,
                has_current_line=self.current_line is not None,
                has_training=self.training is not None,
                mode=self.mode,
                error_panel_active=self.error_panel_active,
                has_error_rows=bool(self.error_list.get_children()),
                has_error_selection=bool(self.error_list.selection()),
                has_error_session=self.error_session is not None,
                has_lines=bool(self.lines),
                set_line_finished=self._set_line_finished,
            )
        )

        self.start_button.configure(state=self._tk_state(states.start))
        self.restart_button.configure(state=self._tk_state(states.restart))
        self.undo_button.configure(state=self._tk_state(states.undo))
        self.solution_button.configure(state=self._tk_state(states.solution))
        self.repeat_button.configure(state=self._tk_state(states.repeat))
        self.next_line_button.configure(state=self._tk_state(states.next_line))

        if hasattr(self, "tree_train_white_button"):
            self.tree_train_white_button.configure(state=self._tk_state(states.train_white))
            self.tree_train_black_button.configure(state=self._tk_state(states.train_black))
            self._update_tree_action_buttons()

        self.wrong_session_button.configure(state=self._tk_state(states.wrong_session))
        self.selected_error_button.configure(state=self._tk_state(states.selected_error))
        self.session_next_button.configure(state=self._tk_state(states.session_next))

    def _start_training(self) -> None:
        line = self._selected_line()
        if line is None:
            self.status_var.set("Bitte zuerst eine Variante auswählen.")
            return

        if not line.moves_uci:
            self.status_var.set("Diese Variante enthält keine Züge und kann nicht trainiert werden.")
            return

        self._set_mode(AppMode.VARIANT_TRAINING)
        self.training = TrainingState(line, train_color=self.train_color)
        self.current_line = line
        self.selected_square = None
        self.error_panel_active = False
        self.error_training_active = False
        self.error_session = None
        self.training_run = None
        self._set_line_finished = False
        self.board_widget.set_board(self.training.board)
        self.board_widget.set_wrong_move(None)
        self.board_widget.set_solution(None)
        self.board_widget.set_last_move(self.training.last_move_uci)

        solution = self.training.expected_solution()
        if solution:
            if self.train_color == chess.BLACK and self.training.last_move_uci:
                self.status_var.set(
                    f"Training gestartet. Programm hat Weiß eröffnet. Erwarteter schwarzer Zug: {solution.san}"
                )
            else:
                self.status_var.set(f"Training gestartet. Erwarteter erster Zug: {solution.san}")
            self._update_progress()
            self._update_stats_display()
            self._update_ui_state()
        else:
            self.status_var.set("Training gestartet. Variante enthält keine Züge.")
            self._update_progress()
            self._update_stats_display()

    # --- Set-/Repertoire-Training -----------------------------------------

    def _apply_train_color(self, color: chess.Color) -> None:
        self.train_color = color
        self.train_colour_var.set("white" if color == chess.WHITE else "black")
        self.board_widget.set_flipped(color == chess.BLACK)
        self.board_widget.set_hover_piece_colour(color)
        self._save_settings()

    def _start_repertoire_training(self, side: str) -> None:
        if not self.lines:
            self.status_var.set("Bitte zuerst eine PGN laden.")
            return

        label = "Weiß-Repertoire" if side == SIDE_WHITE else "Schwarz-Repertoire"
        lines = [
            line
            for line in self.repertoire_store.repertoire.lines_for_side(side, self.lines)
            if line.moves_uci
        ]
        if not lines:
            self.status_var.set(
                f"Das {label} enthält keine trainierbaren Varianten. "
                "Ordne im Reiter „Repertoire“ Gruppen dieser Seite zu."
            )
            return

        self._apply_train_color(chess.WHITE if side == SIDE_WHITE else chess.BLACK)
        self._begin_set(lines, label)

    def _start_tree_group_training(self) -> None:
        name = self._selected_tree_group()
        if name is None:
            self.status_var.set("Bitte zuerst eine Gruppe im Baum auswählen.")
            return
        self._start_group_training_for(name)

    def _start_group_training_for(self, name: str) -> None:
        if not self.lines:
            self.status_var.set("Bitte zuerst eine PGN laden.")
            return

        repertoire = self.repertoire_store.repertoire
        lines = [line for line in repertoire.lines_for_category(name, self.lines) if line.moves_uci]
        if not lines:
            self.status_var.set(f"Die Gruppe {name} enthält keine trainierbaren Varianten.")
            return

        category = repertoire.category(name)
        if category is not None and category.side == SIDE_WHITE:
            self._apply_train_color(chess.WHITE)
        elif category is not None and category.side == SIDE_BLACK:
            self._apply_train_color(chess.BLACK)

        self._begin_set(lines, f"Gruppe {name}")

    def _begin_set(self, lines: list[OpeningLine], label: str) -> None:
        if self.order_var.get() == "Schwächste zuerst":
            lines = self.stats_store.order_lines_weakest_first(lines)
            label = f"{label} (schwächste zuerst)"

        self.training_run = TrainingRun(lines=lines)
        self._set_label = label
        self._set_line_finished = False
        self._review_active = False
        self.error_panel_active = False
        self.error_training_active = False
        self.error_session = None
        self._set_mode(AppMode.SET_TRAINING)
        self.status_var.set(f"{label} gestartet: {len(lines)} Varianten.")
        self._start_set_line(self.training_run.current_line())

    def _start_set_line(self, line: OpeningLine | None) -> None:
        if line is None:
            return

        self._set_line_had_wrong = False
        self.training = TrainingState(line, train_color=self.train_color)
        self.current_line = line
        self.selected_square = None
        self._select_current_line_in_table()
        self.board_widget.set_board(self.training.board)
        self.board_widget.set_wrong_move(None)
        self.board_widget.set_solution(None)
        self.board_widget.set_last_move(self.training.last_move_uci)

        prefix = self.training_run.progress_text()
        solution = self.training.expected_solution()
        if solution:
            self.status_var.set(f"{prefix} · {line.name} · erwartet: {solution.san}")
        else:
            self.status_var.set(f"{prefix} · {line.name}")
        self._refresh_mode_line()
        self._update_progress()
        self._update_stats_display()
        self._update_ui_state()

    def _handle_set_line_progress(self, result) -> None:
        # Wird nur bei korrektem Zug im Set-Training aufgerufen.
        if self.training is not None and self.training.is_finished():
            if self._set_line_had_wrong:
                self.training_run.mark_wrong()
            else:
                self.training_run.mark_correct()
            self._set_line_finished = True

            if self._review_active and self.current_line is not None:
                passed = not self._set_line_had_wrong
                card = self.schedule_store.card_for(self.current_line.source_name, self.current_line.name)
                self.schedule_store.set_card(
                    self.current_line.source_name,
                    self.current_line.name,
                    schedule_review(card, passed, date.today()),
                )
                self.schedule_store.save(self.schedule_path)
            if self.training_run.current_display_index() >= self.training_run.total:
                hint = "Letzte Variante — „Nächste Variante“ schließt das Set ab."
            else:
                hint = "Weiter mit „Nächste Variante“."
            self.status_var.set(f"Variante abgeschlossen · {self.training_run.progress_text()}. {hint}")
            self._refresh_mode_line()
            self._update_ui_state()
            self.next_line_button.focus_set()
        else:
            self.status_var.set(f"{self.training_run.progress_text()} · {result.message}")

    def _on_next_line_key(self, _event=None) -> None:
        # Enter schaltet im Set zur nächsten Variante, aber nur wenn eine Variante
        # fertig ist und der Fokus nicht in einem Eingabefeld liegt.
        focus = self.focus_get()
        if isinstance(focus, (tk.Entry, ttk.Entry, ttk.Combobox)):
            return
        if self.training_run is not None and self._set_line_finished:
            self._continue_set_training()

    def _continue_set_training(self) -> None:
        if self.training_run is None:
            self.status_var.set("Kein Set-Training aktiv.")
            return

        next_line = self.training_run.advance()
        if next_line is None:
            self._finish_set_training()
            return

        self._set_line_finished = False
        self._start_set_line(next_line)

    def _finish_set_training(self) -> None:
        run = self.training_run
        set_stats = self.stats_store.stats_for_lines(run.lines)
        percent = round(set_stats.accuracy * 100) if set_stats.attempts else 0
        self.status_var.set(
            f"{self._set_label} abgeschlossen: {run.total} Varianten · "
            f"fehlerfrei {run.correct} · mit Fehler {run.wrong}. "
            f"Trefferquote {percent} % · {set_stats.lines_trained}/{set_stats.lines_total} Varianten geübt."
        )
        self.training_run = None
        self._set_line_finished = False
        self._review_active = False
        self._set_mode(AppMode.IDLE)
        self._refresh_variant_table()
        self._update_due_count()
        self._update_ui_state()

    def _update_due_count(self) -> None:
        if not hasattr(self, "due_var"):
            return
        if not self.lines:
            self.due_var.set("Heute zu wiederholen: — (PGN laden)")
            return
        count = len(self.schedule_store.due_lines(self.lines, date.today()))
        self.due_var.set(f"Heute zu wiederholen: {count} " + ("Variante" if count == 1 else "Varianten"))

    def _start_review(self) -> None:
        if not self.lines:
            self.status_var.set("Bitte zuerst eine PGN laden.")
            return
        due = self.schedule_store.due_lines(self.lines, date.today())
        if not due:
            self.status_var.set("Heute ist nichts fällig — gut gemacht. Schau morgen wieder vorbei.")
            return
        self._begin_set(due, "Wiederholung")
        self._review_active = True
        self.status_var.set(f"Wiederholung gestartet: {len(due)} fällige Varianten.")

    def _on_trainable_hover(self, square: chess.Square) -> None:
        if self.training is None:
            return

        if self.training.last_wrong_uci is not None:
            self.training.clear_wrong_marker()
            self.board_widget.set_wrong_move(None)

    def _on_drag_move(self, from_square: chess.Square, to_square: chess.Square) -> None:
        if self.training is None:
            self.status_var.set("Bitte zuerst Training starten.")
            return
        self.selected_square = None
        self._play_move(chess.Move(from_square, to_square).uci())

    def _on_square_click(self, square: chess.Square) -> None:
        if self.training is None:
            self.status_var.set("Bitte zuerst Training starten.")
            return

        if self.selected_square is None:
            piece = self.training.board.piece_at(square)
            if piece is None:
                self.status_var.set("Bitte eine eigene Figur anklicken.")
                return
            if piece.color != self.train_color:
                side = "weiße" if self.train_color == chess.WHITE else "schwarze"
                self.status_var.set(f"Bitte eine {side} Figur anklicken.")
                return

            self.selected_square = square
            self.status_var.set(f"Startfeld gewählt: {chess.square_name(square)}")
            return

        move = chess.Move(self.selected_square, square)
        self.selected_square = None
        self._play_move(move.uci())

    def _record_training_event(self, *, correct: bool, expected_san: str | None, played_san: str | None, fen_before: str) -> None:
        if self.current_line is None:
            return

        self.stats_store.add_event(
            source_name=self.current_line.source_name,
            line_name=self.current_line.name,
            fen_before=fen_before,
            expected_san=expected_san,
            played_san=played_san,
            correct=correct,
        )
        self.stats_store.save(self.stats_path)
        self._update_stats_display()
        self._refresh_progress_tab()

    def _play_move(self, move_uci: str) -> None:
        assert self.training is not None

        fen_before = self.training.board.fen()
        result = self.training.play_user_move_uci(move_uci)

        if result.kind == "wrong":
            self._record_training_event(
                correct=False,
                expected_san=result.expected_san,
                played_san=result.played_san,
                fen_before=fen_before,
            )
            if self.error_session is not None:
                self.error_session.mark_wrong()
                self._refresh_mode_line()
            if self.training_run is not None:
                self._set_line_had_wrong = True

            self.board_widget.set_board(self.training.board)
            self.board_widget.set_wrong_move(result.wrong_uci)
            self.status_var.set(
                f"{result.message} Erwartet: {result.expected_san}. Gespielt: {result.played_san}."
            )
            self._update_progress()
            return

        if result.kind == "correct":
            self._record_training_event(
                correct=True,
                expected_san=result.expected_san,
                played_san=result.played_san,
                fen_before=fen_before,
            )

        self.board_widget.set_board(self.training.board)
        self.board_widget.set_wrong_move(None)
        self.board_widget.set_solution(None)
        self.board_widget.set_last_move(result.last_move_uci)
        self.board_widget.animate_move(result.last_move_uci)

        if result.kind == "correct" and self.training_run is not None:
            self._handle_set_line_progress(result)
            self._update_progress()
            return

        if result.kind == "correct" and self.error_training_active and self.current_line is not None:
            if self.error_session is not None:
                self.error_session.mark_correct()
                self._refresh_mode_line()

            wrong_count = len(
                self.stats_store.wrong_move_summary_for_line(
                    source_name=self.current_line.source_name,
                    line_name=self.current_line.name,
                )
            )

            if self.error_session is not None:
                history = wrong_move_history_text(self.active_error_position)
                self.status_var.set(
                    solved_session_message(
                        self.error_session.index,
                        self.error_session.total,
                        history,
                        self.error_session.correct,
                        self.error_session.wrong,
                    )
                )
            elif wrong_count == 0:
                self.status_var.set("Fehler korrekt gelöst. Für diese Variante sind keine Fehlzüge protokolliert.")
            elif wrong_count == 1:
                self.status_var.set("Fehler korrekt gelöst. Im Protokoll bleibt 1 Fehlzug gespeichert.")
            else:
                self.status_var.set(f"Fehler korrekt gelöst. Im Protokoll bleiben {wrong_count} Fehlzüge gespeichert.")

            self.error_training_active = False
            if self.active_error_position is not None:
                self._select_error_position_in_table(self.active_error_position)
        else:
            self.status_var.set(result.message)

        self._update_progress()

    def _undo(self) -> None:
        if self.training is None:
            self.status_var.set("Kein Training aktiv.")
            return

        message = self.training.undo()
        self.selected_square = None
        self.board_widget.set_board(self.training.board)
        self.board_widget.set_wrong_move(None)
        self.board_widget.set_solution(None)
        self.board_widget.set_last_move(self.training.last_move_uci)
        self.status_var.set(message)
        self._update_progress()

    def _show_solution(self) -> None:
        if self.training is None:
            self.status_var.set("Kein Training aktiv.")
            return

        solution = self.training.expected_solution()
        if solution is None:
            self.status_var.set("Keine Lösung: Variante ist beendet.")
            return

        self.board_widget.set_solution(solution.uci)
        self.status_var.set(f"Lösung: {solution.san}")

    def _repeat_until_here(self) -> None:
        if self.training is None:
            self.status_var.set("Kein Training aktiv.")
            return

        self._set_mode(AppMode.SECTION_TRAINING)
        message = self.training.repeat_until_here()
        self.selected_square = None
        self.board_widget.set_board(self.training.board)
        self.board_widget.set_wrong_move(None)
        self.board_widget.set_solution(None)
        self.board_widget.set_last_move(self.training.last_move_uci)

        solution = self.training.expected_solution()
        if solution:
            self.status_var.set(f"{message} Erwartet: {solution.san}")
            self._update_progress()
        else:
            self.status_var.set(message)
            self._update_progress()

    def _update_error_sort_headers(self) -> None:
        labels = {
            "count": "Anzahl",
            "kind": "Typ",
            "expected": "Erwartet",
            "last_played": "Gespielt",
            "last_timestamp": "Letzter Fehler",
        }

        for column, label in labels.items():
            if column == self.error_sort_column:
                arrow = "▼" if self.error_sort_reverse else "▲"
            else:
                arrow = "⇅"

            self.error_list.heading(
                column,
                text=f"{label} {arrow}",
                command=lambda col=column: self._sort_error_table(col),
            )

    def _sort_error_table(self, column: str, keep_direction: bool = False) -> None:
        if not keep_direction:
            if self.error_sort_column == column:
                self.error_sort_reverse = not self.error_sort_reverse
            else:
                self.error_sort_column = column
                self.error_sort_reverse = False
        else:
            self.error_sort_column = column

        rows = []
        for item_id in self.error_list.get_children():
            value = self.error_list.set(item_id, column)
            if column == "count":
                try:
                    key = int(value.replace("×", "").strip())
                except ValueError:
                    key = 0
            else:
                key = value.casefold()
            rows.append((key, item_id))

        rows.sort(key=lambda row: row[0], reverse=self.error_sort_reverse)

        for position, (_, item_id) in enumerate(rows):
            self.error_list.move(item_id, "", position)

        self._update_error_sort_headers()

    def _wrong_summary_kind(self, summary) -> str:
        if self._is_input_error_summary(summary):
            return "Eingabefehler"
        return "Fehlzug"

    def _is_input_error_summary(self, error_position) -> bool:
        played = getattr(error_position, "played_san", None)
        if not played:
            return False

        if len(played) == 4 and played[0] in "abcdefgh" and played[2] in "abcdefgh":
            return played[:2] == played[2:]

        return False

    def _trainable_wrong_summaries_for_current_line(self):
        if self.current_line is None:
            return []

        summaries = self.stats_store.wrong_move_summary_for_line(
            source_name=self.current_line.source_name,
            line_name=self.current_line.name,
        )

        return [
            summary
            for summary in summaries
            if not self._is_input_error_summary(summary)
        ]

    def _trainable_error_positions(self):
        positions = []
        for item_id in self.error_list.get_children():
            try:
                index = int(item_id)
            except ValueError:
                continue

            if 0 <= index < len(self.current_error_positions):
                position = self.current_error_positions[index]
                if not self._is_input_error_summary(position):
                    positions.append(position)

        return positions

    def _clear_active_error_tag(self) -> None:
        for item_id in self.error_list.get_children():
            tags = tuple(tag for tag in self.error_list.item(item_id, "tags") if tag != "active_error")
            self.error_list.item(item_id, tags=tags)

    def _select_error_position_in_table(self, error_position) -> None:
        for index, position in enumerate(self.current_error_positions):
            if (
                getattr(position, "fen_before", None) == getattr(error_position, "fen_before", None)
                and getattr(position, "expected_san", None) == getattr(error_position, "expected_san", None)
                and getattr(position, "played_san", None) == getattr(error_position, "played_san", None)
            ):
                item_id = str(index)
                if self.error_list.exists(item_id):
                    self._clear_active_error_tag()
                    self.error_list.selection_set(item_id)
                    self.error_list.focus(item_id)
                    self.error_list.see(item_id)
                    current_tags = tuple(self.error_list.item(item_id, "tags"))
                    if "active_error" not in current_tags:
                        self.error_list.item(item_id, tags=current_tags + ("active_error",))
                    self._update_error_detail()
                return

    def _summary_reachable(self, summary) -> bool:
        """Liegt die gespeicherte Fehlerstellung tatsächlich in der aktuellen
        Variante? Schützt vor falsch beschrifteten Altdaten (Stellung gehört zu
        einer anderen Variante) – solche Einträge sind hier nicht trainierbar."""
        line = self.current_line
        if line is None:
            return False
        fen = getattr(summary, "fen_before", None)
        if not fen:
            return False
        return TrainingState(line, train_color=self.train_color).jump_to_fen(fen)

    def _start_error_training_from_position(self, line: OpeningLine, error_position) -> bool:
        if self._is_input_error_summary(error_position):
            self.status_var.set("Dieser Eintrag ist ein Eingabefehler und nicht als Fehlzug trainierbar.")
            return False

        training = TrainingState(line, train_color=self.train_color)
        found = training.jump_to_fen(error_position.fen_before)

        if not found:
            self.status_var.set("Die gespeicherte Fehlerstellung wurde in dieser Variante nicht gefunden.")
            return False

        self._set_mode(AppMode.WRONG_MOVE_SESSION)
        self.training = training
        self.current_line = line
        self.selected_square = None
        self.error_training_active = True
        self.active_error_position = error_position
        self.training_run = None
        self._set_line_finished = False

        self.board_widget.set_board(self.training.board)
        self.board_widget.set_wrong_move(None)
        self.board_widget.set_solution(None)
        self.board_widget.set_last_move(self.training.last_move_uci)

        solution = self.training.expected_solution()
        error_count = getattr(error_position, "wrong_count", getattr(error_position, "count", 0))
        if solution:
            self.status_var.set(
                f"Markierter Fehlzug geladen. Erwartet: {solution.san} · protokolliert: {error_count}×"
            )
        else:
            self.status_var.set("Markierter Fehlzug geladen.")

        self._update_progress()
        self._update_stats_display()
        self._select_error_position_in_table(error_position)
        return True

    def _train_selected_error_position(self) -> None:
        line = self.current_line or self._selected_line()
        if line is None:
            self.status_var.set("Bitte zuerst eine Variante auswählen.")
            return

        selection = self.error_list.selection()
        if not selection:
            self.status_var.set("Bitte zuerst eine Fehlzug-Sitzung starten und dann einen Eintrag auswählen.")
            return

        try:
            table_index = int(selection[0])
        except ValueError:
            self.status_var.set("Die ausgewählte Fehlerstellung ist nicht verfügbar.")
            return

        if table_index < 0 or table_index >= len(self.current_error_positions):
            self.status_var.set("Die ausgewählte Fehlerstellung ist nicht verfügbar.")
            return

        selected_position = self.current_error_positions[table_index]
        if self._is_input_error_summary(selected_position):
            self.status_var.set("Dieser Eintrag ist ein Eingabefehler und nicht trainierbar.")
            return

        session_positions = self._trainable_error_positions()
        if not session_positions:
            self.status_var.set("Für diese Variante gibt es keine trainierbaren Fehlzüge.")
            return

        session_index = session_index_for_selected_problem(session_positions, selected_position)

        if session_index is None:
            self.status_var.set("Der ausgewählte Fehlzug ist in der sichtbaren Trainingsliste nicht verfügbar.")
            return

        self.current_line = line
        self.error_session = WrongMoveSession(positions=session_positions, index=session_index)
        self.error_training_active = False
        self._set_mode(AppMode.WRONG_MOVE_SESSION)
        self._continue_wrong_move_session()

    def _start_wrong_move_session(self) -> None:
        line = self._selected_line() or self.current_line
        if line is None:
            self.status_var.set("Bitte zuerst eine Variante auswählen.")
            return

        self.current_line = line
        self.error_panel_active = True
        self._update_stats_display()

        session_positions = self._trainable_error_positions()
        if not session_positions:
            self.status_var.set("Für diese Variante gibt es keine trainierbaren Fehlzüge.")
            return

        self._set_mode(AppMode.WRONG_MOVE_SESSION)
        self.error_session = WrongMoveSession(positions=session_positions)

        self.status_var.set(
            f"Fehlzug-Sitzung gestartet. {self.error_session.total} Fehlzugprobleme in dieser Sitzung."
        )
        self._continue_wrong_move_session()

    def _continue_wrong_move_session(self) -> None:
        line = self.current_line or self._selected_line()
        if line is None:
            self.status_var.set("Bitte zuerst eine Variante auswählen.")
            return

        if self.error_session is None:
            self.status_var.set("Keine Fehlzug-Sitzung aktiv. Starte zuerst „Fehlzug-Sitzung starten“ oder „Sitzung ab Auswahl starten“.")
            return

        if self.error_session.is_finished:
            self.status_var.set(
                finished_session_message(self.error_session.total, self.error_session.correct, self.error_session.wrong)
            )
            self.error_training_active = False
            self.error_session = None
            self._refresh_mode_line()
            self._update_ui_state()
            return

        skipped = 0
        while True:
            error_position = self.error_session.next_problem()
            if error_position is None:
                if skipped:
                    self.status_var.set(
                        f"Keine auffindbare Fehlerstellung mehr ({skipped} übersprungen, da nicht in dieser Variante)."
                    )
                else:
                    self.status_var.set("Keine weitere Fehlerstellung verfügbar.")
                self.error_training_active = False
                self.error_session = None
                self._refresh_mode_line()
                self._update_ui_state()
                return

            if self._start_error_training_from_position(line, error_position):
                break

            # Stellung gehört nicht zu dieser Variante (z. B. falsch beschriftete
            # Altdaten) – überspringen und zum nächsten Problem.
            skipped += 1
            if self.error_session.is_finished:
                self.status_var.set(
                    f"Keine auffindbare Fehlerstellung ({skipped} übersprungen, da nicht in dieser Variante)."
                )
                self.error_training_active = False
                self.error_session = None
                self._refresh_mode_line()
                self._update_ui_state()
                return

        history = wrong_move_history_text(error_position)
        session_status = loaded_session_message(
            self.error_session.index,
            self.error_session.total,
            history,
            self.error_session.correct,
            self.error_session.wrong,
        )
        self.status_var.set(session_status)
        self._update_ui_state()

    def _restart(self) -> None:
        if self.training is None:
            self.status_var.set("Kein Training aktiv.")
            return

        self.training.restart_full_line()
        self.selected_square = None
        self.error_training_active = False
        self.board_widget.set_board(self.training.board)
        self.board_widget.clear_marks()
        self.board_widget.set_last_move(self.training.last_move_uci)

        solution = self.training.expected_solution()
        if solution:
            self.status_var.set(f"Variante neu gestartet. Erwartet: {solution.san}")
            self._update_progress()
        else:
            self.status_var.set("Variante neu gestartet.")
            self._update_progress()
