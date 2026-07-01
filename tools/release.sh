#!/usr/bin/env bash
# ============================================================================
#  Opening Trainer — Release mit HARTEN TOREN.
#
#  Der EINZIGE erlaubte Weg, ein GitHub-Release zu veröffentlichen. Jedes Tor
#  bricht bei Fehler ab (set -e). So kann ein Release strukturell NICHT mehr
#  ohne Tests, ohne aktualisierte Version/CHANGELOG, ohne aktualisierte Doku
#  und vor allem NICHT mit kaputter Code-Signatur veröffentlicht werden.
#
#  Aufruf:
#    ./tools/release.sh              # ALLES prüfen + bauen + Signatur/ZIP
#                                    #   verifizieren — aber NICHT veröffentlichen
#    ./tools/release.sh --publish    # zusätzlich: deployen, GitHub-Release,
#                                    #   Upload, und Asset nach dem Upload prüfen
#    ./tools/release.sh --docs-ok    # bestätigt: dieses Release hat KEINE
#                                    #   sichtbaren Änderungen -> Doku-Tor überspringen
#  (Flags kombinierbar.)
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."
REPO="vancoeur/chess-opening-trainer"
APP="dist/Opening Trainer.app"
ZIP="dist/Opening Trainer.app.zip"

PUBLISH=0; DOCS_OK=0
for a in "$@"; do
  case "$a" in
    --publish) PUBLISH=1 ;;
    --docs-ok) DOCS_OK=1 ;;
    *) echo "Unbekanntes Flag: $a"; exit 2 ;;
  esac
done

step() { printf '\n\033[1m▶ %s\033[0m\n' "$1"; }
ok()   { printf '   \033[32m✓ %s\033[0m\n' "$1"; }
abort(){ printf '\n\033[31m✗ ABBRUCH: %s\033[0m\n' "$1" >&2; exit 1; }

# ---------------------------------------------------------------------------
step "Tor 1 — sauberer Git-Zustand"
[ -z "$(git status --porcelain)" ] || abort "Uncommittete Änderungen. Erst committen (Release baut aus dem committeten Stand)."
branch="$(git rev-parse --abbrev-ref HEAD)"
[ "$branch" = "main" ] || echo "   ⚠ nicht auf main (aktuell: $branch) — fortfahren, falls gewollt."
ok "Arbeitsbaum sauber"

# ---------------------------------------------------------------------------
step "Tor 2 — Version & CHANGELOG stimmen überein"
VERSION="$(grep -E '^APP_VERSION = ' qt_app/main_window.py | head -1 | sed -E 's/.*"([^"]+)".*/\1/')"
[ -n "$VERSION" ] || abort "APP_VERSION nicht gefunden in qt_app/main_window.py"
CL_TOP="$(grep -m1 -E '^## \[' CHANGELOG.md | sed -E 's/^## \[([^]]+)\].*/\1/')"
[ "$CL_TOP" = "$VERSION" ] || abort "CHANGELOG-Kopf ist [$CL_TOP], aber APP_VERSION ist $VERSION. Bitte CHANGELOG-Eintrag für $VERSION ganz oben ergänzen."
ok "Version $VERSION == oberster CHANGELOG-Eintrag"
if [ "$PUBLISH" = 1 ]; then
  if gh release view "v$VERSION" -R "$REPO" >/dev/null 2>&1; then
    abort "Release v$VERSION existiert schon. APP_VERSION bumpen (kein versehentliches Überschreiben)."
  fi
  ok "v$VERSION ist noch nicht veröffentlicht"
fi

# ---------------------------------------------------------------------------
step "Tor 3 — volle Testsuite"
QT_QPA_PLATFORM=offscreen python3 -m pytest -q -p no:cacheprovider >/tmp/ot_release_tests.log 2>&1 \
  || { tail -20 /tmp/ot_release_tests.log; abort "Tests rot — kein Release."; }
ok "$(grep -Eo '[0-9]+ passed' /tmp/ot_release_tests.log | tail -1) — grün"

# ---------------------------------------------------------------------------
step "Tor 4 — Doku aktuell (README + Handbuch)"
# Das Handbuch-PDF ist NICHT deterministisch (Zeitstempel) -> nicht neu bauen und
# per Hash prüfen, sondern per Git-Historie: wurde die Quelle .md NACH dem PDF
# committet, ist das PDF veraltet.
md_ct="$(git log -1 --format=%ct -- docs/Bedienungshandbuch.md 2>/dev/null || echo 0)"
pdf_ct="$(git log -1 --format=%ct -- docs/Bedienungshandbuch.pdf 2>/dev/null || echo 0)"
[ "$pdf_ct" != 0 ] || abort "docs/Bedienungshandbuch.pdf ist nicht eingecheckt."
[ "$md_ct" -le "$pdf_ct" ] \
  || abort "Handbuch veraltet: Bedienungshandbuch.md wurde nach dem PDF geändert. Neu bauen ('tools/make_manual_pdf.py') und mit-committen."
ok "Handbuch-PDF ist so aktuell wie die Quelle"
if [ "$DOCS_OK" = 1 ]; then
  echo "   ⚠ --docs-ok gesetzt: Doku-Änderungs-Prüfung übersprungen (Release ohne sichtbare Änderung)."
else
  git fetch --tags -q "$REPO" 2>/dev/null || git fetch --tags -q 2>/dev/null || true
  PREV="$(gh release list -L 1 -R "$REPO" --json tagName -q '.[0].tagName' 2>/dev/null || true)"
  if [ -n "$PREV" ] && git rev-parse "$PREV" >/dev/null 2>&1; then
    CHANGED="$(git diff --name-only "$PREV"..HEAD -- README.md README.de.md docs/ 2>/dev/null || true)"
    [ -n "$CHANGED" ] || abort "Seit $PREV wurden README/Handbuch NICHT geändert. Bei sichtbaren Änderungen README+Handbuch nachziehen; sonst mit --docs-ok bestätigen."
    ok "README/Handbuch seit $PREV aktualisiert"
  else
    echo "   ⚠ Vorheriges Tag nicht auflösbar — Doku-Diff nicht prüfbar. Bitte manuell sicherstellen, dass README+Handbuch stimmen."
  fi
fi

# ---------------------------------------------------------------------------
step "Tor 5 — App bauen + ad-hoc signieren"
./build_app.sh >/tmp/ot_release_build.log 2>&1 || { tail -20 /tmp/ot_release_build.log; abort "Build fehlgeschlagen."; }
PLIST_VER="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$APP/Contents/Info.plist" 2>/dev/null || true)"
[ "$PLIST_VER" = "$VERSION" ] || abort "Version im Paket ($PLIST_VER) != $VERSION."
ok "Gebaut, Version im Paket: $PLIST_VER"

# ---------------------------------------------------------------------------
step "Tor 6 — Code-Signatur des Bundles GÜLTIG"
codesign --verify --deep --strict "$APP" 2>/dev/null || abort "Signatur ungültig (das war der 'beschädigt'-Bug!). build_app.sh muss nach dem Plist-Stempeln neu signieren."
ok "codesign --verify: gültig"

# ---------------------------------------------------------------------------
step "Tor 7 — ZIP schnüren und ENTPACKT erneut verifizieren (End-to-End)"
rm -f "$ZIP"
( cd dist && ditto -c -k --sequesterRsrc --keepParent "Opening Trainer.app" "Opening Trainer.app.zip" )
TMP="$(mktemp -d)"; ditto -x -k "$ZIP" "$TMP/x"
UAPP="$(find "$TMP/x" -maxdepth 1 -name '*.app' | head -1)"
codesign --verify --deep --strict "$UAPP" 2>/dev/null || { rm -rf "$TMP"; abort "Signatur im ZIP ungültig — Nutzer bekämen 'beschädigt'. Release gestoppt."; }
rm -rf "$TMP"
ok "ZIP entpackt + Signatur gültig ($(du -h "$ZIP" | cut -f1))"

# ---------------------------------------------------------------------------
if [ "$PUBLISH" != 1 ]; then
  printf '\n\033[1;32mAlle Tore grün.\033[0m Zum Veröffentlichen:  ./tools/release.sh --publish\n'
  exit 0
fi

# ---------------------------------------------------------------------------
step "Tor 8 — lokal deployen (/Applications)"
rm -rf "/Applications/Opening Trainer.app"
cp -R "$APP" /Applications/
ok "nach /Applications kopiert"

# ---------------------------------------------------------------------------
step "Tor 9 — Release-Notes aus CHANGELOG + Install-Notiz erzeugen"
NOTES="$(mktemp)"
awk -v ver="[$VERSION]" '
  $0 ~ /^## \[/ { if (seen) exit; if (index($0, ver)) { seen=1; next } }
  seen { print }
' CHANGELOG.md > "$NOTES"
[ -s "$NOTES" ] || abort "Konnte CHANGELOG-Abschnitt für $VERSION nicht extrahieren."
cat docs/release_install_note.md >> "$NOTES"
ok "Notes erzeugt"

# ---------------------------------------------------------------------------
step "Tor 10 — GitHub-Release anlegen + Asset hochladen"
gh release create "v$VERSION" "$ZIP" -R "$REPO" \
  --title "Opening Trainer $VERSION" --notes-file "$NOTES" >/dev/null
ok "v$VERSION veröffentlicht"

# ---------------------------------------------------------------------------
step "Tor 11 — Veröffentlichtes Asset ZURÜCKLADEN und Signatur prüfen"
VTMP="$(mktemp -d)"; ( cd "$VTMP" && gh release download "v$VERSION" -R "$REPO" -p "*.zip" >/dev/null 2>&1 )
VZ="$(find "$VTMP" -maxdepth 1 -name '*.zip' | head -1)"
[ -n "$VZ" ] || { rm -rf "$VTMP"; abort "Konnte veröffentlichtes Asset nicht zurückladen."; }
ditto -x -k "$VZ" "$VTMP/x"
VAPP="$(find "$VTMP/x" -maxdepth 1 -name '*.app' | head -1)"
if codesign --verify --deep --strict "$VAPP" 2>/dev/null; then
  ok "Live-Asset auf GitHub: Signatur gültig"
else
  rm -rf "$VTMP"; abort "Das VERÖFFENTLICHTE Asset hat eine ungültige Signatur! Sofort Asset ersetzen."
fi
rm -rf "$VTMP" "$NOTES"

printf '\n\033[1;32m✓ Release v%s ist live und verifiziert:\033[0m https://github.com/%s/releases/tag/v%s\n' "$VERSION" "$REPO" "$VERSION"
