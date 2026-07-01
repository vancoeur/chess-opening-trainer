# OpeningTrainer — Projekt-Anweisungen für Claude

Persönlicher Schach-Eröffnungstrainer (macOS). Achim ist Nutzer/Auftraggeber,
kein Programmierer — er denkt in Schach- und Bedien-Begriffen, nicht in Code.

## Stack
- **Python 3** · **PySide6** (Qt) · **python-chess** · **Stockfish** (im App-Bundle).
- Reine Fachlogik in `opening_trainer/`, Qt-Oberfläche in `qt_app/` (Hauptdatei:
  `qt_app/main_window.py`, eine `QStackedWidget` mit Seiten 0–13).
- Einstiegspunkt: `qt_main.py`.

## Schnell iterieren — NICHT bei jeder Änderung das Bundle bauen
- **Tests (Sekunden, immer zuerst):**
  `QT_QPA_PLATFORM=offscreen python3 -m pytest -q`
  (bei Hängern in der Hintergrund-Shell hilft `-p no:cacheprovider`).
  Aktuell ~423 Tests, müssen grün bleiben.
- **App aus dem Quellcode starten (Sekunden, zum Ausprobieren):**
  `python3 qt_main.py`
- **Bundle bauen + deployen (Minuten — NUR wenn Achim es real testen/„rausgeben"
  will, am Ende eines Schwungs):**
  `./build_app.sh` → `rm -rf "/Applications/Opening Trainer.app" && cp -R "dist/Opening Trainer.app" /Applications/`
  Danach muss Achim die App **⌘Q** + neu öffnen.

## Architektur-Kern (Stand 2026-06)
- **Positionsmodell ist primär** (Chessable-Stil): Repertoire = `RepertoireTree`-Bäume
  (`tree_store`, `repertoire_trees.json`); Training/Statistik/Auswertung/Prüfung laufen
  über Stellungen (EPD-Schlüssel), nicht über lineare Linien.
- **Cutover KOMPLETT (Teil A 2026-06-25, Teil B 2026-06-27):** die alte lineare
  Maschinerie ist ganz weg. `self.lines` ist **eliminiert** — die Eröffnungs-Liste
  (Bibliothek/Seiten-Zuordnung/Meldungen) leitet sich jetzt aus den Bäumen ab via
  `opening_trainer/catalog.py` (`build_catalog`→`CatalogEntry`, ein Eintrag je Auto-Baum)
  über die Methode `_catalog()`. Bäume = einzige Quelle. `_load_lines()` lebt nur noch als
  Einmal-Parser für `run_migration`. **`opening_sides` bleibt** (per-Eröffnung-Seitenspeicher,
  speist die `dominant_side` des Tree-Syncs UND die Bibliotheks-Anzeige via `_side_of_line`).
  Partien-Auswertung nutzte schon die Bäume (`build_san_book`).
- Reine, getestete Helfer in `opening_trainer/tree_session.py`, `position_book.py`,
  `position_training.py`, `opening_id.py` (Eröffnungs-Erkennung), `tree_sync.py`,
  `comments.py` (Kommentar-/Kapitelnamen säubern).
- **Repertoire-Baum-Seite (Index 13) = namens-orientierte Übersicht (Stand v1.4.1):**
  flaches QListWidget ist durch ein **aufklappbares QTreeWidget** ersetzt, gruppiert nach
  **ECO-Eröffnungsnamen**. `tree_session.variation_outline(trees, side, misc_label, strip_family)`
  benennt jedes Kapitel über die ersten ~20 Halbzüge via `opening_id.opening_name_for_grouping`
  (= `identify_opening_name` + Eindeutigkeits-/Transpositions-Check gegen `identify_opening`-Familie).
  ECO hat Vorrang; nur wenn der ECO-Name nicht zur Familie passt (Transposition, z. B. London→„Old
  Benoni") oder nur die nackte Familie liefert → Rückfall auf den **gesäuberten PGN-Kapitelnamen**
  (`comments.clean_chapter_name`). Lehrmaterial (`is_instructional`) in EINE „Lehrmaterial"-Gruppe.
  Namen werden LIVE bei jedem Öffnen neu berechnet (kein Cache).
- **ECO-Datenbank:** `opening_trainer/data/eco_openings.tsv` (3 Spalten: eco⇥name⇥uci, ~3733
  Einträge, eingecheckt + via `.spec`/`build_app.sh` ins Bundle gepackt). Neu erzeugen mit
  `tools/build_eco_data.py` (lädt lichess-org/chess-openings, behält die Namen).
- **Übe-Modi:** Tagessitzung „Heute fällig" (Spaced Repetition, SM-2), **Schwächen-Radar**
  (offene Fehler, Dashboard-Kachel, `WEAK_SESSION_LIMIT`), **Blitz** (60-Sek-Sprint `BLITZ_SECONDS`,
  eigener `_blitz`-Modus, rührt Lernplan/Statistik NICHT an), Einzel-/Variantendrill.
- **Oberfläche/Design (Stand v1.4.1):** EIN Stylesheet via `build_style(UI_THEMES[...])` in
  `main_window.py` — **Hell/Dunkel** (Akzent **Blau (hell)/Grün (dunkel)**, Ansicht→Erscheinungsbild,
  QSettings `ui_theme`), feste **Navigations-Seitenleiste** links (`_build_sidebar`/`_nav_buttons`,
  aktive Seite via `_update_nav_active`, Bereichs-Überschriften in Akzentfarbe) statt „Gehe zu"-Menü;
  Startseite = Dashboard (`_build_home_page`). Schrift durchgängig **Lucida Grande**
  (`FONT_SANS`==`FONT_SERIF`); App-Standardschrift in `__init__` früh setzen, sonst schneiden
  Listen Unterlängen ab. Selbstgemalte Balken via `board_view.set_ui_palette`.
  **ACHTUNG: Offscreen-Render-/Vorschau-Skripte schreiben über `_set_ui_theme`/`_set_language` in
  die ECHTEN QSettings (nur `data_dir` ist monkeypatchbar) — danach `ui_theme`/`board_theme`/
  `language` zurücksetzen, sonst startet Achims App falsch.**
- Daten der echten App: `~/Library/Application Support/Opening Trainer/`. In Tests
  per `monkeypatch.setattr(mw, "data_dir", lambda: tmp)` umbiegen (nie die echten
  Daten beschreiben; für Read-only-Checks eine Kopie verwenden).

## Konventionen
- **Bauweise:** reine Logik (testbar, kein Qt) → Tests → UI verdrahten → Offscreen-Render
  als Beleg → volle Suite grün → committen. Pro Feature ein Commit.
- **Zweisprachig:** jeder UI-Text via `t("deutsch", "english")`. Im DE-Modus Schach-Notation
  germanisieren (N→S, B→L, R→T, Q→D).
- **Commits auf Englisch**, am Ende `Co-Authored-By: Claude <noreply@anthropic.com>`.
  Direkt auf `main`, dann `git push` (Achims Workflow; nicht branchen, außer er sagt es).
- **Release — NUR über `./tools/release.sh`** (eigener Schritt, nur auf Achims Wunsch).
  Das Skript hat **harte Tore** und bricht ab, wenn etwas fehlt — nie von Hand `gh release
  create` aufrufen. Ablauf: `APP_VERSION` bumpen + `CHANGELOG.md`-Eintrag ganz oben + bei
  **sichtbaren Änderungen IMMER README (DE+EN) + Handbuch mitziehen** (Screenshots
  `docs/screen-*.png` eigenes /tmp-Skript, `tools/render_manual_shots.py`; Handbuch-Text +
  PDF via `tools/make_manual_pdf.py`, `.md`+`.pdf` zusammen committen). **Render-Skripte
  schreiben in die ECHTEN QSettings (Sprache/Theme) → vorher sichern, nachher auf
  `en`/`light`/`green` zurücksetzen.** **Demo-GIFs `docs/tour-*.gif` haben KEINEN Generator
  (imageio fehlt).** Dann `./tools/release.sh` (validiert+baut+verifiziert, ohne zu
  veröffentlichen) → `./tools/release.sh --publish` (deploy+Release+Upload+Nachprüfung des
  Live-Assets). Tore u. a.: Version==CHANGELOG, Tests grün, Doku aktualisiert, **`codesign
  --verify` gültig** + **ZIP entpackt erneut verifiziert** (fängt den „beschädigt"-Bug:
  build_app.sh signiert nach dem Plist-Stempeln neu). Checkliste: `docs/RELEASE_CHECKLIST.md`
  + Memory [[opening-trainer-release-prozess]].

## Arbeitsweise mit Achim (wichtig)
- **Schritte einzeln quittieren** bei riskanter Arbeit: Diagnose → Vorschlag → sein OK →
  Änderung; Build/Deploy/Commit getrennt. Bei klar umrissenen Aufgaben darf ich einen
  Schwung autonom abarbeiten (mit Tests).
- **Alles auf Deutsch erklären, in Alltags-/Schachsprache**, kein Fachjargon. Sichtbar
  machen statt erklären.
- **Ehrlich bleiben**, was das Tool NICHT kann (z. B. Eröffnungs-Tiefe/Begründungen
  entstehen nur aus Achims eigenen Daten/Notizen, nicht „aus dem Nichts").
- Achim denkt in **benannten Repertoires** (gegen Sizilianisch, Caro-Kann, Grünfeld …),
  nicht in „Weiß/Schwarz". Funktionen daran ausrichten.
- Längere Texte/Beiträge als **Datei** liefern (Kopieren aus dem Chat ist für ihn hakelig).

## Fortlaufender Stand
Zuletzt veröffentlicht: **v1.4.1** (2026-06-29). Der detaillierte Projektstand +
nächste Schritte stehen im Auto-Memory (`opening-trainer-repertoire-training.md`)
— vor Arbeitsbeginn lesen.
