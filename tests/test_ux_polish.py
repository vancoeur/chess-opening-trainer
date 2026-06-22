"""UX-Bündel 6: Politur — Fortschritts-Leerbalken, Kürzel-Tooltips, Skip-Label."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets  # noqa: E402

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _win(tmp_path, monkeypatch, lang="en"):
    import qt_app.main_window as mw
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(mw, "data_dir", lambda: data)
    win = mw.MainWindow()
    from qt_app import i18n
    i18n.set_language(lang)
    return win


def test_progress_hides_empty_bar(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch, lang="en")
    win.lines = []
    win._refresh_progress()
    assert win.progress_bar.isHidden()                       # kein leerer grauer Balken
    assert "assign" in win.progress_counts.text().lower()    # stattdessen ein Hinweis


def test_shortcut_tooltips_and_clear_skip_label(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    assert win.solution_btn.toolTip() != ""                  # „L"
    assert win.next_btn.toolTip() != ""                      # „Enter"
    assert win.next_btn.text() in ("Diese Eröffnung überspringen", "Skip this opening")


def test_eval_legend_tooltips_present(tmp_path, monkeypatch):
    win = _win(tmp_path, monkeypatch)
    assert win.tuv_status.toolTip() != ""                    # Centipawn-Erklärung
    assert win.viewer_status.toolTip() != ""
