# Opening Trainer

**English** · [Deutsch](README.de.md)

[![Support on Ko-fi](https://img.shields.io/badge/Ko--fi-Support%20this%20project-FF5E5B?logo=ko-fi&logoColor=white)](https://ko-fi.com/vancoeur)

A personal chess **opening trainer** for the Mac — practice your own
repertoires (White and Black) with **spaced repetition**, build and correct them
in a built-in **editor** (variations and all), drill the moves you keep getting
wrong, and have **Stockfish** check your lines and your played games.

> Modern Qt/PySide6 interface. Stockfish is bundled — the app runs on its own,
> no extra installation. The interface is available in **English and German**.

![Screenshot — Opening Trainer in English: the repertoire tree with the new sidebar](docs/screen-en.png)

*Modern interface with a fixed sidebar. **Light or dark** (View → Appearance) and **English or German** (View → Language). Here in English, light — the [same window in German](docs/screen-de.png).*

## Download (ready-to-run app)

**[⬇ Download the latest release](https://github.com/vancoeur/chess-opening-trainer/releases/latest)** — unzip and drag `Opening Trainer.app` into your `Applications` folder. Requires a Mac with **Apple Silicon** (M1 or newer); Intel Macs are not supported by this build.

> See the **[changelog](CHANGELOG.md)** for what was added or extended in each version.

> **⚠️ Important — first launch (Gatekeeper):**
> The app is **not signed or notarised** (this is a free, open-source project without
> an Apple Developer subscription). macOS will therefore **block the first start**.
> On Apple Silicon Macs you often get *“Opening Trainer” is damaged and can’t be
> opened* — **the app is NOT damaged**; that is just Apple’s block on unsigned apps
> downloaded from the internet.
>
> **Reliable method — remove the quarantine flag (Terminal):**
> 1. Open **Terminal** (Applications → Utilities → Terminal).
> 2. Type — or copy — this command, but **do not press Enter yet:**
>    ```
>    xattr -dr com.apple.quarantine
>    ```
> 3. Press the **spacebar once** — there **must** be a single space after the command.
> 4. **Drag `Opening Trainer.app` from the Finder into the Terminal window.** Its path is inserted automatically after the space.
> 5. Press **Enter**. Then open the app by **double-click**.
>
> The finished line should look like this (path depends on where the app is):
> ```
> xattr -dr com.apple.quarantine /Users/you/Downloads/Opening\ Trainer.app
> ```
> *Shortcut:* if the app sits in your **Downloads** folder under its original name, you can paste this whole line and press Enter instead:
> ```
> xattr -dr com.apple.quarantine ~/Downloads/"Opening Trainer.app"
> ```
>
> **GUI alternative:** open the app once, dismiss the warning, then go to
> **System Settings → Privacy & Security**, scroll down to *“… was blocked…”* and
> click **“Open Anyway”**. (On recent macOS the old right-click → *Open* trick no
> longer bypasses this.)
>
> This is needed **only once** — afterwards the app starts normally by double-click.

The app ships with **three sample openings** (Italian Game, Caro-Kann, Queen’s Gambit Declined) so you can try everything immediately — load your own PGN repertoire whenever you’re ready. The interface follows your system language (English/German) and can be switched any time.

## What it does

- **Daily review (spaced repetition):** the app shows what’s **due today** —
  position by position, so transposing lines share one card and nothing is
  reviewed twice. A **“Due today” overview** breaks it down per opening
  (*X due · Y new*), forecasts today / tomorrow / this week, and lets you drill a
  single opening; after each answer it shows when the position is next due.
- **Repertoire tree, grouped by opening name:** your whole repertoire as a
  **collapsible tree**, grouped under the **named variations** it belongs to —
  identified from a built-in **ECO opening database** (e.g. *Caro-Kann Defense:
  Advance Variation*, *Sicilian Defense: Alapin Variation*). Expand a variation,
  **double-click a name to train just that variation**, and spot **gaps** (⚠ lines
  where it’s your move but no reply is stored yet).
- **Blitz refresh** — a **60-second sprint** across your whole repertoire: positions
  come fast, one point per correct move. A pressure-free speed drill that
  deliberately leaves your review schedule and mistake stats untouched.
- **Weak-spots radar** — the positions you keep getting wrong surface as a
  **“Not solid yet”** card on the home screen (and on *Accuracy & mistakes*), so you
  can drill exactly those, most-missed first.
- **Build & edit repertoires — with variations:** loading a PGN keeps its
  **branches and comments**; or build and correct a repertoire move by move in
  the **in-app editor** (add lines, promote a variation to the main line, delete,
  comment, export back to PGN).
- **Practice on the board** (drag or click-click) with automatic opponent
  replies; or **free-play a tree** to step through a whole line end to end —
  optionally playing the opponent’s moves yourself.
- **White/Black repertoire:** the side is auto-detected from the file name on
  load; assign or change it any time, and train a whole side or your whole
  repertoire.
- **Library** of all openings with a **search field** and automatic groups
  (e.g. “Black ▸ vs 1.e4 ▸ Sicilian”).
- **Analysis** with a mistake log and targeted mistake drills.
- **Progress** view — see at a glance which openings are solid, shaky or
  untrained, and filter by category.
- **Notes** — add a personal reminder to any opening (under “All openings”);
  it shows with a 📝 in the list.
- **Stockfish features:**
  - **Repertoire check** — scans every assigned line and flags suspicious moves
    of your side (blunders / inaccuracies), so you don’t memorise mistakes.
    Each finding is clickable to train.
  - **“Was my move good?”** — when you deviate while practising, the engine
    tells you whether your move was equal, slightly worse, or a mistake.
  - **Evaluation bar** beside the analysis boards (repertoire check, game
    viewer) when Stockfish is present.
  - **Sparring** — play the opening position out against Stockfish (three
    strengths), with take-back and a blunder hint.
- **Lichess opening explorer** — see what is actually played in each position
  (move frequencies and white/draw/black results). Requires a free Lichess API
  token (no permissions needed).
- **Review your games** — load a PGN of your played games (Lichess, chess.com,
  any platform) and see **where you left your repertoire** and, with Stockfish,
  **where you blundered** — with a board viewer to step through each game.
- **Load PGN** (single file or whole folder) — **variations are kept** and feed
  the position review. Your PGN stays original material; training data stays
  local and private.
- **Modern interface** — a fixed sidebar for navigation and a **light/dark**
  mode (*View → Appearance*).
- **English / German interface** — switch any time via *View → Language*; the
  interface changes **instantly**, no restart needed. Opening names are
  translated too.

## Requirements

- **macOS** (Apple Silicon / arm64 for the bundled Stockfish binary)
- **Python 3.10+**
- Python packages: **PySide6**, **python-chess** (see `requirements.txt`)
- **Stockfish** — bundled for the packaged app; when running from source it is
  found under `assets/engine/stockfish` or in your system (`brew install
  stockfish`).

## Run from source

```bash
python3 -m pip install -r requirements.txt
python3 qt_main.py
```

## Build a standalone Mac app

```bash
./build_app.sh          # produces: dist/Opening Trainer.app
```

The script bundles Stockfish automatically (from `assets/engine/stockfish` or
your local installation) and re-signs the bundle **ad-hoc** after stamping the
version (so the code signature stays valid). The app is still **not
notarised** — on another Mac, clear the quarantine flag on first launch (see
[Download → first launch](#download-ready-to-run-app)).

## Tests

```bash
python3 -m pytest -q
```

## Where is my data?

- **From source:** in the project folder `data/`.
- **Packaged app:** `~/Library/Application Support/Opening Trainer/`
  (settings, statistics, schedule, repertoire assignment).

These files are local and private; they are not version-controlled.

## License

This program is **free software** under the **GNU General Public License v3 or
later** (GPLv3+) — see [`LICENSE`](LICENSE).

Why: Opening Trainer uses **python-chess** (GPL-3.0+) and bundles **Stockfish**
(GPLv3). You may use, share and modify the app; if you pass it on, the source
must come with it and recipients get the same freedoms.

Third-party components and their licenses are listed in [`NOTICE.md`](NOTICE.md)
(Stockfish, python-chess, Qt/PySide6, Cburnett pieces).

## Support

Opening Trainer is free and open source, and always will be. If it helps your
chess and you’d like to say thanks, you can
[buy me a coffee on Ko-fi](https://ko-fi.com/vancoeur) ☕ — completely optional,
hugely appreciated, and it keeps the project going.

## Layout (overview)

- `qt_main.py` — entry point of the Qt interface
- `qt_app/` — interface (window, board, Stockfish/Lichess integration)
- `opening_trainer/` — toolkit-independent core logic (PGN, training, spaced
  repetition, statistics, judgement logic), tested under `tests/`
- `assets/` — piece graphics, app icon, bundled Stockfish
- `legacy/` — the earlier Tkinter program (archived, still runnable)

## Development principles

- Tests first, then UI.
- Keep core logic and interface separate.
- Small, secured steps; PGN stays original material.
- Training data stays local and private.
