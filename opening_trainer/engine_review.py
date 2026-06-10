"""Pure judgement logic for the repertoire check (engine-independent, testable).

The actual Stockfish integration lives in ``qt_app/engine.py``. Here we only
decide: *how bad* is a move, given its centipawn loss versus the best move and
the resulting evaluation — so this core can be tested without a running engine.

Always from the point of view of the side to move: positive centipawns = good
for that side, negative = bad.
"""
from __future__ import annotations

from dataclasses import dataclass

# Schwellen in Centibauern (100 = eine Bauerneinheit).
PATZER_LOSS = 300      # so viel schlechter als der beste Zug => grober Fehler
UNGENAU_LOSS = 150     # spürbar schlechter => Ungenauigkeit
# … aber nur melden, wenn die Stellung danach wirklich (zu) schlecht steht:
PATZER_EVAL_MAX = -100
UNGENAU_EVAL_MAX = -50
# Klar verlorene Endstellung: immer Patzer, auch wenn der relative Verlust
# (gegen den ohnehin schon schlechten besten Zug) unter PATZER_LOSS bleibt —
# solange es überhaupt einen spürbar besseren Zug gab. So wird eine Linie, die
# auf -5 endet, nicht als harmlose „Ungenauigkeit" verharmlost.
LOST_EVAL = -250
LOST_MIN_LOSS = 100


@dataclass(frozen=True)
class MoveIssue:
    ply: int            # 0-basierter Halbzug-Index in der Linie
    move_number: int    # menschliche Zugnummer (1, 2, 3 …)
    san: str            # gespielter Zug
    best_san: str       # was Stockfish bevorzugt
    loss_cp: int        # um so viele Centibauern schlechter als der beste Zug
    eval_after_cp: int  # Bewertung nach dem gespielten Zug (aus seiner Sicht)
    severity: str       # "patzer" | "ungenau"


# Schwellen für die Bewertung eines vom Repertoire abweichenden Zuges beim Üben.
DEVIATION_OK = 40       # bis hierher gleichwertig (oder besser als der Repertoire-Zug)
DEVIATION_BAD = 150     # darüber: echter Fehler


# Sparring: Stärke-Stufe -> (Stockfish „Skill Level" 0-20, Bedenkzeit ms).
_SPARRING_LEVELS = {
    "anfaenger": (1, 100),
    "mittel": (7, 250),
    "stark": (16, 450),
}


SPAR_BLUNDER_DROP = 150   # so viel Verschlechterung durch den eigenen Zug => Hinweis


def is_blunder_move(
    before_white_cp: int,
    after_white_cp: int,
    mover_is_white: bool,
    threshold: int = SPAR_BLUNDER_DROP,
) -> bool:
    """Hat der eigene Zug die Stellung deutlich verschlechtert? (Sparring-Hinweis)

    Beide Bewertungen aus *Weiß*-Sicht (Centibauern). Rechnet auf die Sicht des
    Ziehenden um und prüft, ob die Bewertung durch den Zug um mehr als
    ``threshold`` gefallen ist.
    """
    before_pov = before_white_cp if mover_is_white else -before_white_cp
    after_pov = after_white_cp if mover_is_white else -after_white_cp
    return (before_pov - after_pov) > threshold


def sparring_strength(level: str) -> tuple[int, int]:
    """Übersetzt eine Stärke-Stufe in (Skill Level, Bedenkzeit in ms).

    Unbekannte Stufe -> „mittel". So bleibt das Gegner-Niveau spielbar
    (voller Stockfish wäre zum Üben unbrauchbar).
    """
    return _SPARRING_LEVELS.get(level, _SPARRING_LEVELS["mittel"])


def judge_deviation(loss_cp: int, eval_after_cp: int) -> str:
    """Bewertet einen Zug, der vom Repertoire-Zug abweicht (beim Üben).

    ``loss_cp`` = wie viele Centibauern schlechter als der Repertoire-Zug
    (negativ, falls der gespielte Zug sogar besser ist). ``eval_after_cp`` =
    Bewertung der Stellung danach aus Sicht des Ziehenden.

    Rückgabe: ``"gleichwertig"`` | ``"ungenau"`` | ``"fehler"``.
    """
    if loss_cp > DEVIATION_BAD or (eval_after_cp <= LOST_EVAL and loss_cp >= LOST_MIN_LOSS):
        return "fehler"
    if loss_cp > DEVIATION_OK:
        return "ungenau"
    return "gleichwertig"


def classify_loss(loss_cp: int, eval_after_cp: int) -> str | None:
    """Stuft einen Zug ein. Gibt ``None`` zurück, wenn er in Ordnung ist.

    Es muss BEIDES zutreffen: deutlicher Verlust gegenüber dem besten Zug UND
    eine danach wirklich schlechte Stellung. So bleiben bewusst gewählte,
    leicht passive Eröffnungszüge unbeanstandet — nur echte Patzer fallen auf.
    """
    if eval_after_cp <= LOST_EVAL and loss_cp >= LOST_MIN_LOSS:
        return "patzer"
    if loss_cp >= PATZER_LOSS and eval_after_cp <= PATZER_EVAL_MAX:
        return "patzer"
    if loss_cp >= UNGENAU_LOSS and eval_after_cp <= UNGENAU_EVAL_MAX:
        return "ungenau"
    return None
