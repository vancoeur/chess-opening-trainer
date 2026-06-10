# Konzeptskizze: Repertoire-Bedienung verständlich machen

Stand: 2026-06-02. Reaktion auf klares Nutzerfeedback: „Ich durchschaue die
Bedienlogik nicht, es ist unklar, was die Buttons bewirken, und wie ich
Eröffnungen einem Repertoire zuweise." Diese Skizze klärt die Bedienung,
*bevor* gebaut wird. Sie ergänzt KONZEPT_Repertoiretraining.md (Datenmodell
bleibt: Variante → Gruppe → Repertoire-Seite).

## Das eigentliche Problem

Nicht die Logik im Code ist falsch, sondern ihre **Darstellung**:

1. **„Repertoire" ist unsichtbar.** Es ist nur eine Aktion (ein Knopf), nie ein
   Ding, das man sieht. Man kann nirgends ablesen „Mein Weiß-Repertoire besteht
   aus diesen Gruppen". Ohne sichtbare Struktur bildet sich kein Bild im Kopf.
2. **Das Zuweisen ist verstreut.** Eröffnung → Gruppe passiert im Reiter
   (Häkchen), Gruppe → Repertoire in einem versteckten Dialog („→ Weiß"). Zwei
   Orte, drei Schritte, kein roter Faden.
3. **Zu viele Bedienelemente auf einmal** im Reiter „Bibliothek & Training".

## Leitidee: drei Verben, drei klare Orte

Die Arbeit zerfällt in drei einfache Tätigkeiten. Jede bekommt einen eigenen,
aufgeräumten Ort:

| Verb | Frage | Ort |
|------|-------|-----|
| **Organisieren** | Welche Eröffnung gehört in welche Gruppe? | Reiter „Bibliothek" |
| **Repertoire bauen** | Welche Gruppe gehört zu Weiß/Schwarz? | Reiter „Repertoire" (neu, sichtbar) |
| **Üben** | Variante / Gruppe / Repertoire trainieren | dort, wo man das Objekt sieht |

Reiter werden also: **Bibliothek · Repertoire · Fehlerprotokoll**.

## Reiter „Bibliothek" (organisieren)

- PGN laden, Filter, Variantentabelle.
- Gewählte Variante: Häkchenliste „In diesen Gruppen" (Variante ↔ Gruppe) —
  bleibt, das ist der Organisations-Schritt und schon sichtbar.
- Knopf „Gewählte Variante trainieren" (Einzel-Linie übt man hier, wo man sie
  auswählt).

Das war's. Dieser Reiter beantwortet nur: *welche Eröffnung ist in welcher
Gruppe.*

## Reiter „Repertoire" (bauen + üben) — das neue, sichtbare Herzstück

Ein Baum zeigt die Struktur direkt:

```
▾ Weiß-Repertoire                         [ trainieren ]
     Englisch              (5 Varianten)
     Vier-Springer         (3)
▾ Schwarz-Repertoire                      [ trainieren ]
     Slawisch              (4)
     Französisch           (6)
▾ Noch keinem Repertoire zugeordnet
     Königsgambit          (2)
```

Aktionen (auf die in der Liste gewählte Gruppe):

- **[→ Weiß]  [→ Schwarz]  [herausnehmen]** — ordnet die Gruppe einem Repertoire
  zu oder löst sie. Direkt sichtbar, kein Dialog.
- **[Gruppe trainieren]** — übt die gewählte Gruppe am Stück.
- **[Weiß-Repertoire trainieren] / [Schwarz-Repertoire trainieren]** — übt alle
  Gruppen der Seite.
- Reihenfolge-Auswahl (PGN / schwächste zuerst) sitzt hier, wo trainiert wird.
- Gruppenpflege (neu / umbenennen / löschen) ebenfalls hier statt im Extra-Dialog.

Jetzt **sieht** man das Repertoire, füllt es an einer Stelle und übt es dort.

## Was wegfällt (es wird einfacher, nicht mehr)

- der separate Dialog „Gruppen verwalten …" (geht im Repertoire-Reiter auf)
- der „Trainieren"-Block mit vier Knöpfen unten im Bibliotheks-Reiter
- die indirekte Kopplung „Gefilterte Gruppe" an das Filter-Auswahlfeld
- die Verwechslungsgefahr Farbe/Seite (Repertoire-Training setzt die Farbe selbst)

## Nutzer-Ablauf, in je einem Satz

1. **Bibliothek:** Eröffnung anklicken, Gruppe ankreuzen.
2. **Repertoire:** Gruppe auswählen, „→ Weiß" oder „→ Schwarz".
3. **Repertoire:** „Weiß-Repertoire trainieren".

## Bauplan (klein, testfirst, jederzeit lauffähig)

1. Neuer Reiter „Repertoire" mit Baum als **reine Anzeige** der Struktur
   (Weiß / Schwarz / nicht zugeordnet + Gruppen + Variantenzahl). Nichts geht
   kaputt, nur sichtbar machen. Helfer-Logik (Gruppen je Seite, Zähler) als
   reine, getestete Funktion.
2. Aktionen im Baum: → Weiß / → Schwarz / herausnehmen (nutzt vorhandenes
   set_category_side).
3. Training in den Baum verlegen (Gruppe / Repertoire), inкл. Reihenfolge.
4. Aufräumen: alten Trainieren-Block, Verwalten-Dialog und Gefilterte-Gruppe-
   Kopplung aus „Bibliothek" entfernen; Gruppenpflege in den Repertoire-Reiter.
5. Beschriftungen klar und einheitlich.

Nach jedem Schritt: Tests grün, optisch prüfbar. Datenmodell und Trainingslogik
bleiben unverändert — dies ist reine Umordnung der Oberfläche.
