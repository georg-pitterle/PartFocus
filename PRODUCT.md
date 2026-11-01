# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

Das Schema kennt keinen Desktop-Wert, „web“ ist nur der nächstliegende. Tatsächlich ist PartFocus eine
Windows-Desktop-App mit PySide6/Qt Widgets, keine Website und keine native Mobile-App. Für Designarbeit
gelten daher die Erwartungen an Windows-Desktop-Programme, nicht die an Webseiten.

## Users

Chorleiterinnen und Chorleiter, die für ihren eigenen Chor Übe-Tracks vorbereiten. Sie haben die Partituren
als MuseScore-Dateien und wollen daraus für jede Stimme einen Track, den die Sängerinnen und Sänger zu Hause
zum Üben nutzen. MuseScore- oder Audio-Vorkenntnisse dürfen nicht nötig sein.

Die Sängerinnen und Sänger nutzen die App selbst nicht, sie hören nur das Ergebnis.

## Product Purpose

PartFocus macht aus MuseScore-Partituren Übe-Tracks pro Stimme: Die eigene Stimme steht vorne, die anderen
laufen leiser mit, dazu kommt ein „Gesamt“-Track. Erfolg heißt: Partitur hineinziehen, wenige Einstellungen
prüfen, „Tracks erstellen“, und die fertigen Dateien können hochgeladen werden.

## Positioning

Der eigene Export aus MuseScore wäre Handarbeit pro Stimme. PartFocus erledigt alle Stimmen einer oder
mehrerer Partituren in einem Durchgang und richtet das Ergebnis aufs Üben aus: Die Zielstimme bleibt gut
hörbar (eingeebnete Dynamik, Unisono nur einmal, Begleitung leise), und die Dateien bleiben klein.

## Operating Context

- Ablauf: Partituren (.mscz) ins Fenster ziehen, Einstellungen wählen, Tracks erstellen. Die Tracks landen
  neben der Partitur im Ordner `<Stück>/`.
- Danach lädt die Chorleitung die Tracks in die eigene Chor-App bzw. Website hoch. Abgespielt wird dort im
  Browser; darum zählen kleine Dateien und MIDI, das auch in Browser-Playern richtig klingt.
- Rendern dauert je nach Partitur und Zahl der Tracks spürbar lange und läuft über MuseScore im Hintergrund.
  Es lässt sich abbrechen.

## Capabilities and Constraints

- Eingabe: MuseScore-Partituren (.mscz), auch aus MuseScore 3. Das Original bleibt unverändert.
- Einstellbar: Lautstärke der anderen Stimmen, Dynamik, Klang (Original, Muse Choir, Grand Piano), Tempo
  (auch mehrere Fassungen), Format (MP3, MIDI, beides), Bitrate, Unisono, Begleitung, kurze Dateinamen.
- Voraussetzungen auf dem Rechner: Windows, MuseScore Studio 4, Muse Sounds über MuseHub. Fehlt etwas, warnt
  die App beim Start.
- Neben der Oberfläche gibt es eine Kommandozeile (`partfocus-cli`), die nicht alle Einstellungen abdeckt.
- Updates kommen automatisch über GitHub-Releases (Velopack).
- Begriffe: „Stimme“, „Track“, „Partitur“, „Gesamt“, „Begleitung“, „Unisono einfach“.
- Die Oberfläche ist deutsch. Mehrsprachigkeit (z. B. Englisch) ist denkbar, aber noch nicht entschieden;
  andere Betriebssysteme sind nicht geplant.

## Brand Commitments

Der Name ist PartFocus. Die Oberfläche spricht Klartext auf Deutsch.

## Evidence on Hand

Vorhanden sind README.md und die App selbst. Es gibt keine Testimonials, Nutzerzahlen, Referenzchöre oder
Benchmarks; solche Angaben dürfen nicht erfunden werden.

## Product Principles

1. Der Weg von der Partitur zum fertigen Track braucht möglichst wenige Klicks.
2. Die Standardeinstellungen liefern ohne Vorwissen brauchbare Tracks, Optionen sind Zugabe statt Pflicht.
3. Entscheidend ist, dass Sängerinnen und Sänger ihre Stimme gut hören, nicht wie schön die Aufnahme klingt.
4. Das Ergebnis muss gut in die Chor-App passen: kleine Dateien, klare Namen, keine Überraschungen im Browser.
