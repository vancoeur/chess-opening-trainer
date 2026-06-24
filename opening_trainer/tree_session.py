"""A daily 'due positions' session across the whole tree repertoire.

Maps each of the trained side's positions (epd) to one place in the trees where it
occurs, then asks the per-position schedule which are due today. Transpositions
share one epd → one card, so the same position isn't reviewed twice in a day.
Pure (no UI); the UI starts a ``PositionTrainer`` at each returned (tree, node).
"""
from __future__ import annotations

from datetime import date, timedelta

import chess

from opening_trainer.position_book import _start_board, _legal_move, _SIDE_NAME
from opening_trainer.scheduler import is_new, is_due


def build_user_position_index(trees, side) -> dict[str, tuple]:
    """epd -> (tree, node_id) für die erste eigene Stellung (Nutzer am Zug, mit
    vorgesehenem Zug), die diese EPD erreicht. Nur Bäume der passenden Seite."""
    index: dict[str, tuple] = {}
    want = _SIDE_NAME.get(side)
    for tree in trees:
        if tree.side != want:
            continue
        _walk(tree, tree.root, _start_board(tree), side, index)
    return index


def _walk(tree, node, board, side, index) -> None:
    children = tree.children_of(node.id)
    if board.turn == side and children:
        index.setdefault(board.epd(), (tree, node.id))   # erste Fundstelle gewinnt
    for child in children:
        move = _legal_move(board, child.move_uci)
        if move is None:
            continue
        board.push(move)
        _walk(tree, child, board, side, index)
        board.pop()


def due_drill_items(trees, side, schedule, today, new_limit: int = 10) -> list[tuple]:
    """Heute fällige eigene Stellungen als (tree, node_id), in Lernplan-Reihenfolge
    (überfälligste zuerst, dann begrenzt neue)."""
    index = build_user_position_index(trees, side)
    due_epds = schedule.due_positions(list(index.keys()), today, new_limit=new_limit)
    return [index[epd] for epd in due_epds]


def due_items_for_tree(tree, side, schedule, today, new_limit: int = 10) -> list[tuple]:
    """Wie ``due_drill_items``, aber nur für EINEN Baum (gezieltes Üben)."""
    index: dict[str, tuple] = {}
    if tree.side == _SIDE_NAME.get(side):
        _walk(tree, tree.root, _start_board(tree), side, index)
    due_epds = schedule.due_positions(list(index.keys()), today, new_limit=new_limit)
    return [index[epd] for epd in due_epds]


def _tree_user_epds(tree, side) -> set:
    """Alle EPDs, an denen die trainierte Seite in DIESEM Baum am Zug ist (mit
    vorgesehenem Folgezug)."""
    epds: set = set()
    if tree.side != _SIDE_NAME.get(side):
        return epds

    def collect(node, board):
        children = tree.children_of(node.id)
        if board.turn == side and children:
            epds.add(board.epd())
        for child in children:
            move = _legal_move(board, child.move_uci)
            if move is None:
                continue
            board.push(move)
            collect(child, board)
            board.pop()

    collect(tree.root, _start_board(tree))
    return epds


def due_breakdown(trees, side, schedule, today) -> list[dict]:
    """Pro Eröffnung (Baum) der Seite: Name + Anzahl »fällig« + Anzahl »neu«.
    Sortiert: meiste fällige zuerst. (Transpositionen werden pro Baum gezählt.)"""
    want = _SIDE_NAME.get(side)
    out: list[dict] = []
    for tree in trees:
        if tree.side != want:
            continue
        epds = _tree_user_epds(tree, side)
        if not epds:
            continue
        due = new = 0
        for epd in epds:
            card = schedule.card_for(epd)
            if is_new(card):
                new += 1
            elif is_due(card, today):
                due += 1
        out.append({"tree": tree, "name": tree.name, "due": due, "new": new, "total": len(epds)})
    out.sort(key=lambda r: (-r["due"], -r["new"], r["name"]))
    return out


def tree_progress_rows(trees, side, stats_store) -> list[dict]:
    """Pro Eröffnung (Baum) der Seite die aggregierte Positions-Statistik — die
    positions-basierte Ablösung der linien-basierten Fortschrittszeilen.

    Versuche/Treffer werden über alle eigenen Stellungen des Baums summiert
    (FEN-genau, transpositions-bewusst via ``stats_for_position``); die
    Trefferquote ergibt sich daraus. ``positions_total``/``positions_trained``
    machen die Positions-Granularität sichtbar. Bäume ohne eigene Stellung
    werden übersprungen. Einstufung (Eimer) bleibt Sache der UI-Schicht."""
    want = _SIDE_NAME.get(side)
    rows: list[dict] = []
    for tree in trees:
        if tree.side != want:
            continue
        epds = _tree_user_epds(tree, side)
        if not epds:
            continue
        attempts = correct = trained = 0
        for epd in epds:
            s = stats_store.stats_for_position(epd)
            attempts += s.attempts
            correct += s.correct
            if s.attempts > 0:
                trained += 1
        accuracy = correct / attempts if attempts else 0.0
        rows.append({
            "tree": tree,
            "name": tree.name,
            "attempts": attempts,
            "accuracy": accuracy,
            "positions_total": len(epds),
            "positions_trained": trained,
        })
    return rows


def open_error_positions(trees, side, stats_store) -> list[dict]:
    """Offene Fehlerstellungen über das Repertoire der Seite — die
    positions-basierte Ablösung von ``_collect_error_problems``
    (varianten-bewusst, transpositions-dedupliziert).

    Liefert dieselben Dict-Felder wie bisher (``fen``, ``expected_uci``,
    ``expected_san``, ``played``, ``name``, ``count``), damit Anzeige und
    Einzel-Drill unverändert weiterlaufen. Häufigste Fehler zuerst."""
    index = build_user_position_index(trees, side)
    problems: list[dict] = []
    seen: set = set()
    for epd, (tree, _node_id) in index.items():
        for pos in stats_store.error_positions_for_epd(epd):
            if not pos.expected_san:
                continue
            key = (pos.fen_before, pos.expected_san)
            if key in seen:
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
            problems.append({
                "fen": pos.fen_before,
                "expected_uci": expected_uci,
                "expected_san": pos.expected_san,
                "played": pos.last_played_san,
                "name": tree.name,
                "source": tree.name,
                "line": tree.name,
                "count": pos.wrong_count,
            })
    problems.sort(key=lambda p: -p["count"])
    return problems


def due_forecast(trees, side, schedule, today) -> dict:
    """Ausblick über das ganze Repertoire (eigene Stellungen, dedupliziert per EPD):
    wie viele heute (inkl. überfällig), morgen, später diese Woche fällig werden — und neu."""
    want = _SIDE_NAME.get(side)
    epds: set = set()
    for tree in trees:
        if tree.side == want:
            epds |= _tree_user_epds(tree, side)
    tomorrow = today + timedelta(days=1)
    week_end = today + timedelta(days=7)
    res = {"today": 0, "tomorrow": 0, "week": 0, "new": 0}
    for epd in epds:
        card = schedule.card_for(epd)
        if is_new(card):
            res["new"] += 1
            continue
        try:
            d = date.fromisoformat(card.due)
        except ValueError:
            continue
        if d <= today:
            res["today"] += 1
        elif d == tomorrow:
            res["tomorrow"] += 1
        elif d <= week_end:
            res["week"] += 1
    return res
