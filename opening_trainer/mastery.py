"""Pure mastery classification per opening (for the progress overview).

Engine-/UI-independent and testable. From the existing training data
(attempts + accuracy) a simple bucket is derived:

- ``"neu"``     — never practised
- ``"wackelt"`` — practised, but accuracy below the threshold
- ``"sitzt"``   — practised and accuracy above the threshold
"""
from __future__ import annotations

SITZT_ACCURACY = 0.85   # ab hier gilt eine geübte Eröffnung als „sitzt"

BUCKETS = ("sitzt", "wackelt", "neu")


def mastery_bucket(attempts: int, accuracy: float) -> str:
    """Stuft eine Eröffnung anhand Versuche + Trefferquote (0..1) ein."""
    if attempts <= 0:
        return "neu"
    if accuracy >= SITZT_ACCURACY:
        return "sitzt"
    return "wackelt"


def summarize_mastery(items: list[tuple[int, float]]) -> dict[str, int]:
    """Zählt, wie viele Eröffnungen in jeden Eimer fallen.

    ``items`` ist eine Liste von ``(versuche, trefferquote)``.
    """
    counts = {b: 0 for b in BUCKETS}
    for attempts, accuracy in items:
        counts[mastery_bucket(attempts, accuracy)] += 1
    return counts
