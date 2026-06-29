# Changelog

All notable changes to **Opening Trainer**, newest first. Each release adds an
entry explaining what was added or extended. Ready-to-run downloads for every
version are on the [Releases page](https://github.com/vancoeur/chess-opening-trainer/releases).

The interface is bilingual (English/German); version numbers follow
`MAJOR.MINOR.PATCH`.

## [1.4.1] — 2026-06-29

**A clearer repertoire view — openings named by their ECO names.**

- **Repertoire tree, reorganised.** The repertoire page is no longer one long,
  endlessly-scrolling move list. It now shows your **named variations** as a
  **collapsible tree**: a handful of opening names up top, each expanding to its
  moves (the straight line opens to the first real branch in one click).
- **Openings named from the ECO database.** Each line is identified by its first
  moves against a built-in **ECO opening database** and grouped under its real
  opening name (e.g. *Caro-Kann Defense: Advance Variation*, *Sicilian Defense:
  Alapin Variation*). Where a line transposes into a foreign system that ECO can't
  name unambiguously (typical for setup systems like the **London**), the view
  falls back to your own — cleaned — chapter name instead of a wrong label.
- **Teaching chapters kept aside.** Introductions, instructive games and
  middlegame plans are collected into one **“Study material”** group at the end,
  so they don't clutter your opening variations.
- **Double-click a variation name** to train just that variation.
- **Blitz fix.** After a blitz round ends, **“Show solution”** now correctly
  marks the move on the board; the **“Idea”** line no longer shows raw Lichess
  arrow codes (`[%cal]`/`[%csl]`).
- **Clearer sidebar.** The section headers (Practice / Repertoire / Review /
  Explore) now stand out in the accent colour.

## [1.4.0] — 2026-06-28

**Two new ways to practise: a weak-spots radar and a timed blitz.**

- **Weak-spots radar.** The home screen now surfaces the positions you keep
  getting wrong as a **“Not solid yet”** card, with one button to drill exactly
  those — the most-missed first. This is separate from “Due today”: a position can
  be not due yet still trip you up every time, and now it won’t slip through. The
  **“Accuracy & mistakes”** page also gained a **“Drill all”** button to practise
  the whole mistake list at once instead of clicking each one. A single weak-spots
  round is capped so it stays short; the rest waits for the next round.
- **Blitz refresh.** A new **60-second sprint**: positions from your whole
  repertoire come fast, every correct move scores a point, and when the clock runs
  out you get your score and a restart. It’s a pressure-free speed drill, so it
  deliberately leaves your review schedule and mistake stats untouched — fast
  clicking can’t distort when things are next due. Start it from the home card or
  the **⏱ Blitz** entry in the sidebar.

## [1.3.0] — 2026-06-28

**A new look, a new icon, and notes are back.**

- **Refreshed colours & type.** The interface now uses a calm **blue** accent in
  light mode — on a subtle light-blue background with a distinct sidebar — and a
  warm charcoal with **green** in dark mode, set in a clean sans-serif. Switch
  under *View → Appearance*.
- **New app icon** — a faceted, dark Staunton knight in blue.
- **Per-opening notes are back.** Add a personal reminder to any opening from the
  “All openings” list (📝 button); it shows with a 📝 next to the opening.
- **One repertoire model.** Internal cleanup: the app now keeps a single
  position-based model of your repertoire (the old linear catalogue is gone), so
  the library, game review and side assignments all derive from the same trees.

## [1.2.0] — 2026-06-26

**A modern redesign.**

- **New look, light & dark.** A refreshed interface with an indigo accent, cleaner
  cards and spacing. Switch between **light and dark mode** under *View →
  Appearance* — the choice is remembered, and dark mode also picks a fitting board.
- **Fixed sidebar navigation.** A navigation rail on the left is now visible on
  every page, grouped *Practice / Repertoire / Review / Explore*, with the current
  page highlighted. It replaces the old “Go” menu; the familiar ⌘1–6 / R / E / D / T
  shortcuts still work.
- **Home is a dashboard.** The start page now shows a “due today” hero card with the
  train button plus at-a-glance cards (repertoires, positions, due this week).
- **More elegant typography.** Serif headings and numbers paired with a clean,
  humanist body font.
- **Streamlined training.** The position-based repertoire model is now the single
  training path; the old dormant linear-training code has been removed.

## [1.1.2] — 2026-06-24

**A home start page and smarter back navigation.**

- **New start page (home hub).** The app now opens on a clear home screen: the
  daily **“Train what's due (N)”** action with a today / tomorrow / this-week
  forecast (or a “try the samples” prompt for new users), plus tiles grouped
  *Practice / Repertoire / Review / Explore* that link to every part of the app.
  “Home” is now one place instead of two competing start screens.
- **“Back” returns to the previous page.** Every page’s back button now goes to the
  page you came from — stepping back through your path — and falls back to the home
  hub, instead of always jumping straight to the start.

## [1.1.1] — 2026-06-23

**Live language switching, plus fixes and a consistency pass.**

- **Language switch is now live.** Pick English or German under *View → Language*
  and the whole interface switches **immediately** — no restart needed. Window
  size, the current page and all your data are kept.
- **Due-today overview:** the per-opening *train* button could render as an empty
  box on wider windows — fixed. Scrollbars are now clearly visible, and the
  unnecessary horizontal scrollbar is gone.
- **Design consistency:** every page’s back button now reads *Back to start* and
  returns there reliably; page headers and margins are unified across the app.
- **Review games:** a clear, actionable message when macOS blocks a protected
  folder (Downloads/Desktop/Documents) instead of a raw error, and the file
  dialog opens in the folder where your PGNs are.
- **Opening explorer:** *Take back* now steps all the way back to move 1, and
  *Restart from move 1* reliably returns to the starting position.

## [1.1.0] — 2026-06-22

**Position-based spaced repetition, an in-app repertoire editor, and branched
repertoires.** The biggest update so far — daily review is now Chessable-style.

- **Daily review, position by position.** A new **“Due today” overview** breaks
  down what’s due per opening (*X due · Y new*), forecasts today / tomorrow /
  this week, and lets you drill a single opening. After each answer it shows when
  the position is next due. Transposing lines share one card, so nothing is
  reviewed twice. The line-by-line **“play a line”** mode stays available.
- **Loading a PGN now feeds the review automatically** and keeps its variations,
  so “Due today” fills for any loaded repertoire — not only migrated data.
- **Repertoire editor with variations.** Build and correct repertoires move by
  move in the app (add lines, promote a variation to the main line, delete,
  comment, export to PGN); your edits are kept across reloads.
- **One single load path** that preserves branches and comments; the separate
  “import as trees” entry is gone.
- **Player color auto-detected** from the file name on load, and rare first moves
  (1.b3, 1.g3, 1.Nc3 …) are grouped correctly.
- **UX polish:** sparring and the Lichess explorer reachable from the menu;
  friendlier empty states and onboarding; clearer move feedback; editor
  move-list no longer jumps to the top when you click a later move.
- **Stability:** fixed a crash on quit (background worker threads weren’t always
  stopped before shutdown).

## [1.0.4] — 2026-06-14

**Interface quality-of-life.**

- **Selectable board colors.** New menu *View → Board color* with four themes —
  Green (default), Wood, Blue, Grey — applied instantly and remembered.
- **File and Go menus with keyboard shortcuts.** A proper menu bar: *File* → Load
  PGN (⌘O), Load folder (⇧⌘O); *Go* → Home (⌘1), All openings (⌘2), Analysis
  (⌘3), Progress (⌘4), Review games (⌘5), Repertoire check (⌘6).
- **Evaluation bar aligned to the board** — it now starts and ends exactly at the
  board’s top and bottom edges.

## [1.0.3] — 2026-06-14

**Wording polish.**

- Renamed the German label of the Stockfish repertoire scan from
  “Repertoire-TÜV” to the clearer **“Repertoire-Prüfung”**. The English label
  (“Repertoire check”) is unchanged.

## [1.0.2] — 2026-06-14

**Easier Lichess explorer and first steps.**

- **One-click Lichess token setup.** The “🔑 Lichess token” button opens a guided
  dialog with a *“Create token on Lichess”* button — the token page opens in your
  browser already filled in, with no permissions to tick.
- **Help → Getting started** — a short in-app guide to the key flows.
- **Help → Open project website** links to the GitHub repository.
- Fixed: the About dialog showed a stale version number.

## [1.0.1] — 2026-06-12

**Friendlier first start.**

- **Three sample openings included** (Italian Game, Caro-Kann, Queen’s Gambit
  Declined): on first start, one click on *“🎁 Try the sample openings”* and you
  can explore every feature immediately — no own PGN needed yet.
- **The interface follows your system language** (English/German) on first start;
  switch any time via *View → Language*.
- The first-start screen is now fully translated.

## [1.0] — 2026-06-12

**First public release** — a free, open-source chess opening trainer for the Mac.

- Practice your own **White & Black opening repertoires** (PGN import) with
  spaced repetition (“due today”).
- **Stockfish built in** (no installation): repertoire check, “was my move good?”,
  evaluation bar, and sparring against the engine.
- **Lichess opening explorer** — see what is played in real games (requires a free,
  no-permission Lichess API token).
- **Review your games** — load a PGN of your played games and see where you left
  your repertoire and where you blundered.

[1.4.1]: https://github.com/vancoeur/chess-opening-trainer/releases/tag/v1.4.1
[1.4.0]: https://github.com/vancoeur/chess-opening-trainer/releases/tag/v1.4.0
[1.1.2]: https://github.com/vancoeur/chess-opening-trainer/releases/tag/v1.1.2
[1.1.1]: https://github.com/vancoeur/chess-opening-trainer/releases/tag/v1.1.1
[1.1.0]: https://github.com/vancoeur/chess-opening-trainer/releases/tag/v1.1.0
[1.0.4]: https://github.com/vancoeur/chess-opening-trainer/releases/tag/v1.0.4
[1.0.3]: https://github.com/vancoeur/chess-opening-trainer/releases/tag/v1.0.3
[1.0.2]: https://github.com/vancoeur/chess-opening-trainer/releases/tag/v1.0.2
[1.0.1]: https://github.com/vancoeur/chess-opening-trainer/releases/tag/v1.0.1
[1.0]: https://github.com/vancoeur/chess-opening-trainer/releases/tag/v1.0
