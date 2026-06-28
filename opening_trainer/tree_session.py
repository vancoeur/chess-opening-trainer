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


def merge_side_trees(trees, side):
    """Verschmilzt alle Bäume EINER Seite zu EINEM verzweigten Übersichtsbaum
    (Zug-Trie): gemeinsame Zugfolgen werden zusammengeführt, an der ersten
    Abweichung entsteht ein Ast. So wird aus vielen getrennten geraden Linien
    ein einziger Repertoire-Baum. Reine Funktion (nutzt ``add_child``-Dedupe).

    Nur Bäume mit Standard-Grundstellung (kein eigenes ``start_fen``) werden
    zusammengeführt, damit das Verschmelzen über die Zugfolge eindeutig bleibt."""
    from opening_trainer.repertoire_tree import RepertoireTree
    want = _SIDE_NAME.get(side)
    combined = RepertoireTree.new("", want)
    for tree in trees:
        if tree.side != want or tree.start_fen:
            continue

        def walk(src_id, dst_id):
            for child in tree.children_of(src_id):
                # Der Name der Quell-Linie wird am ENDE der Linie (Blatt) als
                # Kommentar mitgeführt -> der verschmolzene Baum behält die
                # Eröffnungsnamen (z. B. »B18 · Caro-Kann: Klassisch«).
                is_leaf = not tree.children_of(child.id)
                comment = child.comment or (tree.name if is_leaf else "")
                dst_child = combined.add_child(dst_id, child.move_uci, comment)
                walk(child.id, dst_child.id)

        walk(tree.root_id, combined.root_id)
    return combined


def overview_rows(tree, side) -> list[dict]:
    """Flache, eingerückte Zeilen eines (Übersichts-)Baums für die Anzeige.

    Eine Zeile je Halbzug, in Vorreihenfolge (Tiefe = Einrückung, mehrere Kinder
    eines Knotens = Verzweigung). Felder: ``depth``, ``label`` (z. B. »3.e5« /
    »3…Lf5«), ``fen_before`` (Stellung vor dem Zug — Drill-Ziel bei eigenen
    Zügen), ``is_user_move``, ``children`` (Kinderzahl = Verzweigungsgrad),
    ``comment``."""
    rows: list[dict] = []
    board = _start_board(tree)

    def walk(node, depth):
        # Einrückung nur an echten Verzweigungen: das erste Kind setzt die
        # Hauptlinie auf gleicher Ebene fort, weitere Kinder (Varianten) rücken
        # eine Ebene ein (PGN-Stil) — sonst liefe eine 30-Zug-Linie aus dem Bild.
        kids = tree.children_of(node.id)
        for i, child in enumerate(kids):
            move = _legal_move(board, child.move_uci)
            if move is None:
                continue
            san = board.san(move)
            fullmove = board.fullmove_number
            white = board.turn == chess.WHITE
            label = f"{fullmove}.{san}" if white else f"{fullmove}…{san}"
            child_depth = depth if i == 0 else depth + 1
            rows.append({
                "depth": child_depth,
                "label": label,
                "move_uci": child.move_uci,
                "fen_before": board.fen(),
                "is_user_move": board.turn == side,
                "children": len(tree.children_of(child.id)),
                "comment": child.comment,
            })
            board.push(move)
            walk(child, child_depth)
            board.pop()

    walk(tree.root, 0)
    return rows


def _format_line_sans(sans) -> str:
    """SAN-Liste -> lesbare Zugfolge »1.e4 c6 2.d4 d5 3.Nc3« (englische Figuren;
    die Oberfläche germanisiert bei Bedarf)."""
    parts = []
    for i, san in enumerate(sans):
        if i % 2 == 0:
            parts.append(f"{i // 2 + 1}.{san}")
        else:
            parts.append(san)
    return " ".join(parts)


def variation_outline(tree, side) -> list[dict]:
    """Gliedert den (verschmolzenen) Übersichtsbaum nach BENANNTEN Varianten —
    die übersichtliche, namens-orientierte Alternative zur flachen ``overview_rows``.

    Eine Gruppe je Variantenname (aus den Blatt-Kommentaren des verschmolzenen
    Baums), in Baum-Reihenfolge (Hauptlinie zuerst). Jede Gruppe trägt den
    verschachtelten Zug-Teilbaum ihrer Linien; der gemeinsame Stamm erscheint
    unter jeder Gruppe (so liest sich jede Variante ab Zug 1). Felder je Gruppe:
    ``name`` (kann leer sein), ``lines`` (Anzahl Linien/Blätter), ``gaps``
    (Lücken: Blätter, an denen die Seite am Zug ist), ``preview`` (gemeinsame
    SAN-Vorhut), ``nodes`` (verschachtelte Zugknoten). Jeder Zugknoten:
    ``label`` (»3.Nc3«/»3…Bf5«), ``move_uci``, ``fen_before`` (Drill-Ziel bei
    eigenen Zügen), ``is_user_move``, ``is_gap``, ``node_id``, ``name``
    (Blattname am Linienende), ``children``. Reine Funktion."""
    # 1. Blätter mit Name, Knoten-Pfad (IDs), SAN-Folge und Lücken-Flag sammeln.
    board = _start_board(tree)
    leaves: list[dict] = []

    def collect(node, ids, sans):
        kids = tree.children_of(node.id)
        if not kids:
            if node.id != tree.root_id:
                leaves.append({
                    "name": node.comment or "",
                    "ids": list(ids),
                    "sans": list(sans),
                    "gap": board.turn == side,
                })
            return
        for child in kids:
            mv = _legal_move(board, child.move_uci)
            if mv is None:
                continue
            san = board.san(mv)
            board.push(mv)
            collect(child, ids + [child.id], sans + [san])
            board.pop()

    collect(tree.root, [], [])

    # 2. Nach Name gruppieren (Erst-Auftreten = Reihenfolge).
    order: list[str] = []
    groups: dict[str, dict] = {}
    for lf in leaves:
        g = groups.get(lf["name"])
        if g is None:
            g = {"ids": set(), "lines": 0, "gaps": 0, "sanlists": []}
            groups[lf["name"]] = g
            order.append(lf["name"])
        g["ids"].update(lf["ids"])
        g["lines"] += 1
        g["gaps"] += 1 if lf["gap"] else 0
        g["sanlists"].append(lf["sans"])

    # 3. Verschachtelten Zug-Teilbaum je Gruppe (nur erlaubte Knoten) bauen.
    def build(parent_node, brd, allowed):
        out = []
        for child in tree.children_of(parent_node.id):
            if child.id not in allowed:
                continue
            mv = _legal_move(brd, child.move_uci)
            if mv is None:
                continue
            fen_before = brd.fen()
            is_user = brd.turn == side
            white = brd.turn == chess.WHITE
            san = brd.san(mv)
            label = f"{brd.fullmove_number}.{san}" if white else f"{brd.fullmove_number}…{san}"
            brd.push(mv)
            kids = build(child, brd, allowed)
            is_leaf = not kids
            is_gap = is_leaf and brd.turn == side
            name = child.comment if is_leaf else ""
            brd.pop()
            out.append({
                "label": label, "move_uci": child.move_uci, "fen_before": fen_before,
                "is_user_move": is_user, "is_gap": is_gap, "node_id": child.id,
                "name": name, "children": kids,
            })
        return out

    def common_prefix(lists):
        if not lists:
            return []
        pref = lists[0]
        for lst in lists[1:]:
            i = 0
            while i < len(pref) and i < len(lst) and pref[i] == lst[i]:
                i += 1
            pref = pref[:i]
            if not pref:
                break
        return pref

    out_groups: list[dict] = []
    for name in order:
        g = groups[name]
        nodes = build(tree.root, _start_board(tree), g["ids"])
        pref = common_prefix(g["sanlists"])
        preview = _format_line_sans(pref)
        if any(len(s) > len(pref) for s in g["sanlists"]):
            preview = (preview + " …").strip()
        out_groups.append({
            "name": name, "lines": g["lines"], "gaps": g["gaps"],
            "preview": preview, "nodes": nodes,
        })
    return out_groups


def merge_stats(trees, side) -> dict:
    """Kennzahlen für den Lade-Report: wie viele Linien dieser Seite vorliegen
    und wie viele Verzweigungen entstehen, wenn man sie zu EINEM Baum
    verschmilzt. ``lines`` = Bäume der Seite (Standard-Grundstellung),
    ``branches`` = Knoten mit mehr als einem Kind im verschmolzenen Baum."""
    want = _SIDE_NAME.get(side)
    n_lines = sum(1 for tr in trees if tr.side == want and not tr.start_fen)
    branches = sum(1 for r in overview_rows(merge_side_trees(trees, side), side)
                   if r["children"] > 1)
    return {"lines": n_lines, "branches": branches}


def repertoire_gaps(trees, side) -> list[dict]:
    """Lücken der trainierten Seite: Linien-Enden (Blätter), an denen DIE SEITE
    am Zug ist (der Gegner zog zuletzt) — dort fehlt eine eigene Antwort, man
    fällt »aus dem Buch«. Reine Funktion; liefert pro Lücke
    (tree, node_id, epd, line=SAN-Folge)."""
    want = _SIDE_NAME.get(side)
    out: list[dict] = []
    for tree in trees:
        if tree.side != want:
            continue
        board = _start_board(tree)

        def walk(node, sans):
            kids = tree.children_of(node.id)
            if not kids:
                if node.id != tree.root_id and board.turn == side:
                    out.append({"tree": tree, "node_id": node.id,
                                "epd": board.epd(), "line": " ".join(sans)})
                return
            for child in kids:
                mv = _legal_move(board, child.move_uci)
                if mv is None:
                    continue
                san = board.san(mv)
                board.push(mv)
                walk(child, sans + [san])
                board.pop()

        walk(tree.root, [])
    return out


def tree_mainline_uci(tree) -> list:
    """Die Hauptlinie eines Baums als UCI-Zugliste (jeweils erstes Kind).
    Grundlage der Eröffnungs-Erkennung."""
    out: list = []
    node = tree.root
    while True:
        kids = tree.children_of(node.id)
        if not kids:
            break
        node = kids[0]
        out.append(node.move_uci)
    return out


def locate_position(index: dict, epd: str):
    """(tree, node_id) für eine EPD aus einem ``build_user_position_index``,
    sonst ``None``. Zum gezielten Drillen einer einzelnen Stellung (Fehler-
    Stellung, Partie-Abweichung)."""
    return index.get(epd)


def tree_for_moves(trees, moves_uci, side):
    """Der Baum der passenden Seite, der diese Zugfolge (Linie) als Pfad von der
    Wurzel enthält. Damit lässt sich ein Bibliotheks-Klick auf eine Linie auf
    ihren Baum-Drill umlenken. Eindeutig (nicht über die geteilte Startstellung).
    ``None``, wenn keine/keine eindeutige Folge passt."""
    if not moves_uci:
        return None
    want = _SIDE_NAME.get(side)
    for tree in trees:
        if tree.side != want:
            continue
        node = tree.root
        ok = True
        for uci in moves_uci:
            child = tree.child_with_move(node.id, uci)
            if child is None:
                ok = False
                break
            node = child
        if ok:
            return tree
    return None


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


def tree_check_paths(trees, side) -> list[tuple]:
    """Wurzel-zu-Blatt-Pfade der Bäume EINER Seite als ``(name, moves_uci, tree)``.

    Jedes Blatt ergibt eine vollständige Variante (Zugfolge beider Farben von der
    Grundstellung bis zum Blatt) — so prüft die Repertoire-Prüfung auch
    Nebenvarianten, nicht nur die lineare Hauptlinie. Hat ein Baum mehrere
    Varianten, wird der Anzeigename nummeriert. Identische Zugfolgen werden
    dedupliziert. Reihenfolge: pro Baum in Knoten-Reihenfolge."""
    want = _SIDE_NAME.get(side)
    out: list[tuple] = []
    seen: set = set()
    for tree in trees:
        if tree.side != want:
            continue
        leaves = [
            n for n in tree.iter_nodes()
            if n.id != tree.root_id and not tree.children_of(n.id)
        ]
        variants = [tree.path_to(leaf.id) for leaf in leaves]
        variants = [v for v in variants if v]
        for k, moves in enumerate(variants, 1):
            key = (tree.id, tuple(moves))
            if key in seen:
                continue
            seen.add(key)
            name = tree.name if len(variants) == 1 else f"{tree.name} — {k}"
            out.append((name, moves, tree))
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


def weak_position_fens(white_trees, black_trees, stats_store, limit=None) -> list[str]:
    """FENs der offenen Fehlerstellungen über BEIDE Seiten — die wackligsten
    zuerst (häufigste Fehler oben), per FEN dedupliziert. Für eine gezielte
    »Schwächen üben«-Sitzung über das ganze Repertoire.

    ``limit`` deckelt die Länge (z. B. nur die Top-N), ``None`` = alle. Quelle ist
    ``open_error_positions`` (varianten-bewusst, transpositions-dedupliziert)."""
    problems = (
        open_error_positions(white_trees, chess.WHITE, stats_store)
        + open_error_positions(black_trees, chess.BLACK, stats_store)
    )
    problems.sort(key=lambda p: -p["count"])
    fens: list[str] = []
    seen: set = set()
    for p in problems:
        fen = p["fen"]
        if fen in seen:
            continue
        seen.add(fen)
        fens.append(fen)
    return fens[:limit] if limit is not None else fens


def blitz_pool(white_trees, black_trees) -> list[tuple]:
    """Alle eigenen Stellungen BEIDER Seiten als ``(tree, node_id, color)`` —
    der Vorrat für den Blitz-Sprint. Feste Reihenfolge (Weiß zuerst, dann in
    Index-Reihenfolge); das Mischen macht die Oberfläche. Pro EPD genau eine
    Stelle (Transpositionen zählen einmal). Unabhängig vom Lernplan."""
    out: list[tuple] = []
    for trees, color in ((white_trees, chess.WHITE), (black_trees, chess.BLACK)):
        for tree, node_id in build_user_position_index(trees, color).values():
            out.append((tree, node_id, color))
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
