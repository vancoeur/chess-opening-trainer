# Opening Trainer — Bedienungshandbuch

Stand: Juni 2026. Persönlicher Schach-Eröffnungstrainer für macOS.

Dieses Handbuch erklärt jede Funktion in Alltags- und Schachsprache — kein
Fachjargon. Du brauchst keine Vorkenntnisse außer Schach.

---

## 1. Was die App für dich tut

Du übst deine **Eröffnungen Stellung für Stellung** (wie bei Chessable/Anki): Die
App zeigt dir ein Brett, du spielst den Zug, der in *deinem* Repertoire vorgesehen
ist — und ein **Lernplan** sorgt dafür, dass du Stellungen, die du vergisst, öfter
wiederholst und sichere seltener. Zusätzlich kann **Stockfish** prüfen, ob deine
Varianten objektiv gut sind, und deine **echten Partien** mit deinem Repertoire
vergleichen.

Dein Repertoire bringst du als **PGN-Datei(en)** mit. Die App macht daraus
verzweigte **Bäume** und besitzt sie dann selbst (Speichern/Üben/Bearbeiten).

---

## 2. Erste Schritte — Repertoire laden

1. Menü **Datei → PGN laden …** (⌘O) für eine Datei, oder **Ordner laden …**
   (⇧⌘O) für einen ganzen Ordner mit PGNs.
2. Die App fragt: **„Welche Farbe spielst du in dieser Datei?"** (Weiß/Schwarz/
   Überspringen). Wähle die Farbe, in der du dieses Repertoire spielst. (Bei
   Ordnern errät die App die Farbe oft aus dem Dateinamen, z. B. „Weiss…".)
3. Danach erscheint ein kurzer **Baum-Bericht**, z. B. *„Schwarz: 23 Linien → 1
   Baum mit 15 Verzweigungen"* — so siehst du sofort, ob deine Datei einen echten
   verzweigten Baum ergibt. Ein Knopf **„Im Repertoire-Baum ansehen"** bringt dich
   direkt dorthin.

Geladene Repertoires **bleiben beim Neustart erhalten** — du musst nichts erneut
laden. Mehrere Dateien/Ordner werden zusammengeführt.

Wenn du noch keine eigene PGN hast: Auf der **Startseite** gibt es einen Knopf
**„Beispiel-Eröffnungen ausprobieren"**.

---

## 3. Orientierung — wo bin ich?

- **Kopfzeile** (graue Leiste oben) und der **Fenstertitel** zeigen immer den Namen
  der aktuellen Seite (z. B. „Repertoire-Baum", „Heute fällig").
- Die **Startseite** (Menü **Gehe zu → Start**, ⌘1) ist der Verteiler: oben der
  große Knopf **„Heute fällig üben"** mit Vorschau, darunter Kacheln in vier Spalten:
  - **Üben:** Heute fällig · Bäume üben · Repertoire-Prüfung
  - **Repertoire:** Repertoire-Baum · Alle Eröffnungen · Repertoire-Editor
  - **Auswerten:** Fortschritt · Trefferquote & Fehler · Partien auswerten
  - **Erkunden:** Eröffnungs-Explorer · Gegen Stockfish
- Mit **„‹ Zurück"** (oben links auf den Unterseiten) kommst du zur vorigen Seite.
- **Ansicht-Menü:** Brettfarbe (Grün/Holz/Blau/Grau), Sprache (Deutsch/English,
  sofort umschaltbar), Bewertungs-Leiste ein/aus.

---

## 4. Das tägliche Üben — „Heute fällig"

Das ist der Kern. Einstieg: großer Knopf **„Heute fällig üben"** auf der Startseite,
oder Menü **Gehe zu → Heute fällig** (⌘D).

1. Du landest in der **Übersicht „Heute fällig"**: oben eine Vorschau (heute/morgen/
   diese Woche/neu), darunter **pro Eröffnung** „X fällig · Y neu" mit eigenem
   „üben"-Knopf, und **„▶ Alles üben (N)"** für die ganze Tagessitzung.
2. Dann beginnt die **Übe-Ansicht** (alles auf einem Bildschirm):
   - **Brett** links — du bist am Zug.
   - **Linien-Kontext** (z. B. „1.e4 …?") — zeigt, *wo* in der Linie du bist.
   - **„Idee"** zur Stellung — falls in deiner PGN ein Kommentar hinterlegt ist.
   - **Status/Feedback** — z. B. „✓ Sitzt — nächste Wiederholung in 4 Tagen".
   - Knöpfe: **Lösung zeigen** (Taste **L**), **Überspringen** (Taste **Enter**),
     **Neu**.
3. **Spielen:** Zieh den vorgesehenen Zug auf dem Brett. Richtig → Gegnerzug kommt
   automatisch, nächste Stellung. Falsch → kurzer Hinweis, nochmal versuchen.

### Learn-Modus (neue Stellungen erst zeigen)
Häkchen **„Neue Stellungen erst zeigen (lernen)"** (standardmäßig an, nur in der
Tagessitzung):
- Eine **neue** Stellung wird dir **mit der Lösung gezeigt** (der Zug ist grün am
  Brett markiert, Text: „Der Zug hier ist …"). Du musst **nicht raten**.
- Knopf **„✓ Verstanden, weiter"** merkt sie vor und geht zur nächsten.
- Schon **gelernte** (fällige) Stellungen werden weiterhin **abgefragt**.
- Häkchen aus → auch neue Stellungen sofort abfragen.

---

## 5. Wie der Lernplan entscheidet (Spaced Repetition)

Die App entscheidet **selbst**, was heute dran ist (Anki-Prinzip) — du musst nicht
auswählen. Nach jeder richtigen Antwort wird die nächste Wiederholung weiter in die
Zukunft geschoben (1 Tag → mehrere Tage → …); bei Fehlern kommt die Stellung bald
wieder. **Gleiche Stellungen über verschiedene Zugwege (Transpositionen) zählen als
eine** — du übst sie nicht doppelt. „Neu" = noch nie geübte Stellungen; sie werden
**nach und nach** eingeführt, nicht alle auf einmal.

---

## 6. Der Repertoire-Baum (⌘R)

Menü **Gehe zu → Repertoire-Baum** (⌘R) oder Startseiten-Kachel. Hier siehst du dein
Repertoire als **einen verzweigten Baum**.

- **Zwei Auswahlfelder oben:** links die **Seite** (Weiß/Schwarz), rechts das
  **konkrete Repertoire** — „Alles" oder eine benannte Eröffnung (z. B.
  „Sizilianisch", „Caro-Kann", „Grünfeld"). Wähle eine, und der Baum zeigt **nur
  diese**.
- **Die Liste** ist der Baum: Hauptlinie flach, **Verzweigungen eingerückt** und mit
  **⎇** markiert. Am Ende jeder Linie steht ihr **Eröffnungsname** (aus der PGN oder
  von der App aus den Zügen erkannt — auch bei nichtssagenden Kapitelnamen).
- **Zeile anklicken** → das Brett zeigt die Stellung (dein Zug gelb markiert).
- **Lücken (⚠):** Eine Zeile mit **⚠** bedeutet: Die Linie endet, **du bist am Zug,
  aber es ist keine Antwort hinterlegt** — hier würdest du „aus dem Buch" fallen. Oben
  steht die Zahl der Lücken. Klick eine ⚠-Zeile an, dann **„⚠ Im Editor ergänzen"** —
  das springt genau dorthin, damit du den fehlenden Zug eintragen kannst.
- **„▶ Dieses Repertoire üben"** startet eine Übe-Sitzung genau für die gewählte
  Eröffnung; **„Diese Stellung üben"** drillt die angeklickte Einzelstellung.

---

## 7. Der Repertoire-Editor (⌘E)

Menü **Gehe zu → Repertoire-Editor** (⌘E). Hier **baust und korrigierst** du Bäume.

- Oben den Baum wählen (Combo) oder **„Neuer Baum"** (fragt die Seite).
- **Zug aufs Brett spielen** = anhängen/navigieren (gibt es den Zug schon, springst
  du dorthin; sonst wird er angehängt). So baust du Varianten: an einer Stellung
  einen zweiten eigenen Zug oder weitere Gegner-Antworten hinzufügen.
- Die **eingerückte Zugliste** rechts ist klickbar; 💬 markiert einen Kommentar.
- Knöpfe: **„Zur Hauptlinie"** (eine Variante zur Hauptlinie machen), **„Zug
  löschen"** (samt Nachfolgern), **„✏ Kommentar"**, **Seite** (Weiß/Schwarz), **„Als
  PGN exportieren"**, **„🗑 Baum löschen"**.
- Jede Änderung wird sofort gespeichert.

---

## 8. Repertoire-Prüfung (⌘6)

Menü **Gehe zu → Repertoire-Prüfung**. **Stockfish** geht **alle Varianten** deines
Repertoires durch und meldet **Patzer/Ungenauigkeiten** in *deinen* hinterlegten
Zügen („⛔ Patzer bei Zug X: du hast Y — besser Z"). So findest du schwache Stellen in
deiner Vorbereitung. Klick einen Fund an → du kannst die Variante üben/im Editor
korrigieren. (Braucht Stockfish — ist eingebaut.)

---

## 9. Partien auswerten (⌘5)

Menü **Gehe zu → Partien auswerten**.

1. Trag einmal deinen **Spielernamen** ein (Lichess/chess.com), damit die App pro
   Partie weiß, welche Farbe du hattest.
2. **PGN deiner Partien laden.** Die App vergleicht jede Partie mit deinem Repertoire
   (varianten-bewusst!) und zeigt: **abgewichen** (wo du vom Repertoire abgewichen
   bist), **Eröffnung ungedeckt**, oder **gefolgt**.
3. Klick eine Partie an → **Betrachter:** durchblättern; an der Abweichung steht „dein
   Repertoire: … — du spieltest: …". Knopf **„🔍 Mit Stockfish prüfen"** markiert
   zusätzlich deine **Patzer in dieser Partie**. **„Diese Stellung üben"** drillt die
   Abweichungs-Stelle.

---

## 10. Auswerten — Fortschritt & Trefferquote

- **Fortschritt** (⌘4): pro Eröffnung ein Status — 🟢 **sitzt** (Trefferquote ≥ 85 %),
  🟡 **wackelt**, ⚪ **neu** — mit „X von Y Stellungen geübt". Oben ein Balken über
  alles. Klick eine Eröffnung → direkt üben.
- **Trefferquote & Fehler** (⌘3): deine **Gesamt-Trefferquote** und Tendenz, plus die
  Liste der **offenen Fehlerstellungen** (zuletzt falsch). Klick eine an → gezielt
  diese Stellung üben.

---

## 11. Erkunden

- **Eröffnungs-Explorer** (Gehe zu → …): zeigt zu einer Stellung die Statistik aus der
  **Lichess**-Datenbank (welche Züge wie oft gespielt werden). Braucht einen
  **Lichess-Zugang (Token)** — die App bietet beim ersten Mal einen Ein-Klick-Link
  zum Erstellen (ohne Berechtigungen, nur zur Identifikation).
- **Gegen Stockfish** (Gehe zu → …): aus der aktuellen Stellung **weiterspielen** gegen
  die Engine — drei Stärken. Gut, um eine Eröffnung „auszuspielen".

---

## 12. Repertoires verwalten & aufräumen (Datei-Menü)

- **Geladene Repertoires verwalten …:** zeigt deine geladenen PGN-Quellen mit Anzahl;
  „Ausgewählte entfernen" lädt eine aus (die **Datei auf der Platte bleibt**).
- **Eigene Bäume verwalten/aufräumen …:** zeigt Bäume, die **zu keiner geladenen
  Datei** gehören (Reste alter Importe/Studien). Hier kannst du solche **„Geister"
  löschen**, falls deine Zahlen („Neu: …") unerwartet groß sind.
- **Repertoire leeren …:** entfernt **alle** geladenen Quellen und Bäume aus der App
  (deine PGN-Dateien bleiben). Danach kannst du sauber neu laden.

> **Tipp bei zu großen „Neu"-Zahlen:** *Repertoire leeren* → dann deinen sauberen
> Ordner/Dateien neu laden. Dann zeigt die App nur dein echtes Repertoire.

---

## 13. Tastenkürzel (Überblick)

| Kürzel | Funktion |
|---|---|
| ⌘O / ⇧⌘O | PGN-Datei / Ordner laden |
| ⌘1 | Startseite |
| ⌘2 | Alle Eröffnungen (Bibliothek) |
| ⌘3 | Trefferquote & Fehler |
| ⌘4 | Fortschritt |
| ⌘5 | Partien auswerten |
| ⌘6 | Repertoire-Prüfung |
| ⌘R | Repertoire-Baum |
| ⌘E | Repertoire-Editor |
| ⌘D | Heute fällig |
| ⌘T | Baum frei durchspielen |
| L / Enter | (beim Üben) Lösung zeigen / Überspringen |

---

## 14. Ehrlich: was die App (noch) nicht kann

- Sie erfindet **keine Eröffnungs-Theorie**. Tiefe und Varianten kommen aus **deinen**
  PGNs (oder aus dem, was du im Editor ergänzt). Lade variantenreiche PGNs oder baue
  Äste selbst, wenn du mehr Tiefe willst.
- **Erklärungen/„Ideen"** zu Zügen sind nur so reichhaltig wie **deine eigenen
  Notizen** in der PGN. Dafür kann **Stockfish** dir objektiv sagen, ob ein Zug gut war.
- Die App läuft **lokal auf deinem Mac**, ohne Konto und Cloud.

---

*Bei Fragen oder Wünschen: Hilfe-Menü → „Erste Schritte" / „Projektseite öffnen".*
