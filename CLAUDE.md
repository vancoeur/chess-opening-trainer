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
  Aktuell ~371 Tests, müssen grün bleiben.
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
  `position_training.py`, `opening_id.py` (Eröffnungs-Erkennung), `tree_sync.py`.
- **Oberfläche/Design (modernisiert 2026-06-26):** EIN Stylesheet via
  `build_style(UI_THEMES[...])` in `main_window.py` — **Hell/Dunkel** (Akzent Indigo,
  Ansicht→Erscheinungsbild, QSettings `ui_theme`), feste **Navigations-Seitenleiste** links
  (`_build_sidebar`/`_nav_buttons`, aktive Seite via `_update_nav_active`) statt „Gehe zu"-Menü;
  Startseite = Dashboard (`_build_home_page`). Schrift: Serifen-Titel + Avenir-Body
  (`FONT_SERIF`/`FONT_SANS`); App-Standardschrift in `__init__` früh setzen, sonst schneiden
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
- **Release** (eigener Schritt, nur auf Achims Wunsch): `APP_VERSION` in
  `qt_app/main_window.py` bumpen + `CHANGELOG.md` ergänzen + `gh release create vX.Y …`.
  **Bei sichtbaren Änderungen IMMER Bilder + Handbuch mitziehen** (Achims Regel): README-Shots
  `docs/ui-*.png` / `docs/tour-*.gif`, Handbuch via `tools/render_manual_shots.py` +
  `tools/make_manual_pdf.py`. Vollständige Checkliste im Memory [[opening-trainer-release-prozess]].

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
Der detaillierte Projektstand + nächste Schritte stehen im Auto-Memory
(`opening-trainer-repertoire-training.md`) — vor Arbeitsbeginn lesen.
