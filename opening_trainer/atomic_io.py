"""Atomares Schreiben von Textdateien.

Erst in eine Temp-Datei IM SELBEN Ordner schreiben, durchsynchronisieren und dann
per ``os.replace`` an ihren Platz schieben (ein atomarer Rename auf einem Dateisystem).
So bleibt bei Absturz, Stromausfall oder voller Platte mitten im Schreiben die
bisherige Datei unversehrt — statt sie als halbe/leere Datei zu hinterlassen, aus der
die Stores dann kommentarlos einen LEEREN Speicher laden (= Datenverlust).
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path


def atomic_write_text(path: str | Path, text: str, encoding: str = "utf-8") -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), prefix=p.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding=encoding) as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, p)                 # atomarer Austausch: die alte Datei bleibt bis hierher gültig
    except BaseException:
        try:
            os.unlink(tmp)                 # halbe Temp-Datei aufräumen, Original nie anfassen
        except OSError:
            pass
        raise


def keep_damaged_copy(path: str | Path) -> None:
    """Legt von einer unlesbaren Speicherdatei eine Kopie »<name>.defekt« daneben,
    bevor die App mit leerem Speicher weitermacht — so überschreibt das nächste
    Speichern die (evtl. noch rettbaren) Daten nicht ersatzlos. Fehler dabei werden
    geschluckt: die Sicherung darf den Start nie verhindern."""
    import shutil
    p = Path(path)
    try:
        shutil.copyfile(p, p.with_name(p.name + ".defekt"))
    except OSError:
        pass
