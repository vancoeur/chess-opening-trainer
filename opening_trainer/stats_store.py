from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path


@dataclass(frozen=True)
class TrainingEvent:
    timestamp: str
    source_name: str
    line_name: str
    fen_before: str
    expected_san: str | None
    played_san: str | None
    correct: bool


@dataclass(frozen=True)
class LineStats:
    attempts: int
    correct: int
    wrong: int
    accuracy: float
    last_trained: str | None


@dataclass(frozen=True)
class SetStats:
    """Aggregierte Statistik über eine Menge von Linien (Gruppe/Repertoire)."""

    lines_total: int
    lines_trained: int
    attempts: int
    correct: int
    wrong: int
    accuracy: float


@dataclass(frozen=True)
class ErrorPosition:
    fen_before: str
    expected_san: str | None
    wrong_count: int
    last_played_san: str | None
    last_timestamp: str

    def label(self) -> str:
        expected = self.expected_san or "?"
        last_played = self.last_played_san or "?"
        return f"{self.wrong_count}× Fehler · erwartet: {expected} · zuletzt gespielt: {last_played}"



@dataclass(frozen=True)
class WrongMoveSummary:
    fen_before: str
    expected_san: str | None
    played_san: str | None
    count: int
    last_timestamp: str

    def label(self) -> str:
        expected = self.expected_san or "?"
        played = self.played_san or "?"
        return f"{self.count}× · erwartet: {expected} · gespielt: {played}"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _epd_of_fen(fen: str) -> str:
    """EPD (transpositions-sicherer Schlüssel) = die ersten vier FEN-Felder
    (Figuren, Seite am Zug, Rochade, en passant) — ohne die Zähler."""
    return " ".join(fen.split(" ")[:4])


class StatsStore:
    """Speichert Trainingsereignisse und berechnet einfache Variantenstatistik."""

    def __init__(self) -> None:
        self.events: list[TrainingEvent] = []

    def add_event(
        self,
        *,
        source_name: str,
        line_name: str,
        fen_before: str,
        expected_san: str | None,
        played_san: str | None,
        correct: bool,
        timestamp: str | None = None,
    ) -> TrainingEvent:
        event = TrainingEvent(
            timestamp=timestamp or utc_now_iso(),
            source_name=source_name,
            line_name=line_name,
            fen_before=fen_before,
            expected_san=expected_san,
            played_san=played_san,
            correct=correct,
        )
        self.events.append(event)
        return event

    def stats_for_line(self, *, source_name: str, line_name: str) -> LineStats:
        relevant = [
            event
            for event in self.events
            if event.source_name == source_name and event.line_name == line_name
        ]

        attempts = len(relevant)
        correct = sum(1 for event in relevant if event.correct)
        wrong = attempts - correct
        accuracy = correct / attempts if attempts else 0.0
        last_trained = relevant[-1].timestamp if relevant else None

        return LineStats(
            attempts=attempts,
            correct=correct,
            wrong=wrong,
            accuracy=accuracy,
            last_trained=last_trained,
        )

    def stats_for_position(self, epd: str) -> LineStats:
        """Statistik einer einzelnen Stellung (epd-Schlüssel). Ereignisse sind
        bereits FEN-genau; die EPD = die ersten vier FEN-Felder (ohne Zähler),
        passend zu ``position_book.position_key`` / ``board.epd()``."""
        relevant = [e for e in self.events if _epd_of_fen(e.fen_before) == epd]
        attempts = len(relevant)
        correct = sum(1 for e in relevant if e.correct)
        wrong = attempts - correct
        accuracy = correct / attempts if attempts else 0.0
        last_trained = relevant[-1].timestamp if relevant else None
        return LineStats(attempts, correct, wrong, accuracy, last_trained)

    def stats_for_lines(self, lines) -> SetStats:
        """Fasst die Statistik mehrerer Linien zu einer Set-Statistik zusammen.

        ``lines_trained`` zählt die Linien mit mindestens einem Versuch. Die
        Trefferquote bezieht sich auf alle Versuche im Set zusammen.
        """
        lines_total = 0
        lines_trained = 0
        attempts = 0
        correct = 0
        wrong = 0

        for line in lines:
            lines_total += 1
            line_stats = self.stats_for_line(source_name=line.source_name, line_name=line.name)
            if line_stats.attempts > 0:
                lines_trained += 1
            attempts += line_stats.attempts
            correct += line_stats.correct
            wrong += line_stats.wrong

        accuracy = correct / attempts if attempts else 0.0

        return SetStats(
            lines_total=lines_total,
            lines_trained=lines_trained,
            attempts=attempts,
            correct=correct,
            wrong=wrong,
            accuracy=accuracy,
        )

    def order_lines_weakest_first(self, lines) -> list:
        """Sortiert Linien für gezieltes Üben: noch nie geübte zuerst (in
        ursprünglicher Reihenfolge), danach die geübten nach Trefferquote
        aufsteigend (schwächste oben). Stabil bei Gleichstand.
        """
        indexed = list(enumerate(lines))

        def sort_key(item):
            index, line = item
            stats = self.stats_for_line(source_name=line.source_name, line_name=line.name)
            trained = 1 if stats.attempts > 0 else 0
            accuracy = stats.accuracy if stats.attempts > 0 else 0.0
            return (trained, accuracy, index)

        return [line for _, line in sorted(indexed, key=sort_key)]

    def wrong_move_events_for_line(self, *, source_name: str, line_name: str) -> list[TrainingEvent]:
        """Gibt alle jemals falsch gespielten Einzelzüge einer Variante zurück.

        Diese Liste ist ein Protokoll. Ein späterer richtiger Zug löscht diese
        Ereignisse nicht.
        """
        return [
            event
            for event in self.events
            if event.source_name == source_name
            and event.line_name == line_name
            and not event.correct
        ]

    def wrong_move_summary_for_line(self, *, source_name: str, line_name: str) -> list[WrongMoveSummary]:
        """Gruppiert alle falschen Züge einer Variante.

        Gruppiert wird nach:
        - Stellung vor dem Zug
        - erwartetem Zug
        - tatsächlich falsch gespieltem Zug

        Anders als error_positions_for_line ist dies kein "offene Fehler"-Modell,
        sondern ein vollständiges Fehlerprotokoll in zusammengefasster Form.
        """
        grouped: dict[tuple[str, str | None, str | None], list[TrainingEvent]] = {}

        for event in self.wrong_move_events_for_line(source_name=source_name, line_name=line_name):
            key = (event.fen_before, event.expected_san, event.played_san)
            grouped.setdefault(key, []).append(event)

        summaries: list[WrongMoveSummary] = []

        for (fen_before, expected_san, played_san), events in grouped.items():
            last_event = events[-1]
            summaries.append(
                WrongMoveSummary(
                    fen_before=fen_before,
                    expected_san=expected_san,
                    played_san=played_san,
                    count=len(events),
                    last_timestamp=last_event.timestamp,
                )
            )

        summaries.sort(key=lambda item: (-item.count, item.last_timestamp))
        return summaries

    @staticmethod
    def _open_error_positions(events: list[TrainingEvent]) -> list[ErrorPosition]:
        """Aus einer (bereits gefilterten) Ereignisliste die noch offenen
        Fehlerstellungen ableiten: pro (Stellung, erwarteter Zug) zählt ein
        Fehlversuch hoch, ein späterer Treffer baut ihn wieder ab; bleibt am
        Ende ein offener Fehler übrig, gilt die Stellung als noch nicht gefestigt.
        Gemeinsame Grundlage für die linien- und die positions-basierte Sicht."""
        grouped: dict[tuple[str, str | None], list[TrainingEvent]] = {}
        for event in events:
            key = (event.fen_before, event.expected_san)
            grouped.setdefault(key, []).append(event)

        positions: list[ErrorPosition] = []
        for (fen_before, expected_san), evs in grouped.items():
            open_wrong_count = 0
            last_wrong_event: TrainingEvent | None = None
            last_relevant_timestamp: str | None = None

            for event in evs:
                last_relevant_timestamp = event.timestamp
                if event.correct:
                    if open_wrong_count > 0:
                        open_wrong_count -= 1
                else:
                    open_wrong_count += 1
                    last_wrong_event = event

            if open_wrong_count <= 0 or last_wrong_event is None:
                continue

            positions.append(
                ErrorPosition(
                    fen_before=fen_before,
                    expected_san=expected_san,
                    wrong_count=open_wrong_count,
                    last_played_san=last_wrong_event.played_san,
                    last_timestamp=last_relevant_timestamp or last_wrong_event.timestamp,
                )
            )

        positions.sort(key=lambda item: (-item.wrong_count, item.last_timestamp))
        return positions

    def error_positions_for_line(self, *, source_name: str, line_name: str) -> list[ErrorPosition]:
        relevant = [
            e for e in self.events
            if e.source_name == source_name and e.line_name == line_name
        ]
        return self._open_error_positions(relevant)

    def error_positions_for_epd(self, epd: str) -> list[ErrorPosition]:
        """Offene Fehlerstellungen für eine einzelne Stellung (EPD = erste vier
        FEN-Felder), FEN-genau über ALLE Eröffnungen. Grundlage des
        positions-basierten Fehler-Überblicks (Cutover Statistik/Fortschritt)."""
        relevant = [e for e in self.events if _epd_of_fen(e.fen_before) == epd]
        return self._open_error_positions(relevant)

    def most_common_error_position(self, *, source_name: str, line_name: str) -> ErrorPosition | None:
        positions = self.error_positions_for_line(source_name=source_name, line_name=line_name)
        if not positions:
            return None
        return positions[0]

    def to_dict(self) -> dict:
        return {"events": [asdict(event) for event in self.events]}

    @classmethod
    def from_dict(cls, data: dict) -> "StatsStore":
        store = cls()
        for raw in data.get("events", []):
            store.events.append(
                TrainingEvent(
                    timestamp=str(raw["timestamp"]),
                    source_name=str(raw["source_name"]),
                    line_name=str(raw["line_name"]),
                    fen_before=str(raw["fen_before"]),
                    expected_san=raw.get("expected_san"),
                    played_san=raw.get("played_san"),
                    correct=bool(raw["correct"]),
                )
            )
        return store

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: str | Path) -> "StatsStore":
        p = Path(path)
        if not p.exists():
            return cls()
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return cls()
        return cls.from_dict(data)
