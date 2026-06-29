"""A daily 'due positions' session across the whole tree repertoire.

Maps each of the trained side's positions (epd) to one place in the trees where it
occurs, then asks the per-position schedule which are due today. Transpositions
share one epd → one card, so the same position isn't reviewed twice in a day.
Pure (no UI); the UI starts a ``PositionTrainer`` at each returned (tree, node).
"""
from __future__ import annotations

import re
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


def _outline_nodes(tree, side):
    """Verschachtelte Zugknoten EINES Baums (für die Varianten-Übersicht) plus
    Zähler (Blätter, Lücken). Jeder Knoten: ``label`` (»3.Nc3«/»3…Bf5«),
    ``move_uci``, ``fen_before``, ``is_user_move``, ``is_gap``, ``node_id``,
    ``children``."""
    board = _start_board(tree)

    def build(node):
        out, leaves, gaps = [], 0, 0
        for child in tree.children_of(node.id):
            mv = _legal_move(board, child.move_uci)
            if mv is None:
                continue
            fen_before = board.fen()
            is_user = board.turn == side
            white = board.turn == chess.WHITE
            san = board.san(mv)
            label = f"{board.fullmove_number}.{san}" if white else f"{board.fullmove_number}…{san}"
            board.push(mv)
            kids, kl, kg = build(child)
            is_leaf = not kids
            is_gap = is_leaf and board.turn == side
            leaves += kl + (1 if is_leaf else 0)
            gaps += kg + (1 if is_gap else 0)
            board.pop()
            out.append({
                "label": label, "move_uci": child.move_uci, "fen_before": fen_before,
                "is_user_move": is_user, "is_gap": is_gap, "node_id": child.id,
                "children": kids,
            })
        return out, leaves, gaps

    return build(tree.root)


def _leaf_sanlists(tree):
    """Alle Wurzel-zu-Blatt-SAN-Folgen eines Baums (für die Vorschau-Vorhut)."""
    board = _start_board(tree)
    out: list[list[str]] = []

    def walk(node, sans):
        kids = tree.children_of(node.id)
        if not kids:
            if node.id != tree.root_id:
                out.append(list(sans))
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


def _common_prefix(lists):
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


def variation_outline(trees, side, misc_label: str = "Study material",
                      strip_family: bool = False) -> list[dict]:
    """Gliedert die Bäume EINER Seite nach ihrem **ECO-Eröffnungsnamen** —
    die übersichtliche, namens-orientierte Alternative zur flachen ``overview_rows``.

    Jedes Kapitel wird über die ersten ~20 Halbzüge seiner Hauptlinie in der
    ECO-Datenbank identifiziert (``identify_opening_name``) → ein einheitlicher,
    kanonischer Name (z. B. »Caro-Kann Defense: Advance Variation«). Kapitel mit
    demselben ECO-Namen landen in EINER Gruppe (gemeinsamer Stamm einmal,
    Verzweigung am ersten Unterschied). Rückfall auf den Kapitelnamen nur, wenn
    ECO gar nichts erkennt. **Bewusst nicht nach Blatt-Kommentaren** (Prosa/
    Pfeil-Codes in echten Studien). Felder je Gruppe: ``name``, ``lines``,
    ``gaps``, ``preview``, ``nodes``. Reine Funktion."""
    from opening_trainer.opening_id import identify_opening_name
    from opening_trainer.comments import clean_chapter_name, is_instructional
    want = _SIDE_NAME.get(side)
    chapters = [t for t in trees if t.side == want and not t.start_fen]
    order: list[str] = []
    bucket: dict[str, list] = {}
    for tr in chapters:
        if is_instructional(tr.name):
            # Lehrmaterial (Einführung, Musterpartie, Plan …): in EINE Sammelgruppe,
            # nicht unter die Eröffnungsvarianten mischen.
            nm = misc_label
        else:
            eco = identify_opening_name(tree_mainline_uci(tr))
            if eco and ":" in eco:
                # Echter ECO-Varianten-Name: bis zum ersten Komma bündeln, damit
                # Untervarianten (»…: Advance Variation, Short«) zur Hauptvariante
                # (»…: Advance Variation«) zusammenlaufen statt zu zersplittern.
                nm = eco.split(",", 1)[0].strip()
                if strip_family:
                    # Bei EINER gewählten Familie das »Caro-Kann Defense:«-Präfix
                    # weglassen — so verschmilzt »…: Two Knights Attack« mit dem
                    # Kapitel-Rückfall »Two Knights Attack …« zu EINER Gruppe.
                    nm = nm.split(":", 1)[1].strip()
            else:
                # ECO kennt nur die nackte Familie (oder nichts): den (gesäuberten)
                # Kapitelnamen nehmen — sonst klumpen alle unbenannten Linien.
                nm = clean_chapter_name(tr.name) or eco or (tr.name or "").strip()
                if strip_family and nm:
                    # auf die Haupt-Variante kürzen (»Two Knights Attack - Karpov«
                    # → »Two Knights Attack«), damit Unterkapitel zusammenlaufen.
                    nm = re.split(r"\s[-–]\s", nm, maxsplit=1)[0].strip()
        if nm not in bucket:
            bucket[nm] = []
            order.append(nm)
        bucket[nm].append(tr)
    if misc_label in order:                       # Lehrmaterial immer ans Ende
        order.remove(misc_label)
        order.append(misc_label)

    out_groups: list[dict] = []
    for nm in order:
        sub = merge_side_trees(bucket[nm], side)      # gleichnamige Kapitel vereinen
        nodes, leaves, gaps = _outline_nodes(sub, side)
        if not nodes:
            continue
        sanlists = _leaf_sanlists(sub)
        pref = _common_prefix(sanlists)
        preview = _format_line_sans(pref)
        if any(len(s) > len(pref) for s in sanlists):
            preview = (preview + " …").strip()
        out_groups.append({
            "name": nm, "lines": leaves, "gaps": gaps,
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
        try:
            board = _start_board(tree)          # ungültige start_fen darf nicht crashen
        except ValueError:
            continue

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
