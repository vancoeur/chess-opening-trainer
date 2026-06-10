# Konzeptskizze: Spaced Repetition („Was ist heute fällig?")

Stand: 2026-06-03. Klärt das Vorgehen, bevor gebaut wird. Ziel: Der Trainer
sagt dir, **welche Linien heute zur Wiederholung anstehen**, und terminiert sie
nach deiner Leistung neu — so wiederholst du kurz bevor du vergisst.

## 1. Die prägende Entscheidung: Was ist eine „Karte"?

**Option A — Karte = ganze Variante (Linie).**  Empfohlen für den Start.
- Eine Linie = eine Karte (Schlüssel: Quelle + Variantenname, wie bei der Statistik).
- Wiederholen = die Linie einmal durchspielen.  Bewertung: fehlerfrei durch → *bestanden*; ein Fehler → *nicht bestanden*.
- Wenige Karten (= Anzahl Varianten), einfaches Datenmodell, **dockt direkt an
  das vorhandene Set-Training (`TrainingRun`) an** — das spielt schon eine
  Linienliste der Reihe nach durch und merkt pro Linie „fehlerfrei/mit Fehler".
- Schwäche: Eine 20-Züge-Linie wird auch dann ganz neu terminiert, wenn nur ein
  Zug saß nicht. Für Eröffnungslinien akzeptabel — und die **Fehlzug-Sitzung**
  deckt die Zug-Ebene bereits ab.

**Option B — Karte = einzelne Stellung/Zug (wie Chessable).**
- Sehr gezielt (genau die schwachen Stellen), aber **viele** Karten, komplexes
  Datenmodell (Schlüssel über Stellung/Transpositionen), eigener Drill-Ablauf.

**Empfehlung:** Mit **A** starten. A + die bestehende Fehlzug-Sitzung decken Linien-
und Zug-Ebene zusammen gut ab. B bleibt als spätere Verfeinerung offen.

## 2. Datenmodell (Option A)

Neue Datei `data/schedule.json`. Pro Karte (Quelle + Variantenname):
- `interval_days` — aktuelles Intervall
- `ease` — Leichtigkeitsfaktor (Start 2.5)
- `due` — Fälligkeitsdatum (ISO)
- `reps` — Anzahl erfolgreicher Wiederholungen in Folge
- `last_reviewed`

Linie ohne Eintrag = **neu** (noch nie terminiert).

## 3. Algorithmus (SM-2, vereinfacht auf bestanden/nicht bestanden)

Bewertung pro Linie ergibt sich automatisch aus dem Training (Linie fehlerfrei?):
- **bestanden:** reps 0→Intervall 1 Tag; reps 1→3 Tage; danach `Intervall × ease`
  (aufgerundet). `due = heute + Intervall`, `reps += 1`.
- **nicht bestanden:** `reps = 0`, `Intervall = 0` (heute/morgen wieder fällig),
  `ease = max(1.3, ease − 0.2)`.

(Volles SM-2 nutzt Noten 0–5; für Eröffnungen reicht bestanden/nicht — eine
4-stufige Anki-artige Bewertung bleibt als spätere Option.)

Die reine Logik bekommt `heute` als Parameter übergeben (kein verstecktes
Datum) — testbar und im Stil des Projekts.

## 4. Ablauf

1. **„Heute fällig: N"** — Karten mit `due ≤ heute`, plus eine begrenzte Zahl
   **neuer** Linien pro Tag (z. B. max. 10), damit es nicht überrollt.
2. **„Wiederholung starten"** — baut die Warteschlange der fälligen Linien und
   spielt sie über einen `TrainingRun` der Reihe nach durch.
3. Nach jeder Linie: bestanden/nicht bestanden → Karte neu terminieren, speichern.

## 5. Andocken an Vorhandenes

- **`TrainingRun`** (bereits getestet) läuft die fällige Linienliste ab und
  liefert pro Linie „fehlerfrei/mit Fehler" — genau die Bewertung.
- Kartenschlüssel = (Quelle, Variantenname) — **identisch zur Statistik**, daher
  später leicht eine Spalte „Fällig" in der Variantentabelle.
- Farbe/Brett/Drill bleiben unverändert.

## 6. Bauplan (klein, testfirst, jederzeit lauffähig)

1. **`scheduler.py`** (rein): `Card`, `new_card()`, `is_due(card, today)`,
   `review(card, passed, today) -> Card`. Voll unit-getestet (Intervall-Wachstum,
   Rückfall bei Fehler, Ease-Grenze).
2. **`schedule_store.py`**: JSON laden/speichern, fehlende Datei = leer,
   beschädigt = leer (wie die anderen Stores).
3. **Warteschlange:** reine Funktion `due_cards(lines, schedule, today, new_limit)`
   → geordnete Linienliste. Getestet.
4. **UI-Andockung:** „Heute fällig: N" + „Wiederholung starten" (nutzt
   `TrainingRun`); nach jeder Linie `review()` + speichern.
5. **Optional:** Spalte „Fällig" in der Variantentabelle.

## 7. Bewusst NICHT jetzt (Scope-Schutz)

- Karten auf Zug-Ebene (Option B).
- Mehrstufige Bewertung (Anki-4-Knöpfe).
- Prognose-/Verlaufsgrafiken zur Fälligkeit.
- Einstellbare Algorithmus-Parameter in der UI.

Datenmodell und Trainingslogik bleiben unangetastet; SR ist eine **zusätzliche
Schicht** über den vorhandenen Linien.
