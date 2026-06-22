"""Hält automatisch erzeugte Repertoire-Bäume + Positions-Karten mit den geladenen
PGN-Quellen in Sync, damit die positions-basierte Tagessitzung (»Heute fällig«) für
JEDES geladene Repertoire funktioniert — nicht nur für die einmal migrierten Daten.

Ein Auto-Baum trägt ``headers["_auto"] == "1"``. Bei jedem Sync werden alle
Auto-Bäume verworfen und varianten-erhaltend (``import_pgn_file``) aus den aktuellen
Quellen neu gebaut. **Editor-/manuell erstellte Bäume (ohne Marke) bleiben
unangetastet.** Zusätzlich werden alte, unmarkierte Bäume entfernt, die ein neuer
Auto-Baum VOLLSTÄNDIG enthält (= die einmal-migrierten Einzweig-Bäume) — so
entstehen keine Dubletten, ohne Editor-/Import-Bäume zu verlieren.

Reines Modul (kein Qt) — wie ``migration_v2`` aufgebaut und testbar.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import chess

from opening_trainer.repertoire_tree import RepertoireTree, WHITE, BLACK, NONE
from opening_trainer.pgn_tree_import import import_pgn_file
from opening_trainer.scheduler import is_new

AUTO = "_auto"
_SIDE_COLOR = {WHITE: chess.WHITE, BLACK: chess.BLACK}
_SEP = "\t"


@dataclass
class SyncReport:
    trees: int = 0
    sided: int = 0
    positions_seeded: int = 0
    removed_legacy: int = 0


def dominant_side(sides, source_name: str) -> str:
    """Häufigste zugeordnete Farbe der Eröffnungen EINER Quelle (Datei).
    Robust gegen Namensunterschiede zwischen den beiden Ladern — die Seite hängt
    an der Quelle, nicht am einzelnen Liniennamen."""
    counts: Counter = Counter()
    for key, side in sides.sides.items():
        sn, _, _ln = key.partition(_SEP)
        if sn == source_name and side in (WHITE, BLACK):
            counts[side] += 1
    return counts.most_common(1)[0][0] if counts else NONE


def pgn_files_of_source(path) -> list[Path]:
    """Eine Quelle (Datei ODER Ordner) zu konkreten .pgn-Dateien auflösen."""
    p = Path(path)
    if p.is_dir():
        return sorted(f for f in p.glob("*.pgn") if f.is_file())
    return [p] if p.is_file() else []


def tree_move_paths(tree: RepertoireTree) -> set:
    """Menge aller Wurzel-zu-Knoten-Zugpfade (UCI-Tupel) eines Baums."""
    paths: set = set()

    def walk(node, path):
        for cid in node.children_ids:
            child = tree.nodes[cid]
            p = path + (child.move_uci,)
            paths.add(p)
            walk(child, p)

    walk(tree.root, ())
    return paths


def _seed_missing(tree: RepertoireTree, side_color, card, position_schedule,
                  report: SyncReport) -> None:
    """Trägt die lineare Karte nur auf NOCH NICHT vorhandene Stellungen des
    Hauptpfades ein — aktiver Lernfortschritt (bereits vorhandene Karten) bleibt
    unangetastet."""
    board = chess.Board(tree.start_fen) if tree.start_fen else chess.Board()
    node = tree.root
    while node.children_ids:
        if board.turn == side_color:
            epd = board.epd()
            if epd not in position_schedule.cards:
                position_schedule.cards[epd] = card
                report.positions_seeded += 1
        child = tree.nodes[node.children_ids[0]]
        move = chess.Move.from_uci(child.move_uci) if child.move_uci else None
        if move is None or move not in board.legal_moves:
            break
        board.push(move)
        node = child


def sync_auto_trees(sources, sides, schedule, tree_store, position_schedule) -> SyncReport:
    """Baut die Auto-Bäume aus den Quellen neu und seedet die Positions-Karten.

    ``sources``: iterierbar über Quell-Pfade (Datei oder Ordner).
    ``sides``: OpeningSides. ``schedule``: linearer ScheduleStore.
    ``tree_store``/``position_schedule`` werden in-place aktualisiert."""
    report = SyncReport()

    # 1) bisherige Auto-Bäume verwerfen (Editor-Bäume ohne Marke bleiben)
    for tid in [t.id for t in tree_store.all() if t.headers.get(AUTO) == "1"]:
        tree_store.remove(tid)

    # 2) pro Quelldatei varianten-erhaltend neu bauen + Karten seeden
    auto_paths_by_side: dict = {}
    for src in sources:
        for f in pgn_files_of_source(src):
            source_name = f.name
            side = dominant_side(sides, source_name)
            try:
                trees = import_pgn_file(f, side=side)
            except Exception:  # noqa: BLE001 — eine kaputte Quelle blockiert die anderen nicht
                continue
            for tr in trees:
                tr.headers[AUTO] = "1"
                tr.headers["_source"] = source_name
                tree_store.add(tr)
                report.trees += 1
                auto_paths_by_side.setdefault(tr.side, []).append(tree_move_paths(tr))
                if side in _SIDE_COLOR:
                    report.sided += 1
                    card = schedule.card_for(source_name, tr.name)
                    if not is_new(card):
                        _seed_missing(tr, _SIDE_COLOR[side], card, position_schedule, report)

    # 3) alte unmarkierte Bäume entfernen, die ein Auto-Baum derselben Seite
    #    VOLLSTÄNDIG enthält (= einmal-migrierte Einzweig-Bäume). Editor-/Import-
    #    Bäume mit eigenem Inhalt sind kein Teilbaum und bleiben erhalten.
    for t in list(tree_store.all()):
        if t.headers.get(AUTO) == "1":
            continue
        paths = tree_move_paths(t)
        if paths and any(paths <= ap for ap in auto_paths_by_side.get(t.side, [])):
            tree_store.remove(t.id)
            report.removed_legacy += 1

    return report
