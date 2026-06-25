"""Lädt die gemeinfreie ECO-Eröffnungsdatenbank (lichess-org/chess-openings, CC0)
und schreibt sie kompakt nach opening_trainer/data/eco_openings.tsv
(Spalten: eco <TAB> uci-Zugfolge). Einmal-Schritt; Datendatei wird eingecheckt.

Aufruf:  python3 tools/build_eco_data.py
"""
import ssl, urllib.request, pathlib, chess

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "opening_trainer/data/eco_openings.tsv"
BASE = "https://raw.githubusercontent.com/lichess-org/chess-openings/master/"
# Manche Python-Installs (Framework) haben kein lokales Zertifikat -> ungeprüft
# laden (Quelle ist öffentliche, gemeinfreie Datenbank; Ergebnis wird eingecheckt).
_CTX = ssl._create_unverified_context()

def to_uci(pgn):
    b = chess.Board(); out = []
    for tok in pgn.split():
        if tok.endswith(".") or tok[0].isdigit() or tok in ("1-0","0-1","1/2-1/2","*"):
            continue
        try:
            m = b.parse_san(tok)
        except Exception:
            return None
        out.append(m.uci()); b.push(m)
    return out

rows = []
for f in "abcde":
    data = urllib.request.urlopen(BASE + f + ".tsv", timeout=30, context=_CTX).read().decode("utf-8")
    for ln in data.splitlines()[1:]:
        parts = ln.split("\t")
        if len(parts) < 3:
            continue
        eco, name, pgn = parts[0], parts[1], parts[2]
        uci = to_uci(pgn)
        if uci:
            rows.append((eco, " ".join(uci)))

OUT.write_text("".join(f"{eco}\t{uci}\n" for eco, uci in rows), encoding="utf-8")
print(f"{len(rows)} Eröffnungen -> {OUT} ({OUT.stat().st_size//1024} KB)")
