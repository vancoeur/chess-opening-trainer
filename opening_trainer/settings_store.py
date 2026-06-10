from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class AppSettings:
    last_pgn_folder: str = ""
    last_pgn_path: str = ""
    last_pgn_kind: str = ""
    train_color: str = "white"
    window_geometry: str = ""


class SettingsStore:
    """Speichert lokale Programmeinstellungen als JSON."""

    def __init__(self, settings: AppSettings | None = None) -> None:
        self.settings = settings or AppSettings()

    def to_dict(self) -> dict:
        return asdict(self.settings)

    @classmethod
    def from_dict(cls, data: dict) -> "SettingsStore":
        return cls(
            AppSettings(
                last_pgn_folder=str(data.get("last_pgn_folder", "")),
                last_pgn_path=str(data.get("last_pgn_path", "")),
                last_pgn_kind=str(data.get("last_pgn_kind", "")),
                train_color=str(data.get("train_color", "white")),
                window_geometry=str(data.get("window_geometry", "")),
            )
        )

    def update(
        self,
        *,
        last_pgn_folder: str | None = None,
        last_pgn_path: str | None = None,
        last_pgn_kind: str | None = None,
        train_color: str | None = None,
        window_geometry: str | None = None,
    ) -> None:
        self.settings = AppSettings(
            last_pgn_folder=(
                self.settings.last_pgn_folder
                if last_pgn_folder is None
                else last_pgn_folder
            ),
            last_pgn_path=(
                self.settings.last_pgn_path
                if last_pgn_path is None
                else last_pgn_path
            ),
            last_pgn_kind=(
                self.settings.last_pgn_kind
                if last_pgn_kind is None
                else last_pgn_kind
            ),
            train_color=self.settings.train_color if train_color is None else train_color,
            window_geometry=(
                self.settings.window_geometry
                if window_geometry is None
                else window_geometry
            ),
        )

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: str | Path) -> "SettingsStore":
        p = Path(path)
        if not p.exists():
            return cls()

        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return cls()
        return cls.from_dict(data)
