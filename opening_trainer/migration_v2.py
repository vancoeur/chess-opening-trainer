"""One-shot migration from linear (source, line)-keyed data to trees + per-position cards.

Constraint: preserve months of data. Mapping fidelity (honest):
- **Stats: perfect, no work** — events are already FEN-keyed and read by epd
  (``stats_store.stats_for_position``); the events file is left untouched.
- **Sides: perfect** — each line's side becomes its single-path tree's ``side``.
- **Notes: kept** — a per-line note moves to the tree's root comment.
- **Schedule: best approximation** — a line card has no single position, so it is
  copied onto every trained-side position of the line's path; on a transposition
  collision the *stronger* card wins (more reps, then earlier due). Never resets a
  position the user already knew. A perfect 1:1 line→positions mapping is impossible.

``migrate_data`` is pure; ``run_migration`` adds backup + idempotency + dry-run.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

import chess

from opening_trainer.pgn_loader import OpeningLine
from opening_trainer.repertoire_tree import RepertoireTree, WHITE, BLACK, NONE
from opening_trainer.repertoire_tree_store import RepertoireTreeStore
from opening_trainer.position_schedule_store import PositionScheduleStore
from opening_trainer.scheduler import Card, is_new
from opening_trainer.opening_sides import OpeningSides
from opening_trainer.schedule_store import ScheduleStore
from opening_trainer.line_notes import LineNotes

_SIDE_COLOR = {WHITE: chess.WHITE, BLACK: chess.BLACK}

MARKER_NAME = ".migrated_to_trees"


@dataclass
class MigrationReport:
    trees: int = 0
    sided_trees: int = 0
    positions_seeded: int = 0
    collisions: int = 0
    notes_migrated: int = 0
    skipped: bool = False
    reason: str = ""

    def summary(self) -> str:
        if self.skipped:
            return f"Migration übersprungen ({self.reason})."
        return (
            f"{self.trees} Bäume ({self.sided_trees} mit Seite), "
            f"{self.positions_seeded} Stellungen in den Lernplan übernommen, "
            f"{self.collisions} Transpositions-Kollisionen aufgelöst, "
            f"{self.notes_migrated} Notizen übernommen."
        )


def tree_from_line(line: OpeningLine, side: str) -> RepertoireTree:
    """Einzel-Pfad-Baum aus einer linearen Linie (verlustfrei für lineare Daten)."""
    tree = RepertoireTree.new(name=line.name, side=side)
    tree.headers = dict(line.headers)
    parent = tree.root_id
    for uci in line.moves_uci:
        parent = tree.add_child(parent, uci).id
    return tree


def stronger_card(a: Card, b: Card) -> Card:
    """Behält die »stärkere« Karte: mehr reps, bei Gleichstand frühere Fälligkeit."""
    if a.reps != b.reps:
        return a if a.reps > b.reps else b
    if not a.due:
        return b
    if not b.due:
        return a
    return a if a.due <= b.due else b


def _seed_positions(tree: RepertoireTree, side_color, card: Card,
                    sched: PositionScheduleStore, report: MigrationReport) -> None:
    """Kopiert die Linien-Karte auf alle eigenen Stellungen des Hauptpfades."""
    board = chess.Board(tree.start_fen) if tree.start_fen else chess.Board()
    node = tree.root
    while node.children_ids:
        if board.turn == side_color:
            epd = board.epd()
            existing = sched.cards.get(epd)
            if existing is None:
                sched.cards[epd] = card
                report.positions_seeded += 1
            else:
                sched.cards[epd] = stronger_card(existing, card)
                report.collisions += 1
        child = tree.nodes[node.children_ids[0]]
        move = chess.Move.from_uci(child.move_uci) if child.move_uci else None
        if move is None or move not in board.legal_moves:
            break
        board.push(move)
        node = child


def migrate_data(lines, sides: OpeningSides, schedule: ScheduleStore,
                 notes: LineNotes) -> tuple[RepertoireTreeStore, PositionScheduleStore, MigrationReport]:
    """Reine Migration: Linien + Bestandsdaten -> Bäume + Stellungs-Lernplan."""
    tree_store = RepertoireTreeStore()
    sched = PositionScheduleStore()
    report = MigrationReport()

    for line in lines:
        side = sides.side_of(line.source_name, line.name) or NONE
        tree = tree_from_line(line, side)
        note = notes.note_of(line.source_name, line.name)
        if note:
            tree.root.comment = note
            report.notes_migrated += 1
        tree_store.add(tree)
        report.trees += 1

        if side in _SIDE_COLOR:
            report.sided_trees += 1
            card = schedule.card_for(line.source_name, line.name)
            if not is_new(card):           # nur bereits terminierte Linien tragen Karten bei
                _seed_positions(tree, _SIDE_COLOR[side], card, sched, report)

    return tree_store, sched, report


def run_migration(data_dir, lines, *, dry_run: bool = False, force: bool = False) -> MigrationReport:
    """Datei-Orchestrierung: idempotent (Markierdatei), mit Backup und Dry-Run.

    ``lines`` werden vom Aufrufer geladen (die App kennt den PGN-Ordner). Die
    Bestandsdaten (Seiten/Lernplan/Notizen) liest die Migration aus ``data_dir``.
    """
    data_dir = Path(data_dir)
    marker = data_dir / MARKER_NAME
    if marker.exists() and not force:
        return MigrationReport(skipped=True, reason="bereits migriert")

    sides = OpeningSides.load(data_dir / "opening_sides.json")
    schedule = ScheduleStore.load(data_dir / "schedule.json")
    notes = LineNotes.load(data_dir / "line_notes.json")

    tree_store, sched, report = migrate_data(lines, sides, schedule, notes)

    if dry_run:
        report.reason = "dry-run"
        return report

    for fn in ("opening_sides.json", "schedule.json", "line_notes.json"):
        src = data_dir / fn
        if src.exists():
            shutil.copy2(src, data_dir / f"{fn}.backup-pre-trees")

    tree_store.save(data_dir / "repertoire_trees.json")
    sched.save(data_dir / "position_schedule.json")
    marker.write_text("ok", encoding="utf-8")
    return report
