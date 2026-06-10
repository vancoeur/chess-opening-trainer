"""Entry point of the modern Qt interface of Opening Trainer.

Start:  python3 qt_main.py

Opening Trainer — personal chess opening trainer.
Copyright (C) 2026 Achim (Opening Trainer authors).

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License, version 3 or (at your option) any
later version. It comes with ABSOLUTELY NO WARRANTY. See the LICENSE file and
NOTICE.md for details.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from qt_app.main_window import MainWindow
from qt_app.paths import app_icon_path

APP_VERSION = "1.0"


def _ensure_qt_plugin_path() -> None:
    """In der verpackten App den Qt-Plugin-Pfad explizit setzen, damit Qt seine
    Plugins findet — insbesondere die TLS-Backends, ohne die HTTPS (und damit
    der Lichess-Explorer) nicht funktioniert."""
    meipass = getattr(sys, "_MEIPASS", None)
    if not getattr(sys, "frozen", False) or not meipass:
        return
    plugins = Path(meipass) / "PySide6" / "Qt" / "plugins"
    if plugins.exists():
        QtCore.QCoreApplication.addLibraryPath(str(plugins))


def main() -> int:
    _ensure_qt_plugin_path()
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Opening Trainer")
    app.setApplicationDisplayName("Opening Trainer")
    app.setApplicationVersion(APP_VERSION)
    icon = app_icon_path()
    if icon.exists():
        app.setWindowIcon(QtGui.QIcon(str(icon)))
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
