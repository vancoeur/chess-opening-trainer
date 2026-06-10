from __future__ import annotations

import os
import sys
from pathlib import Path


def _frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def assets_root() -> Path:
    """Wurzel des assets-Ordners (Figuren, Icon) — in Entwicklung und verpackt."""
    if _frozen():
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        return base / "assets"
    return Path(__file__).resolve().parent.parent / "assets"


def asset_dir() -> Path:
    """Ordner mit den Figurengrafiken."""
    return assets_root() / "pieces"


def app_icon_path() -> Path:
    return assets_root() / "app_icon.png"


def bundled_stockfish() -> Path | None:
    """Pfad zur mitgelieferten Stockfish-Programmdatei (assets/engine/stockfish).

    Vorhanden in Entwicklung (ins Projekt kopiert) und in der verpackten App
    (über ``--add-data assets``). Gibt ``None`` zurück, wenn sie fehlt — dann
    sucht ``find_stockfish`` eine System-Installation.
    """
    cand = assets_root() / "engine" / "stockfish"
    return cand if cand.exists() else None


def data_dir() -> Path:
    """Beschreibbarer Ort für Nutzerdaten (Einstellungen, Statistik, Lernplan).

    Entwicklung: das vorhandene ``data/`` im Projekt (gemeinsam mit dem alten
    Programm). Verpackt: ein plattformüblicher, beschreibbarer Ordner im
    Benutzerverzeichnis.
    """
    if not _frozen():
        return Path("data")

    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "Opening Trainer"
    elif os.name == "nt":
        base = Path(os.environ.get("APPDATA", str(Path.home()))) / "Opening Trainer"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))) / "opening-trainer"
    base.mkdir(parents=True, exist_ok=True)
    return base
