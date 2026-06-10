from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from opening_trainer.stats_store import TrainingEvent


@dataclass(frozen=True)
class TrainingSessionSummary:
    started_at: str
    ended_at: str
    attempts: int
    correct: int
    wrong: int
    accuracy: float


@dataclass(frozen=True)
class ProgressOverview:
    session_count: int
    attempts: int
    correct: int
    wrong: int
    accuracy: float
    first_accuracy: float | None
    last_accuracy: float | None


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value)


def summarize_training_sessions(
    events: Iterable[TrainingEvent],
    *,
    max_gap_minutes: int = 30,
) -> list[TrainingSessionSummary]:
    sorted_events = sorted(events, key=lambda event: event.timestamp)
    if not sorted_events:
        return []

    sessions: list[list[TrainingEvent]] = []
    current: list[TrainingEvent] = [sorted_events[0]]

    for event in sorted_events[1:]:
        previous = current[-1]
        gap_seconds = (_parse_timestamp(event.timestamp) - _parse_timestamp(previous.timestamp)).total_seconds()

        if gap_seconds > max_gap_minutes * 60:
            sessions.append(current)
            current = [event]
        else:
            current.append(event)

    sessions.append(current)

    summaries: list[TrainingSessionSummary] = []
    for session_events in sessions:
        attempts = len(session_events)
        correct = sum(1 for event in session_events if event.correct)
        wrong = attempts - correct
        summaries.append(
            TrainingSessionSummary(
                started_at=session_events[0].timestamp,
                ended_at=session_events[-1].timestamp,
                attempts=attempts,
                correct=correct,
                wrong=wrong,
                accuracy=correct / attempts if attempts else 0.0,
            )
        )

    return summaries


def overall_progress(events: Iterable[TrainingEvent], *, max_gap_minutes: int = 30) -> ProgressOverview:
    """Gesamtüberblick über alle Trainingseinheiten: Anzahl Sitzungen,
    Versuche, Gesamt-Trefferquote sowie die Trefferquote der ersten und der
    letzten Sitzung (für die Tendenz). Rein und testbar."""
    sessions = summarize_training_sessions(events, max_gap_minutes=max_gap_minutes)
    attempts = sum(session.attempts for session in sessions)
    correct = sum(session.correct for session in sessions)
    wrong = attempts - correct

    return ProgressOverview(
        session_count=len(sessions),
        attempts=attempts,
        correct=correct,
        wrong=wrong,
        accuracy=correct / attempts if attempts else 0.0,
        first_accuracy=sessions[0].accuracy if sessions else None,
        last_accuracy=sessions[-1].accuracy if sessions else None,
    )
