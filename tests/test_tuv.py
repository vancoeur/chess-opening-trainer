"""Repertoire-Prüfung (A4): Ergebnisse gehören an den Repertoire-Stand, zu dem sie
berechnet wurden — ändert sich das Repertoire, werden alte Ergebnisse verworfen."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets  # noqa: E402

import qt_app.main_window as mw  # noqa: E402
from opening_trainer.repertoire_tree import RepertoireTree, WHITE  # noqa: E402
from opening_trainer.engine_review import MoveIssue  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _win(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    return mw.MainWindow()


def _tree(name, ucis):
    t = RepertoireTree.new(name, WHITE)
    p = t.root_id
    for u in ucis:
        p = t.add_child(p, u).id
    return t


def _issue():
    return MoveIssue(ply=2, move_number=2, san="Nf3", best_san="d4",
                     loss_cp=90, eval_after_cp=-30, severity="patzer")


def test_tuv_discards_stale_results_but_shows_current(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    tree = _tree("Italienisch", ["e2e4", "e7e5", "g1f3"])
    win.tree_store.add(tree)
    line = mw._TuvPath("Italienisch", ["e2e4", "e7e5", "g1f3"], tree)

    # (a) Ergebnis eines Laufs, dessen Signatur nicht mehr zum Stand passt -> verworfen
    win._tuv_run_sig = (("stale", "x", 0),)
    win._on_tuv_finished([{"line": line, "issues": [_issue()]}])
    assert win.tuv_list.count() == 0
    assert "ndert" in win.tuv_status.text() or "chang" in win.tuv_status.text().lower()

    # (b) Ergebnis eines Laufs am AKTUELLEN Stand -> angezeigt
    win._tuv_run_sig = win._repertoire_signature()
    win._on_tuv_finished([{"line": line, "issues": [_issue()]}])
    assert win.tuv_list.count() == 1


def test_repertoire_signature_changes_on_edit(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    tree = _tree("Italienisch", ["e2e4", "e7e5"])
    win.tree_store.add(tree)
    sig1 = win._repertoire_signature()
    leaf = tree.children_of(tree.children_of(tree.root_id)[0].id)[0]   # Knoten nach 1.e4 e5
    tree.add_child(leaf.id, "g1f3")                                    # einen Zug ergänzen
    assert win._repertoire_signature() != sig1
