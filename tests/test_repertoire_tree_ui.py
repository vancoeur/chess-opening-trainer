"""Repertoire-Baum-Seite (Stack 13): namens-orientierte, aufklappbare Übersicht
(QTreeWidget). Oben benannte Varianten, darunter der verschachtelte Zug-Baum;
Klick zeigt die Stellung, eigene Züge drillbar, Doppelklick übt die Variante.
Offscreen gegen die echte ``MainWindow``.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets, QtCore  # noqa: E402

from opening_trainer.repertoire_tree import RepertoireTree, BLACK  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _win(tmp_path, monkeypatch):
    import qt_app.main_window as mw
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    return mw.MainWindow()


def _black(name, ucis):
    t = RepertoireTree.new(name, BLACK)
    p = t.root_id
    for u in ucis:
        p = t.add_child(p, u).id
    return t


def _load_two_caro(win):
    win.tree_store.add(_black("Advance", ["e2e4", "c7c6", "d2d4", "d7d5", "e4e5", "c8f5"]))
    win.tree_store.add(_black("Klassisch", ["e2e4", "c7c6", "d2d4", "d7d5", "b1c3", "d5e4"]))


def _fam_set(win):
    c = win.reptree_family_combo
    return {c.itemData(i) for i in range(c.count())}


def test_family_combo_updates_after_tree_removed(tmp_path, monkeypatch):
    """R1-Regression (der gemeldete Fehler): Baum löschen -> die Familie verschwindet
    SOFORT aus der Repertoire-Baum-Auswahl (nicht erst nach Neustart)."""
    win = _win(tmp_path, monkeypatch)
    caro = _black("Caro", ["e2e4", "c7c6", "d2d4", "d7d5", "e4e5", "c8f5"])
    skandi = _black("Skandi", ["e2e4", "d7d5", "e4d5", "d8d5", "b1c3", "d5a5"])
    win.tree_store.add(caro)
    win.tree_store.add(skandi)
    win._open_repertoire_tree()
    win.reptree_side_combo.setCurrentIndex(1)              # Schwarz
    win._reptree_refresh_families()
    fam = win._tree_family(skandi)
    assert fam in _fam_set(win)
    win.tree_store.remove(skandi.id)                       # löschen wie im Verwalten-Dialog
    win._refresh_all_views()                               # zentrale Auffrischung
    assert fam not in _fam_set(win)                        # sofort weg


def test_reptree_self_heals_on_navigation(tmp_path, monkeypatch):
    """Auch wenn eine Änderung anderswo passiert (Baum weg, während man NICHT auf der
    Seite ist): beim Zurückkehren baut sich die Repertoire-Baum-Seite frisch auf."""
    win = _win(tmp_path, monkeypatch)
    caro = _black("Caro", ["e2e4", "c7c6", "d2d4", "d7d5", "e4e5", "c8f5"])
    skandi = _black("Skandi", ["e2e4", "d7d5", "e4d5", "d8d5", "b1c3", "d5a5"])
    win.tree_store.add(caro)
    win.tree_store.add(skandi)
    win._open_repertoire_tree()
    win.reptree_side_combo.setCurrentIndex(1)
    win._reptree_refresh_families()
    fam = win._tree_family(skandi)
    win.stack.setCurrentIndex(12)                          # weg (Start-Hub)
    win.tree_store.remove(skandi.id)                       # Änderung ohne explizite Auffrischung
    win.stack.setCurrentIndex(13)                          # zurück -> _on_page_changed heilt
    assert fam not in _fam_set(win)


def test_reptree_family_filter_preserved_on_refresh(tmp_path, monkeypatch):
    """Papierschnitt: das Auffrischen darf die gewählte Familie nicht auf »Alles«
    zurückwerfen, solange es sie noch gibt."""
    win = _win(tmp_path, monkeypatch)
    caro = _black("Caro", ["e2e4", "c7c6", "d2d4", "d7d5", "e4e5", "c8f5"])
    skandi = _black("Skandi", ["e2e4", "d7d5", "e4d5", "d8d5", "b1c3", "d5a5"])
    win.tree_store.add(caro)
    win.tree_store.add(skandi)
    win._open_repertoire_tree()
    win.reptree_side_combo.setCurrentIndex(1)
    win._reptree_refresh_families()
    fam = win._tree_family(caro)
    win.reptree_family_combo.setCurrentIndex(win.reptree_family_combo.findData(fam))
    win._reptree_refresh_families()                        # erneut auffrischen
    assert win.reptree_family_combo.currentData() == fam   # Auswahl bleibt


def _all_items(tree):
    out = []

    def walk(it):
        out.append(it)
        for i in range(it.childCount()):
            walk(it.child(i))

    for i in range(tree.topLevelItemCount()):
        walk(tree.topLevelItem(i))
    return out


def _move_items(tree):
    """Nur Zug-Knoten (nicht die Gruppen-Köpfe)."""
    out = []
    for it in _all_items(tree):
        d = it.data(0, QtCore.Qt.UserRole)
        if isinstance(d, dict) and "is_user_move" in d:
            out.append(it)
    return out


def test_page_groups_named_variations(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _load_two_caro(win)
    win._open_repertoire_tree()
    assert win.stack.currentIndex() == 13
    assert win.reptree_side_combo.currentData() == "black"      # Seite mit Repertoire
    # Zwei Varianten = zwei oberste Einträge, benannt über die ECO-Datenbank.
    assert win.reptree_tree.topLevelItemCount() == 2
    tops = [win.reptree_tree.topLevelItem(i).text(0) for i in range(2)]
    assert any("Advance Variation" in x for x in tops)          # ECO-Name, nicht »Advance«-Kapitel
    assert any("Caro-Kann Defense" in x for x in tops)


def test_branch_marker_within_a_named_variation(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    # EINE benannte Variante, die sich intern verzweigt (…Bf5 / …Nf6).
    base = ["e2e4", "c7c6", "d2d4", "d7d5", "b1c3", "d5e4", "c3e4"]
    win.tree_store.add(_black("Klassisch", base + ["c8f5"]))
    win.tree_store.add(_black("Klassisch", base + ["g8f6"]))
    win._open_repertoire_tree()
    assert win.reptree_tree.topLevelItemCount() == 1            # ein Name
    texts = [it.text(0) for it in _all_items(win.reptree_tree)]
    assert any("⎇" in tx for tx in texts)                      # interne Verzweigung markiert


def test_click_user_move_makes_button_drill_position(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _load_two_caro(win)
    win._open_repertoire_tree()
    item = next(it for it in _move_items(win.reptree_tree)
                if it.data(0, QtCore.Qt.UserRole)["is_user_move"])
    win._reptree_clicked(item)
    assert win._reptree_target[0] == "position"                 # Haupt-Button = »Diese Stellung«
    assert "Stellung" in win.reptree_train_btn.text() or "position" in win.reptree_train_btn.text()
    win._reptree_primary_action()
    assert win.stack.currentIndex() == 10                       # startet die Stellungs-Sitzung


def test_click_opponent_move_targets_the_variation(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _load_two_caro(win)
    win._open_repertoire_tree()
    item = next(it for it in _move_items(win.reptree_tree)
                if not it.data(0, QtCore.Qt.UserRole)["is_user_move"])
    win._reptree_clicked(item)
    # kein »kaputter« grauer Knopf mehr: der Gegnerzug zielt auf seine Variante
    assert win._reptree_target[0] in ("variation", "repertoire")
    assert "üben" in win.reptree_train_btn.text() or "Train" in win.reptree_train_btn.text()


def test_click_variation_name_trains_that_variation(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _load_two_caro(win)
    win._open_repertoire_tree()
    top = win.reptree_tree.topLevelItem(0)
    win._reptree_clicked(top)
    assert win._reptree_target[0] == "variation"
    assert "Variante" in win.reptree_train_btn.text() or "variation" in win.reptree_train_btn.text()
    win._reptree_primary_action()
    assert win.stack.currentIndex() == 10                       # Variante wird geübt


def test_double_click_name_trains_variation(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _load_two_caro(win)
    win._open_repertoire_tree()
    top = win.reptree_tree.topLevelItem(0)                      # ein Varianten-Kopf
    win._reptree_item_double_clicked(top)
    assert win.stack.currentIndex() == 10                       # Variante wird geübt


def test_tree_report_lines_after_load(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _load_two_caro(win)
    lines = win._tree_report_lines()
    assert len(lines) == 1                                  # nur Schwarz hat Linien
    text = lines[0]
    assert ("Schwarz" in text or "Black" in text)
    assert ("Verzweigung" in text or "branch" in text)      # die zwei Linien verzweigen


def _families(win):
    return [win.reptree_family_combo.itemText(i) for i in range(win.reptree_family_combo.count())]


def test_family_selector_lists_repertoires(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    win.tree_store.add(_black("B18 · Caro-Kann: Klassisch", ["e2e4", "c7c6", "d2d4", "d7d5"]))
    win.tree_store.add(_black("C65 · Ruy López: Berliner", ["e2e4", "e7e5", "g1f3", "b8c6", "f1b5", "a7a6"]))
    win._open_repertoire_tree()
    fams = _families(win)
    assert fams[0] in ("Alles", "All")            # erste Option = alles
    assert "Caro-Kann" in fams and "Ruy López" in fams


def test_family_selection_filters_tree_and_trains(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    win.tree_store.add(_black("B18 · Caro-Kann: Klassisch", ["e2e4", "c7c6", "d2d4", "d7d5"]))
    win.tree_store.add(_black("C65 · Ruy López: Berliner", ["e2e4", "e7e5", "g1f3", "b8c6", "f1b5", "a7a6"]))
    win._open_repertoire_tree()
    # Caro-Kann wählen -> nur diese Züge im Baum (keine Ruy-Züge)
    idx = next(i for i in range(win.reptree_family_combo.count())
               if win.reptree_family_combo.itemData(i) == "Caro-Kann")
    win.reptree_family_combo.setCurrentIndex(idx)
    texts = " ".join(it.text(0) for it in _move_items(win.reptree_tree))
    assert "c6" in texts and "e5" not in texts
    # dieses Repertoire üben -> Stellungs-Sitzung
    win._reptree_train()
    assert win.stack.currentIndex() == 10


def test_generic_chapter_name_gets_detected_opening(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    # unbenanntes Studien-Kapitel mit Caro-Zügen
    win.tree_store.add(_black("Chapter #24", ["e2e4", "c7c6", "d2d4", "d7d5"]))
    win._open_repertoire_tree()
    fams = _families(win)
    assert "Caro-Kann" in fams              # aus den Zügen erkannt
    assert "Chapter #24" not in fams        # generischer Name ersetzt


def test_train_variation_keeps_opening_at_shared_start(tmp_path, monkeypatch):
    """Regression: mehrere Weiss-Repertoires teilen die Grundstellung (e4 vs c4).
    »Diese Variante üben« fuer Italienisch darf die Grundstellung NICHT dem
    Englisch-Baum (c4) zuordnen, sondern muss beim Italiener (e4) bleiben."""
    import chess
    from opening_trainer.tree_session import variation_outline
    from opening_trainer.position_training import PositionTrainer
    win = _win(tmp_path, monkeypatch)

    def white(name, ucis):
        t = RepertoireTree.new(name, "white")
        p = t.root_id
        for u in ucis:
            p = t.add_child(p, u).id
        return t

    # Englisch ZUERST laden (erster Treffer im Index) -> genau der Fehlerfall.
    win.tree_store.add(white("Englisch", ["c2c4", "e7e5", "b1c3", "g8f6"]))
    win.tree_store.add(white("Italienisch", ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "f8c5"]))
    win._open_repertoire_tree()
    win.reptree_side_combo.setCurrentIndex(0)                 # Weiss

    groups = variation_outline(win.tree_store.by_side("white"), chess.WHITE)
    ital = next(g for g in groups if "Italian" in g["name"])
    items = win._reptree_group_user_items(ital)
    assert items, "die Variante sollte trainierbare Stellungen haben"
    tree, node_id, color = items[0]                          # erste = Grundstellung
    sol = PositionTrainer(tree, color, start_node_id=node_id, auto_opponent=True).expected_solution()
    assert sol is not None and sol.san == "e4"               # Italienisch e4, NICHT Englisch c4


def test_drill_position_keeps_opening_at_shared_start(tmp_path, monkeypatch):
    """Selbe Absicherung fuer den »Diese Stellung üben«-Knopf: die Grundstellung
    des Italieners darf nicht als Englisch (c4) aufgeloest werden."""
    import chess
    from opening_trainer.tree_session import variation_outline
    from opening_trainer.position_training import PositionTrainer
    win = _win(tmp_path, monkeypatch)

    def white(name, ucis):
        t = RepertoireTree.new(name, "white")
        p = t.root_id
        for u in ucis:
            p = t.add_child(p, u).id
        return t

    win.tree_store.add(white("Englisch", ["c2c4", "e7e5", "b1c3", "g8f6"]))
    win.tree_store.add(white("Italienisch", ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "f8c5"]))
    win._open_repertoire_tree()
    win.reptree_side_combo.setCurrentIndex(0)                 # Weiss

    groups = variation_outline(win.tree_store.by_side("white"), chess.WHITE)
    ital = next(g for g in groups if "Italian" in g["name"])
    start_fen = chess.Board().fen()                          # geteilte Grundstellung
    item = win._reptree_locate_fen(ital, start_fen)
    assert item is not None
    tree, node_id, color = item
    sol = PositionTrainer(tree, color, start_node_id=node_id, auto_opponent=True).expected_solution()
    assert sol is not None and sol.san == "e4"


def test_gap_shown_and_jumps_to_editor(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    # Linie endet nach Weiß' 2.d4 -> Schwarz am Zug, keine Antwort = Lücke
    win.tree_store.add(_black("Caro", ["e2e4", "c7c6", "d2d4"]))
    win._open_repertoire_tree()
    assert "⚠" in win.reptree_hint.text()
    gap_items = [it for it in _move_items(win.reptree_tree)
                 if it.data(0, QtCore.Qt.UserRole).get("is_gap")]
    assert gap_items, "es sollte eine Lücken-Zeile geben"
    win._reptree_clicked(gap_items[0])
    assert win.reptree_gap_btn.isEnabled()
    win._reptree_fill_gap()
    assert win.stack.currentIndex() == 9        # Editor an der Lücke


def test_white_defense_gets_gegen_label(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    lbl = win._reptree_family_label("Sizilianisch", "white")
    assert lbl != "Sizilianisch" and "Sizilianisch" in lbl       # »gegen Sizilianisch«
    assert win._reptree_family_label("Englische Eröffnung", "white") == "Englische Eröffnung"
    assert win._reptree_family_label("Sizilianisch", "black") == "Sizilianisch"  # als Schwarz: kein »gegen«


def test_train_loaded_file_starts_session(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    f = tmp_path / "Weiss Sizilianisch.pgn"
    f.write_text('[Event "x"]\n[ChapterName "Sizilianisch Alapin"]\n\n1. e4 c5 2. c3 d5 3. exd5 *\n', encoding="utf-8")
    win._add_pgn_source(str(f))
    win._auto_fill_sides_by_filename()
    assert win._trees_for_source(str(f)), "Bäume der Datei sollten auffindbar sein"
    win._train_source(str(f))
    assert win.stack.currentIndex() == 10        # Stellungs-Sitzung dieser Datei


def test_window_title_reflects_page(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    win.stack.setCurrentIndex(13)
    assert "Repertoire-Baum" in win.windowTitle() or "Repertoire tree" in win.windowTitle()
    win.stack.setCurrentIndex(11)
    assert "Heute fällig" in win.windowTitle() or "Due today" in win.windowTitle()


def test_unassigned_trees_are_flagged_not_silently_hidden(tmp_path, monkeypatch):
    from opening_trainer.repertoire_tree import RepertoireTree
    win = _win(tmp_path, monkeypatch)
    _load_two_caro(win)                                # Schwarz-Repertoire (sichtbar)
    noside = RepertoireTree.new("Ohne Seite", "none")  # nicht zugeordnet
    p = noside.root_id
    for u in ["e2e4", "e7e5"]:
        p = noside.add_child(p, u).id
    win.tree_store.add(noside)
    win._open_repertoire_tree()
    hint = win.reptree_hint.text().lower()
    assert "ohne" in hint or "no side" in hint         # Warnung sichtbar
    assert "⚠" in win.reptree_hint.text()


def test_empty_side_shows_hint(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    _load_two_caro(win)
    win._open_repertoire_tree()
    win.reptree_side_combo.setCurrentIndex(0)                   # Weiß: kein Repertoire
    assert win.reptree_tree.topLevelItemCount() == 0
    assert "kein Repertoire" in win.reptree_hint.text() or "No repertoire" in win.reptree_hint.text()
