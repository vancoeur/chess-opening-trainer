# Changelog

All notable changes to **Opening Trainer**, newest first. Each release adds an
entry explaining what was added or extended. Ready-to-run downloads for every
version are on the [Releases page](https://github.com/vancoeur/chess-opening-trainer/releases).

The interface is bilingual (English/German); version numbers follow
`MAJOR.MINOR.PATCH`.

## [1.6.3] — 2026-07-04

**A deep hardening pass — five review rounds across every part of the app.** The
look and the way you work are unchanged; the app just behaves correctly in many
more places, and a few things that could lose data or freeze can no longer happen.
Highlights:

- **No silent data loss.** Two different files that happen to share a filename and
  a chapter name no longer overwrite each other — both repertoires are kept.
  Editing a loaded opening survives restart. Notes are written safely so a crash
  mid-save can't wipe them.
- **No freezes or crashes.** A daily-review streak on one position can no longer
  overflow the schedule and crash the drill; "Play Stockfish" no longer freezes on
  "Stockfish is thinking…" after an engine hiccup.
- **Displays always current.** Deleting or loading a repertoire immediately updates
  the repertoire-tree list, dashboard and stats — no more stale entries lingering
  until restart. Study/puzzle chapters no longer clutter the opening selector.
- **Correct numbers and review.** The mistakes list shows the move you actually
  played (not the correct one); overall accuracy ignores openings you've deleted;
  games and the repertoire check honour a study's own start position (Chess960 /
  set-up positions) instead of misreading them; the repertoire check no longer
  shows stale results after you edit.
- **Look & language polish.** Switching light/dark keeps your chosen board colour;
  a board-colour change now recolours every board; German move notation is used in
  the drill hints ("Lösung: Sf3"); the opening explorer cancels superseded requests
  and shows a clear "too many requests — wait a moment" message.
- Import/export now preserves move glyphs (!, ?, !!) and a chapter's intro comment,
  and warns when a PGN has unreadable moves.

## [1.6.2] — 2026-07-04

**Correctness pass — ten fixes from a full review of every flow, each with a test.**
Nothing about the look or the way you work changes; the app just behaves correctly
in more places. Highlights:

- **No more lost edits.** Editing a loaded opening in the editor (adding a note,
  deleting a move, promoting a line, changing the side) used to be silently wiped
  the next time the app started. Your edits now survive, with no duplicate opening
  appearing beside them.
- **"Train this variation" stays on the opening you picked.** With several
  repertoires loaded, training a variation (or the starting move) could jump to a
  different opening that shares the same position — e.g. the Italian showing the
  English's 1.c4. It now always trains the opening you selected.
- **Game analysis can't land on the wrong game.** Starting Stockfish analysis and
  then switching games no longer paints the old game's blunder marks onto the new
  one.
- **Practice sessions don't leak state.** Leaving a daily session's learn mode for
  a free tree drill no longer freezes the board; the "play opponent moves myself"
  checkbox no longer disagrees with what actually happens.
- **Safer saved data.** All data is now written atomically, so a crash mid-save
  can't leave a truncated file that wipes your repertoire; a corrupt opening is
  skipped on load instead of crashing the editor.
- Smaller fixes: the "due today" per-opening counts no longer double-count shared
  positions; a file mixing White and Black chapters tags each chapter correctly;
  "Drill weak spots" shows a message instead of doing nothing when a position
  can't be found; descriptive chapter names like "London - d4 setup" are no longer
  truncated.

## [1.6.1] — 2026-07-03

**Small polish on the practice screen.**

- The opening name above the board is now a modest one-line label instead of a
  page-title-sized heading that could wrap across two lines.
- In a weak-spots round the "Show new positions first (learn)" checkbox is
  hidden — weak spots are always quizzed directly, so it had no effect there.

## [1.6.0] — 2026-07-03

**A friendlier finish and a gentler start.** Small touches that make the daily
loop feel complete and welcome newcomers.

- **Session-end summary card.** Finishing your "Train today" round now ends on
  a proper card instead of a bare line: how many you got **right first try**,
  how many needed **help**, how many were **newly learned** — plus an honest
  look ahead (still open today, or due again tomorrow) and one adaptive button
  (**Keep training** / **Drill weak spots**). The card knows its context: after
  a weak-spots round it talks about weak spots, not the daily plan.
- **Gentle 3-step onboarding.** A brand-new user is greeted with a **Welcome**
  card spelling out the three steps — load a repertoire · assign a side · train
  today — with **Try the samples** and **Load your PGN …** right there.
- **Weak spots are always quizzed.** Drilling your weak spots now tests you
  directly instead of showing the move first.
- **Sharper sidebar.** "Free-play" drops the "tree" jargon, and **Repertoire
  check** moved from *Practice* to *Review* (it's engine analysis, not
  practice) — so *Practice* now holds only real practice.

## [1.5.0] — 2026-07-02

**One clear way to practise — a calmer, more intuitive flow.** No new learning
machinery; the same spaced-repetition engine, reached through far fewer, clearer
buttons.

- **Home screen is one command centre.** The big **“Train today”** button now
  starts the day’s due session **immediately** — no more landing on an
  in-between page and pressing “Train all” again. The per-opening breakdown is
  still there, one small link away (“View breakdown”).
- **Clearer dashboard numbers.** The first card counts **real repertoires**
  (named openings), not chapters; “this week” is now **cumulative** (today +
  the rest of the week), and a one-line note explains the day’s round
  (reviews + new positions).
- **Repertoire tree: one button that adapts to your selection.** Select a
  **variation**, a **position**, or the **whole repertoire** and a single
  button trains exactly that — no greyed-out “broken-looking” buttons and no
  hidden double-click knowledge. A **gap (⚠)** turns it into
  “Fix in editor”, jumping straight to the missing move.
- **Library routes into the tree.** The library’s own train buttons are gone;
  clicking an opening (or **“Open in repertoire tree”**) takes it into the
  repertoire tree — the one place for targeted training. The library is now for
  finding, assigning sides and notes.
- **Consistent wording.** The mistake list’s button is now **“Drill weak
  spots”**, matching the home-screen card; the buried “Train selected”
  duplicate in the manage-sources dialog is gone.
- **Docs & help refreshed** to match the new flow (README, manual, in-app
  “How to get started”).

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
