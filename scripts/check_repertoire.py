"""One-off repertoire check: runs Stockfish over all lines and reports
suspicious moves of one's own side. Pure verification run (no UI).

Start:  python3 scripts/check_repertoire.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import chess
import chess.engine

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from opening_trainer.pgn_loader import load_pgn_folder  # noqa: E402
from qt_app.engine import find_stockfish, review_line     # noqa: E402

FOLDER = Path.home() / "Desktop" / "Repertoire"
SIDES = Path.home() / "Library" / "Application Support" / "Opening Trainer" / "opening_sides.json"
LIMIT = chess.engine.Limit(depth=14)


def load_sides() -> dict:
    """(source_name, line_name) -> 'white'/'black'/'none'."""
    raw = json.loads(SIDES.read_text())
    entries = raw.get("sides", []) if isinstance(raw, dict) else raw
    return {(e["source_name"], e["line_name"]): e["side"] for e in entries}


def main() -> int:
    sf = find_stockfish()
    if not sf:
        print("Kein Stockfish gefunden.")
        return 1
    lines = load_pgn_folder(FOLDER)
    sides = load_sides()
    print(f"Pruefe {len(lines)} Linien mit {sf} (depth {LIMIT.depth}) …\n", flush=True)

    engine = chess.engine.SimpleEngine.popen_uci(str(sf))
    total_issues = 0
    checked = 0
    try:
        for i, line in enumerate(lines, 1):
            side_str = sides.get((line.source_name, line.name))
            if side_str not in ("white", "black"):
                continue  # nur zugeordnete Linien pruefen
            checked += 1
            side = chess.WHITE if side_str == "white" else chess.BLACK
            issues = review_line(engine, line.moves_uci, side, LIMIT)
            if issues:
                print(f"[{i:3}] {line.name}  ({side_str})", flush=True)
                for it in issues:
                    ev = it.eval_after_cp / 100
                    print(
                        f"      Zug {it.move_number}: {it.san}  "
                        f"[{it.severity}, {it.loss_cp/100:+.1f} schlechter als {it.best_san}, "
                        f"Stellung danach {ev:+.1f}]",
                        flush=True,
                    )
                total_issues += len(issues)
    finally:
        engine.quit()

    print(f"\nFertig. {checked} zugeordnete Linien geprueft, {total_issues} Auffaelligkeiten.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
