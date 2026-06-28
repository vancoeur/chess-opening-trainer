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
