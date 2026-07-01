# Release-Checkliste (Opening Trainer)

**Regel: Ein Release entsteht NUR über `./tools/release.sh`.** Das Skript erzwingt
alle Tore unten und bricht ab, wenn eins fehlt. So kann kein Release ohne Tests,
ohne aktualisierte Version/CHANGELOG/Doku und vor allem **nicht mit kaputter
Signatur** („beschädigt") veröffentlicht werden.

## Vorbereiten (von Hand, dann committen)

1. **Code fertig**, volle Suite grün (`QT_QPA_PLATFORM=offscreen python3 -m pytest -q`).
2. **`APP_VERSION`** in `qt_app/main_window.py` bumpen (Semver: PATCH=Fixes,
   MINOR=neue Funktionen, MAJOR=Bruch).
3. **`CHANGELOG.md`**: neuer Abschnitt `## [x.y.z] — JJJJ-MM-TT` ganz oben, in
   Englisch, erklärt WAS dazukam/erweitert wurde; Link-Referenz unten ergänzen.
4. **Bei sichtbaren Änderungen (Aussehen/Bedienung) — PFLICHT:**
   - **README.md + README.de.md**: Feature-Liste, Screenshots-Bezug, Texte aktualisieren.
   - **Screenshots**: `tools/render_manual_shots.py` (Handbuch) + eigenes /tmp-Skript
     für `docs/screen-de.png`/`screen-en.png`. **ACHTUNG:** diese Skripte schreiben
     in die ECHTEN QSettings (Sprache/Theme) → vorher sichern, nachher auf
     `en`/`light`/`green` zurücksetzen.
   - **Handbuch**: `docs/Bedienungshandbuch.md` inhaltlich nachziehen, dann
     **PDF neu bauen**: `QT_QPA_PLATFORM=offscreen PYTHONPATH=. python3 tools/make_manual_pdf.py`
     — und `.md` + `.pdf` **zusammen** committen (sonst schlägt Tor 4 an).
   - **Demo-GIFs** (`docs/tour-*.gif`) haben KEINEN Generator (imageio fehlt) — bei
     sichtbaren Änderungen entweder entfernen oder separat neu erstellen.
5. **Alles committen** (Arbeitsbaum muss sauber sein) und pushen.

## Veröffentlichen

```bash
./tools/release.sh            # prüft + baut + verifiziert, OHNE zu veröffentlichen
./tools/release.sh --publish  # zusätzlich: deploy, GitHub-Release, Upload, Nachprüfung
```

Sonderfall „Release ohne sichtbare Änderung" (reiner Bugfix): `--docs-ok` anhängen,
um das Doku-Änderungs-Tor bewusst zu überspringen.

## Die Tore des Skripts (alle müssen grün sein)

| # | Tor | Bricht ab, wenn … |
|---|-----|-------------------|
| 1 | sauberer Git-Zustand | uncommittete Änderungen |
| 2 | Version == CHANGELOG-Kopf | `APP_VERSION` ≠ oberster CHANGELOG-Eintrag; (bei `--publish`) Tag existiert schon |
| 3 | volle Testsuite | Tests rot |
| 4 | Doku aktuell | Handbuch-`.md` neuer als PDF; oder README/Handbuch seit letztem Release unverändert (ohne `--docs-ok`) |
| 5 | Build + ad-hoc-Signatur | Build scheitert; Version im Paket ≠ `APP_VERSION` |
| 6 | **Signatur gültig** | `codesign --verify` schlägt fehl (der „beschädigt"-Bug) |
| 7 | **ZIP end-to-end** | Signatur im entpackten ZIP ungültig |
| 8–11 (`--publish`) | Deploy, Release, Upload, **Asset zurückladen + prüfen** | Upload/Signatur des LIVE-Assets fehlerhaft |

## Warum es diese Tore gibt

- **v1.1.0–v1.4.0** wurden mit **kaputter Signatur** ausgeliefert (Info.plist nach
  dem Signieren geändert → „beschädigt", Rechtsklick→Öffnen half nicht). Tore 6/7/11
  fangen das jetzt strukturell.
- README/Handbuch wurden bei Releases **unvollständig** nachgezogen. Tor 4 erzwingt
  die Aktualisierung.

## Zweites, unabhängiges Netz (Cloud)

Zusätzlich zum lokalen Skript prüft eine **GitHub-Action** (`.github/workflows/
verify-release.yml`) bei **jedem veröffentlichten Release** das tatsächlich
hochgeladene Asset auf einem **sauberen macOS-Runner**: laden → entpacken →
`codesign --verify`. Ungültige Signatur = **roter Lauf** am Release, unabhängig von
der Maschine, die es gebaut hat. Manuell für ein beliebiges Tag auslösbar
(Actions → *Verify release asset* → *Run workflow*). Die Testsuite läuft ohnehin in
`.github/workflows/tests.yml` bei jedem Push.

Die App ist unsigniert/ad-hoc (nicht notarisiert) → Endnutzer entfernen beim ersten
Start die Quarantäne (`xattr -dr com.apple.quarantine <app>`); steht in den
Release-Notes (`docs/release_install_note.md`) und beiden READMEs. Einziger Weg
ganz ohne Warnung: Apple-Notarisierung.
