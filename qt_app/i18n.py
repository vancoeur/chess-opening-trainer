"""Tiny language system for the interface (German / English).

Texts are kept bilingually inline in the code: ``t("Üben", "Train")``. The
current language is set once at startup (from the settings); a change takes
effect after a restart. This keeps it simple, with no live rebuild.
"""
from __future__ import annotations

_LANG = "de"


def set_language(lang: str) -> None:
    """Setzt die aktuelle Sprache (\"de\" oder \"en\")."""
    global _LANG
    _LANG = "en" if str(lang).lower().startswith("en") else "de"


def language() -> str:
    return _LANG


def t(de: str, en: str) -> str:
    """Gibt je nach aktueller Sprache den deutschen oder englischen Text zurück."""
    return en if _LANG == "en" else de
