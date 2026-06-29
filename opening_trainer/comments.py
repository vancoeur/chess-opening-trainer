"""Kommentar-Aufbereitung für die Anzeige.

PGN-Kommentare aus Lichess-Studien enthalten oft **Zeichen-Anweisungen** wie
``[%csl Ga5,Gc4]`` (farbige Felder) oder ``[%cal Gc6a5,Ga5c4]`` (farbige Pfeile)
sowie Uhr-/Eval-Marken (``[%clk ...]``, ``[%eval ...]``). Für die »Idee«-Zeile im
Training sollen diese rohen Codes NICHT als Text erscheinen — nur der lesbare
Resttext. Die Rohdaten bleiben im Baum erhalten (für späteres Pfeil-Zeichnen);
hier wird ausschließlich der Anzeige-Text gesäubert.
"""
import re

_MARKUP = re.compile(r"\[%[^\]]*\]")


def clean_comment_text(comment: str) -> str:
    """Entfernt ``[%...]``-Anweisungen aus einem Kommentar und liefert den
    lesbaren Resttext (Mehrfach-Leerzeichen zusammengezogen, getrimmt)."""
    if not comment:
        return ""
    without = _MARKUP.sub("", comment)
    return re.sub(r"\s+", " ", without).strip()


# Studien-Lärm vor dem eigentlichen Variantennamen (Lichess-Kapitel).
_CHAPTER_PREFIX = re.compile(
    r"^\s*(chapter\s*#?\d+|quickstarter guide|quickstarter|introduction)[\s\-–:]*",
    re.IGNORECASE,
)
# Vorangestellter ECO-Code (»B18 · …«, »C65 - …«).
_ECO_PREFIX = re.compile(r"^\s*[A-E]\d{2}\s*[·\-–:]\s*")
# Angehängtes Zugfragment am Ende (»… - e4 c6 2. d4 …«).
_MOVE_TAIL = re.compile(r"\s*[-–]\s*(\d+\.\s*)?[a-h][1-8]?\b.*$")


def clean_chapter_name(name: str) -> str:
    """Macht aus einem rohen Studien-Kapitelnamen einen lesbaren Variantennamen:
    entfernt »Chapter #N:«, »Quickstarter Guide«, »Introduction«, angehängte
    Zugfragmente und PGN-Markup. Z. B. »Chapter #10: - Classical Variation -
    Karpov - e4 c6 …« → »Classical Variation - Karpov«."""
    s = clean_comment_text(name or "")
    s = _ECO_PREFIX.sub("", s)
    s = _CHAPTER_PREFIX.sub("", s)
    s = _MOVE_TAIL.sub("", s)
    s = re.sub(r"(\s*[-–]\s*){2,}", " - ", s)        # »Kasparov - - Ivanchuk« -> » - «
    s = re.sub(r"\s*[-–]\s*$", "", s).strip()
    return s
