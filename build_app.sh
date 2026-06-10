#!/usr/bin/env bash
# Baut die moderne Qt-Oberfläche zu einer eigenständigen macOS-App
# (Doppelklick-Start, ohne Terminal).
#
# Voraussetzungen (einmalig):
#   python3 -m pip install --user PySide6 pyinstaller
#
# Danach:
#   ./build_app.sh
#   -> Ergebnis: dist/Opening Trainer.app
#
# Hinweis: Die App ist nicht signiert/notarisiert. Auf einem anderen Mac
# evtl. beim ersten Start Rechtsklick -> "Öffnen" wählen (Gatekeeper).
set -e
cd "$(dirname "$0")"

# Stockfish wird mitgeliefert (assets/engine/stockfish), damit die App auch
# ohne Homebrew laeuft. Fehlt die Datei, aus der lokalen Installation holen.
# Hinweis: arm64-Binary; fuer Intel-Macs eine x86_64-Stockfish-Datei ablegen.
if [ ! -f assets/engine/stockfish ]; then
  src="$(command -v stockfish || true)"
  if [ -z "$src" ]; then
    echo "FEHLER: assets/engine/stockfish fehlt und kein 'stockfish' im PATH."
    echo "        Installiere es (brew install stockfish) oder lege die Datei selbst ab."
    exit 1
  fi
  mkdir -p assets/engine
  cp "$(python3 -c "import os,sys;print(os.path.realpath(sys.argv[1]))" "$src")" assets/engine/stockfish
  chmod +x assets/engine/stockfish
  echo "Stockfish aus $src nach assets/engine/ kopiert."
fi

python3 -m PyInstaller \
  --name "Opening Trainer" \
  --windowed \
  --noconfirm \
  --osx-bundle-identifier "com.local.openingtrainer" \
  --icon "assets/app_icon.icns" \
  --add-data "assets:assets" \
  qt_main.py

echo
echo "Fertig: dist/Opening Trainer.app"
echo "Starten:  open 'dist/Opening Trainer.app'   (oder doppelklicken)"
