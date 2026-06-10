# Third-Party Notices

Opening Trainer itself is licensed under the **GPLv3+** (see `LICENSE`). This
file lists the third-party components it uses and their licenses, as required
by those licenses.

---

## Stockfish (chess engine) — **bundled**

- **Use:** Bundled as a standalone program (`assets/engine/stockfish`) and
  driven via the UCI protocol (repertoire check, evaluation, “Was my move
  good?”, sparring, game analysis).
- **Version:** Stockfish 18 (arm64).
- **License:** **GNU General Public License v3** (GPLv3).
- **Source code:** https://github.com/official-stockfish/Stockfish
- **Copyright:** © The Stockfish developers.

Because Stockfish is bundled under the GPLv3, its complete source code is
available at the link above. The bundled binary can be replaced with your own
build of Stockfish at any time.

## python-chess (chess library)

- **Use:** Imported Python library (move logic, SAN/UCI/FEN, PGN reading,
  engine integration).
- **License:** **GPL-3.0-or-later**.
- **Project:** https://github.com/niklasf/python-chess
- **Copyright:** © Niklas Fiekas and contributors.

Because python-chess is imported as a library, the combined work Opening
Trainer is likewise under the GPLv3+.

## Qt / PySide6 (user interface)

- **Use:** GUI toolkit (dynamically linked; included in the packaged app).
- **License:** **GNU Lesser General Public License v3** (LGPLv3) — or usable
  under a commercial Qt license. Used here under the LGPLv3.
- **Project:** https://www.qt.io/qt-for-python — Qt: https://www.qt.io/
- **Copyright:** © The Qt Company Ltd. and contributors.

The LGPLv3 permits distribution together with this program. The source code of
Qt/PySide6 is available via the project pages above; the Qt libraries can be
replaced.

## Cburnett chess pieces (graphics)

- **Use:** Piece graphics under `assets/pieces/` (Lichess’ default piece set).
- **Author:** Colin M. L. Burnett.
- **Source:** Wikimedia Commons (`Chess_*45.svg`).
- **License:** Multi-license **GPLv2+ / BSD / GFDL** (free to use with
  attribution). See `assets/pieces/README.md`.

## PyInstaller (build only)

- **Use:** Builds the standalone Mac app from source (`build_app.sh`). The
  bundled PyInstaller bootloader is under the **GPL with an exception clause**
  that explicitly permits distributing the resulting app under any license
  (here: GPLv3+).
- **Project:** https://pyinstaller.org/
