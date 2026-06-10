from __future__ import annotations

import csv
from pathlib import Path

from opening_trainer.stats_store import StatsStore


CSV_FIELDS = [
    "timestamp",
    "source_name",
    "line_name",
    "fen_before",
    "expected_san",
    "played_san",
    "correct",
]


def export_training_events_csv(store: StatsStore, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    with p.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        writer.writeheader()

        for event in store.events:
            writer.writerow(
                {
                    "timestamp": event.timestamp,
                    "source_name": event.source_name,
                    "line_name": event.line_name,
                    "fen_before": event.fen_before,
                    "expected_san": event.expected_san or "",
                    "played_san": event.played_san or "",
                    "correct": "true" if event.correct else "false",
                }
            )
