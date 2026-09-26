# PartFocus

Übe-Tracks pro Stimme aus MuseScore-Partituren. Für jede Stimme entsteht eine
MP3, in der diese Stimme vorne steht und die anderen leiser mitlaufen, dazu ein
„Gesamt“-Track. Gerendert wird mit MuseScore 4 und Muse Sounds.

- Lautstärke der anderen Stimmen einstellbar (−40 bis −5 dB)
- Dynamik wahlweise eingeebnet, damit leise Stellen hörbar bleiben
- Klang: Original, Muse Choir oder Grand Piano
- alle Tracks auf −1 dBFS normalisiert, nichts übersteuert
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
Die MP3s landen neben der Partitur im Ordner `<Stück>/`.

Kommandozeile:

```
partfocus-cli <datei.mscz | ordner> [--sound=original|choir|piano] [--dry-run]
```

## Funktionsweise

Pro Stimme schreibt PartFocus eine Kopie der Partitur ins Temp-Verzeichnis. Das
Original bleibt unverändert.

- **Lautstärken:** In `audiosettings.json` der .mscz bekommt jeder Part sein
  `out.volumeDb`, die Zielstimme 0 dB, die anderen den eingestellten Wert. Das
  Metronom bleibt unberührt.
- **Dynamik:** Jedes `<Dynamic>` bekommt dieselbe Stufe und Velocity, Crescendo-
  und Decrescendo-Gabeln (`<Spanner type="HairPin">`) werden entfernt.
- **Klang:** Ersetzt `track["in"]` durch einen Muse-Sounds-Eintrag. Muse Choir
  wählt die Stimme nach Instrument bzw. Stimmname: Sopran/Mezzo → Sopranos,
  Alt → Altos, Tenor → Tenors, Bariton/Bass → Basses. Andere Instrumente bleiben
  original. Die Dateinamen bekommen dann den Zusatz „(Muse Choir)“ bzw.
  „(Grand Piano)“.
- **MuseScore-3-Dateien** haben keine `audiosettings.json` und keine Part-IDs.
  Sie werden zuerst mit `MuseScore4.exe -o` umgewandelt. Die fehlenden
  Track-Einträge legt PartFocus ohne `in` an, dann wählt MuseScore den Klang
  wie beim normalen Öffnen.
- **Rendern** in zwei Durchläufen mit je einem Aufruf
  `MuseScore4.exe -j job.json --sound-profile "Muse Sounds"`:
  1. WAV rendern und den Spitzenpegel messen
  2. `master.volumeDb` so setzen, dass die Spitze bei −1 dBFS liegt (Boost
     höchstens +24 dB), dann MP3 mit 192 kbps rendern
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
