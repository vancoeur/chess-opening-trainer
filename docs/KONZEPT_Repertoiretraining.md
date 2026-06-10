# Konzeptnotiz: Vom Linien-Üben zum Repertoire-Training

Stand: 2026-06-01. Diese Notiz klärt das *Ziel*, bevor Code entsteht.
Sie ist die Richtschnur für die nächsten Schritte; sie ersetzt keine
bestehende Funktion, sondern ordnet sie ein.

## 1. Was der Nutzer erreichen will

Sinngemäß aus seinen eigenen Worten:

- Eröffnungen trainieren und dabei **sichtbar besser werden**.
- **Fehlzüge** angezeigt bekommen und **so oft wiederholen**, wie er will.
- Sich **ein solides Repertoire zusammenstellen** — einmal für Weiß, einmal
  für Schwarz — und **dieses Repertoire schließlich am Stück trainieren**.
- Eine **thematische Gruppierung** (Englisch, Slawisch, Französisch …) soll
  das **Zusammenstellen** der Repertoires erleichtern.

## 2. Der Weg durchs Programm (Bedienlogik)

1. **Laden:** PGN-Datei oder -Ordner mit Eröffnungslinien.
2. **Zusammenstellen:** Linien thematisch gruppieren und in ein Repertoire
   (Weiß / Schwarz) aufnehmen.
3. **Trainieren:** entweder eine einzelne Linie *oder ein ganzes Set* der
   Reihe nach.
4. **Fortschritt sehen:** Trefferquote je Linie *und je Set/Repertoire*.
5. **Fehler drillen:** protokollierte Fehlzüge gezielt und beliebig oft
   wiederholen.

## 3. Begriffe — zwei Ebenen

- **Variante / Linie:** eine konkrete Zugfolge aus der PGN (existiert).
- **Thematische Gruppe:** eine benannte Menge von Varianten (Englisch,
  Slawisch, Französisch …). Eine Variante kann in **mehreren** Gruppen sein
  (existiert bereits, Mehrfach-Haken).
- **Repertoire:** es gibt genau zwei — **Weiß-Repertoire** und
  **Schwarz-Repertoire**. Ein Repertoire ist eine **Menge thematischer
  Gruppen** (nicht direkt von Varianten) und darf **jederzeit ergänzt**
  werden.
- **Zuordnung:** jede thematische Gruppe gehört zu **genau einem** Repertoire
  — Weiß *oder* Schwarz — oder (noch) zu keinem. Die Varianten eines
  Repertoires sind die **Vereinigung** der Varianten seiner zugeordneten
  Gruppen. Begründung: die Seite bestimmt zugleich die Trainingsfarbe; eine
  Gruppe „beidseitig" hieße, dieselbe Linie aus der falschen Seite zu üben.
- **Weiß / Schwarz beim Üben:** das Weiß-Repertoire wird als Weiß trainiert,
  das Schwarz-Repertoire als Schwarz — das deckt sich mit dem vorhandenen
  Farbschalter.
- **Set-Training:** die fehlende Handlung — eine ganze Gruppe *oder ein ganzes
  Repertoire* der Reihe nach durchspielen.

Es sind also **zwei Ebenen**: Gruppe (→ Varianten) und Repertoire (→ Gruppen).
Das Repertoire bleibt trotzdem **kein Duplikat** der Varianten — es referenziert
Gruppen, die ihrerseits Varianten referenzieren.

**Datenmodell-Hinweis / Namensfalle:** Im Code heißt die vorhandene
Sammelstruktur bereits `Repertoire` (sie hält *alle* Gruppen). Das neue
Nutzer-Konzept „Weiß-/Schwarz-Repertoire" ist etwas anderes und bekommt im Code
einen eigenen Namen (z. B. `RepertoireSide` / „Farbrepertoire"), um
Verwechslung zu vermeiden. Umgesetzt wird es **minimal**: jede Gruppe erhält
ein **Seiten-Feld** (Weiß / Schwarz / keine). Das Repertoire ist daraus
*abgeleitet* (alle Gruppen einer Seite) — keine separate Struktur, keine Kopie
von Varianten.

## 4. Was es schon gibt (darauf bauen wir auf, nichts davon neu)

- Einzel-Linientraining (Weiß/Schwarz, Gegenzüge) — stabil.
- Vollständiges Fehlerprotokoll + Fehlzug-Sitzungen — ausgereift.
- Statistik je Variante (Versuche, Richtig, Fehler, Trefferquote).
- Gruppen anlegen/zuweisen/umbenennen/löschen, Mehrfachzugehörigkeit.
- `repertoire.lines_for_category(...)` liefert alle Linien einer Gruppe —
  **getestet, aber vom Training bisher ungenutzt.**
- `session_log.summarize_training_sessions(...)` für Verlauf über Zeit —
  **vorhanden, aber in der UI nicht gezeigt.**

## 5. Die Lücke

Training läuft **immer nur eine einzelne Linie**. Es gibt:

- kein Training einer Gruppe / eines Repertoires am Stück,
- keine Trefferquote auf Set-Ebene,
- keinen sichtbaren Fortschritt über Zeit.

Damit zahlt die ganze Gruppen-Mechanik bisher auf kein Ziel ein.

## 6. Der Kern-Baustein: Set-Training

Eine **Set-Sitzung** geht eine Linienmenge der Reihe nach durch — analog zur
bestehenden `WrongMoveSession`, nur über Linien statt über Fehlzüge. Sie ist
**agnostisch**: Sie bekommt eine fertige, geordnete Linienliste, egal woher.

Zwei Einstiegspunkte liefern diese Liste:

- **Gruppe trainieren:** die Linien einer thematischen Gruppe
  (über `lines_for_category`).
- **Repertoire trainieren:** die Linien **aller Gruppen**, die dem Weiß- bzw.
  Schwarz-Repertoire zugeordnet sind (Vereinigung, dedupliziert).

Jeweils gefiltert auf trainierbare Linien (haben Züge). Ablauf: Linie 1
vollständig, dann Linie 2, … pro Linie der vorhandene `TrainingState`.
Zählung: erledigte Linien / gesamt, richtig / falsch über die Sitzung.
Abschluss: Zusammenmeldung; danach Trefferquote des Sets.

Die **Trainingsfarbe** ergibt sich aus der Seite: „Repertoire trainieren" setzt
sie automatisch (Weiß-Repertoire → Weiß). „Gruppe trainieren" nimmt die Farbe
aus der Seite der Gruppe; hat die Gruppe keine Seite, gilt der vorhandene
Farbschalter.

Fortschritt-pro-Set fällt fast nebenbei ab: die Statistik je Linie existiert
schon (`stats_for_line`); sie muss nur über die Gruppe summiert und angezeigt
werden.

## 7. Reihenfolge der Umsetzung (klein, testfirst, gesichert)

Wie schon bei `WrongMoveSession`: erst die reine Fachlogik mit Tests, dann
die UI.

1. **Fachlogik `TrainingRun`** (neues Modul, rein, ohne GUI): geordnete
   Linienliste, aktueller Index, `advance()`, `is_finished`, Zähler,
   Fortschrittstext. Vollständig per Unit-Test abgedeckt.
2. **Gruppe → Repertoire im Datenmodell:** jede Gruppe bekommt ein Seiten-Feld
   (Weiß / Schwarz / keine); Laden/Speichern in `repertoire.json` erweitern.
   Reine Logik „Linien eines Repertoires" (Vereinigung der Gruppen einer Seite).
   Test zuerst, abwärtskompatibel zu bestehenden Dateien (fehlendes Feld =
   keine Seite).
3. **Set-Statistik:** reine Funktion „Trefferquote über eine Linienmenge"
   aus vorhandenen Events. Test zuerst.
4. **UI-Andockung:** im Verwalten-Dialog je Gruppe Weiß/Schwarz zuordnen;
   Knöpfe „Gruppe trainieren" / „Weiß-Repertoire trainieren" /
   „Schwarz-Repertoire trainieren"; die Set-Sitzung steuert, welche Linie der
   `TrainingState` gerade zeigt; Fortschritt in der Statusleiste (wie bei der
   Fehlzug-Sitzung).
5. **Begriffe nachziehen:** „Repertoire" sichtbar machen, wo es trainiert wird.
6. **Optional später:** Fortschritt über Zeit (das vorhandene `session_log`
   in der UI zeigen).

## 8. Bewusst NICHT jetzt (Scope-Schutz)

- Spaced-Repetition-Algorithmus / Fälligkeiten.
- Grafische Verlaufskurven.
- Stockfish, Lichess-Explorer, Analysemodus.
- Eine Repertoire-Struktur, die Varianten **kopiert** (statt nur Gruppen zu
  referenzieren). Die Zuordnung bleibt minimal: Gruppe → Weiß/Schwarz.

Diese Punkte kommen erst infrage, wenn der Kern — ein Set am Stück trainieren
und seinen Fortschritt sehen — steht und sich bewährt hat.
