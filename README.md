# PartFocus

Übe-Tracks pro Stimme aus MuseScore-Partituren. Für jede Stimme entsteht eine
MP3, in der diese Stimme vorne steht und die anderen leiser mitlaufen, dazu ein
„Gesamt“-Track. Gerendert wird mit MuseScore 4 und Muse Sounds.

- Lautstärke der anderen Stimmen einstellbar (−40 bis −5 dB)
- Dynamik wahlweise eingeebnet, damit leise Stellen hörbar bleiben
- Unisono einfach: singen mehrere Stimmen denselben Ton, erklingt er nur einmal
- Begleitung (z. B. Klavier) wahlweise leise in jedem Track oder stumm
- Klang: Original, Muse Choir oder Grand Piano
- Tempo: 100 % bis 50 % in 10-%-Schritten, auch mehrere Fassungen auf einmal
- Format: MP3, MIDI oder beides; MIDI-Dateien sind nur wenige KB groß
- MP3 mit 192, 128, 96 oder 64 kbps (pro Minute etwa 1,4 / 1 / 0,7 / 0,5 MB)
- mit Original-Dynamik alle Tracks auf −1 dBFS normalisiert, nichts übersteuert
- auch für MuseScore-3-Dateien

## Voraussetzungen

- Windows
- [MuseScore Studio 4](https://musescore.org) unter `C:\Program Files\MuseScore 4\`
- Muse Sounds (Muse Choir, Muse Keys) über [MuseHub](https://www.musehub.com)

## Installation

Den Installer aus den [Releases](https://github.com/georg-pitterle/PartFocus/releases)
laden. PartFocus aktualisiert sich danach selbst.

## Benutzung

Partituren (.mscz) ins Fenster ziehen, Einstellungen wählen, „Tracks erstellen“.
Die Tracks landen neben der Partitur im Ordner `<Stück>/`.

Kommandozeile:

```
partfocus-cli <datei.mscz | ordner> [--sound=original|choir|piano] [--tempo=100,80] [--dry-run]
              [--format=mp3|midi|both] [--bitrate=192|128|96|64] [--keep-unison] [--no-accompaniment]
              [--mscore=<MuseScore4.exe>] [--sampler=<MuseSampler-Ordner>]
```

Standardpfade: `C:\Program Files\MuseScore 4\bin\MuseScore4.exe` und
`%LOCALAPPDATA%\MuseSampler`. Liegen sie woanders, in der Oberfläche unter
„Pfade …“ ändern. Fehlt beim Start etwas, warnt PartFocus.

## Funktionsweise

Pro Stimme schreibt PartFocus eine Kopie der Partitur ins Temp-Verzeichnis. Das
Original bleibt unverändert.

- **Lautstärken:** In `audiosettings.json` der .mscz bekommt jeder Part sein
  `out.volumeDb`, die Zielstimme 0 dB, die anderen den eingestellten Wert. Das
  Metronom bleibt unberührt.
- **Dynamik:** Jedes `<Dynamic>` bekommt dieselbe Stufe und Velocity, Crescendo-
  und Decrescendo-Gabeln (`<Spanner type="HairPin">`) werden entfernt.
- **Unisono:** Für jede Note wird Einsatz, Tonhöhe und Länge berechnet
  (gebundene Noten zählen als ein Ton, Vorschläge nicht). Singt ein anderer Part
  denselben Ton mit gleichem Einsatz und mindestens gleicher Länge, bekommt die
  Kopie `<play>0</play>` und bleibt stumm. Behalten wird die Zielstimme, im
  „Gesamt“-Track der oberste Part. So werden Stellen, an denen z. B. Sopran 1–3
  zusammen singen, nicht lauter als geteilte Stellen. Mit `--keep-unison` bzw.
  ohne Haken bei „Unisono einfach“ bleibt alles hörbar.
- **Begleitung:** Hat eine Partitur Gesangsstimmen (Instrument `voice.*`), gelten
  alle anderen Parts als Begleitung. Sie bekommen keinen eigenen Track und laufen
  in jedem Stimm-Track so laut wie die anderen Stimmen mit, im „Gesamt“-Track
  voll. Beim Unisono bleiben sie außen vor, ein Klavier, das den Chor verdoppelt,
  spielt also weiter. Mit `--no-accompaniment` bzw. ohne Haken bei „Begleitung“
  bekommen alle ihre Noten `<play>0</play>`. Partituren ganz ohne Gesangsstimmen
  bekommen wie bisher einen Track pro Instrument.
- **Klang:** Ersetzt `track["in"]` durch einen Muse-Sounds-Eintrag. Muse Choir
  wählt die Stimme nach Instrument bzw. Stimmname: Sopran/Mezzo → Sopranos,
  Alt → Altos, Tenor → Tenors, Bariton/Bass → Basses. Andere Instrumente bleiben
  original. Die Dateinamen bekommen dann den Zusatz „(Muse Choir)“ bzw.
  „(Grand Piano)“.
- **Tempo:** Jeder `<tempo>`-Wert der Tempoangaben wird mit dem Prozentsatz
  multipliziert. rit./accel. sind relativ und skalieren mit. Beginnt die Partitur
  ohne Tempoangabe, kommt eine unsichtbare mit 120 BPM (MuseScore-Standard) dazu.
  Weil MuseScore die Noten langsamer spielt, bleibt die Tonhöhe gleich. Fassungen
  unter 100 % bekommen den Zusatz „(80%)“. Gemessen wird nur die schnellste
  gewählte Fassung, die langsameren übernehmen ihren Pegel.
- **MIDI:** Dieselbe Variante der Partitur wird mit MuseScore als `.mid`
  exportiert, eine Spur pro Notensystem. Eingeebnete Dynamik, Unisono und Tempo
  stecken damit schon drin, die Lautstärke der Parts aber nicht. Darum senkt
  PartFocus danach die Velocity jeder Note der anderen Stimmen um den
  eingestellten Wert (−25 dB: aus 80 wird 4, mindestens 1). Die Kanallautstärke
  (CC7) bleibt, weil Browser-Player wie html-midi-player sie ignorieren. Einen
  Klang hat MIDI nicht, den wählt das Abspielprogramm; die Dateinamen bekommen
  daher keinen Klang-Zusatz, und gemessen wird nichts. MIDI wird in einem
  eigenen MuseScore-Aufruf nach den MP3s exportiert, gemischt stürzt MuseScore ab.
- **MuseScore-3-Dateien** haben keine `audiosettings.json` und keine Part-IDs.
  Sie werden zuerst mit `MuseScore4.exe -o` umgewandelt. Die fehlenden
  Track-Einträge legt PartFocus ohne `in` an, dann wählt MuseScore den Klang
  wie beim normalen Öffnen.
- **Rendern** mit `MuseScore4.exe -j job.json --sound-profile "Muse Sounds"`.
  Mit eingeebneter Dynamik ist der Pegel fest: ein Durchlauf als MP3 mit
  der gewählten Bitrate (`-b`, Standard 128 kbps), `master.volumeDb` bleibt 0 dB.
  Mit Original-Dynamik zwei Durchläufe:
  1. WAV rendern und den Spitzenpegel messen
  2. `master.volumeDb` so setzen, dass die Spitze bei −1 dBFS liegt (Boost
     höchstens +24 dB), dann die MP3 rendern
- **Updates:** Velopack prüft kurz nach dem Start im Hintergrund die GitHub-Releases.
  Ein geladenes Update wird beim Schließen installiert oder sofort über
  „Jetzt neu starten“.

## Entwicklung

```
python -m venv .venv
.venv\Scripts\pip install -e .[dev]
.venv\Scripts\pytest -q
.venv\Scripts\python -m partfocus
```

Das Icon erzeugt `tools/make_icon.py` aus der App-Palette.

Releases entstehen über [release-please](https://github.com/googleapis/release-please):
Commits im Stil von Conventional Commits (`feat:`, `fix:` …) auf `main` halten einen
Release-PR offen. Nach seinem Merge baut `release.yml` das Bundle, prüft es per
Selbsttest, packt es mit Velopack und veröffentlicht das Release.

Einmalig im Repo nötig: Settings → Actions → General → Workflow permissions →
„Allow GitHub Actions to create and approve pull requests“.
