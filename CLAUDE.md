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
  Aktuell ~363 Tests, müssen grün bleiben.
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
- **Cutover Teil A erledigt (2026-06-25):** die schlafende lineare Seite-0-Trainings-
  + Eval-Leisten-Maschinerie ist **gelöscht** (`_build_train_page` ist nur noch ein Stub).
  `self.lines` **bleibt bewusst** als **Bibliotheks-Katalog** (Bibliothek/Statistik/Prüfung
  lesen noch daraus). Teil B (`self.lines` ganz eliminieren) ist offen + riskant — nur auf
  Achims ausdrücklichen Wunsch in eigener Session. Nicht versehentlich reaktivieren.
- Reine, getestete Helfer in `opening_trainer/tree_session.py`, `position_book.py`,
  `position_training.py`, `opening_id.py` (Eröffnungs-Erkennung), `tree_sync.py`.
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
