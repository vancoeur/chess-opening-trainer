"""A daily 'due positions' session across the whole tree repertoire.

Maps each of the trained side's positions (epd) to one place in the trees where it
occurs, then asks the per-position schedule which are due today. Transpositions
share one epd → one card, so the same position isn't reviewed twice in a day.
Pure (no UI); the UI starts a ``PositionTrainer`` at each returned (tree, node).
"""
from __future__ import annotations

from datetime import date, timedelta

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
