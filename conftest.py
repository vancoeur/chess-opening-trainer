"""Pytest-Konfiguration: Qt offscreen + sauberes Beenden.

Viele Tests erzeugen ``MainWindow``-Instanzen, die einen Hintergrund-Thread (die
Bewertungs-Leiste) starten. Endet der Interpreter, ohne diese Threads zu stoppen,
bricht Qt mit ``SIGABRT`` ab (ein noch laufender ``QThread`` im Destruktor) — die
Suite würde dann trotz bestandener Tests mit Exit-Code 134 enden (und CI rot
färben). Darum stoppen wir am Sitzungsende alle laufenden Worker-Threads.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    try:
        from PySide6 import QtWidgets
        app = QtWidgets.QApplication.instance()
        if app is None:
            return
        for w in list(app.topLevelWidgets()):
            stop = getattr(w, "_stop_all_threads", None)
            if callable(stop):
                try:
                    stop()
                except Exception:  # noqa: BLE001
                    pass
        app.processEvents()
    except Exception:  # noqa: BLE001
        pass
