"""PartFocus: Übe-Tracks aus MuseScore-Partituren (.mscz) mit Muse Sounds.

Pro Stimme eine MP3 (Zielstimme 0 dB, Rest Options.others_db) plus "Gesamt" (alle gleich laut).
Dynamik wird eingeebnet: alle Dynamikzeichen -> Options.flat_dynamic, Gabeln entfernt.
Klang wählbar: Original, Muse Choir (Stimme nach Name/Instrument) oder Grand Piano für alle.
MuseScore-3-Dateien (ohne audiosettings.json) werden vorher mit MuseScore 4 umgewandelt.
Mit Original-Dynamik zwei Durchläufe: erst WAV zum Peak-Messen, dann MP3 mit Master-Gain auf PEAK_DBFS.
Mit eingeebneter Dynamik ist der Pegel fest: nur MP3, Master 0 dB.
Tempo wählbar, auch mehrere Fassungen auf einmal (Options.tempos, Prozent vom Original); gemessen wird
nur die schnellste, die anderen übernehmen ihren Pegel.
Unisono: singen mehrere Parts denselben Ton, erklingt er nur einmal (Options.merge_unison).
MIDI statt oder neben MP3 (Options.format): andere Stimmen leiser über die Velocity, ohne Klang und Pegel.
Begleitung (Instrumente neben Gesangsstimmen, z. B. Klavier): kein eigener Track, läuft in jedem Track
so laut wie die anderen Stimmen mit oder bleibt stumm (Options.accompaniment).
Aufruf:  partfocus-cli [datei.mscz | ordner] [--sound=original|choir|piano] [--tempo=100,80] [--dry-run]
         [--format=mp3|midi|both] [--bitrate=128] [--keep-unison] [--no-accompaniment] [--mscore=MuseScore4.exe]
         [--sampler=MuseSampler-Ordner]
Ausgabe: <ordner>/<stück>/<stück> - <Stimme>[ (<Klang>)][ (<Tempo>%)].mp3, MIDI ohne Klang als .mid
GUI:     partfocus
"""
import array, json, math, os, re, struct, subprocess, sys, tempfile, time, zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Callable

MSCORE = r"C:\Program Files\MuseScore 4\bin\MuseScore4.exe"
TARGET_DB = 0.0
PEAK_DBFS = -1.0
MAX_GAIN_DB = 24.0
DEFAULT_TEMPO = 2.0  # Viertel pro Sekunde = 120 BPM, wenn die Partitur keine Tempoangabe hat
TEMPOS = (100, 90, 80, 70, 60, 50)  # wählbare Tempi in Prozent vom Original
BITRATES = (192, 128, 96, 64)  # wählbare MP3-Bitraten in kbps; die Dateigröße wächst proportional
VELOCITY = {"ppp": 16, "pp": 33, "p": 49, "mp": 64, "mf": 80, "f": 96, "ff": 112, "fff": 126}


def _muse(uid: str, name: str, pack: str, setup: str) -> dict:
    """Muse-Sounds-Eintrag für track["in"], so wie MS 4.x ihn in audiosettings.json schreibt."""
    return {"resourceMeta": {"attributes": {"museCategory": pack, "museName": name, "musePack": pack,
                                            "museUID": uid, "museVendorName": "Muse", "playbackSetupData": setup},
                             "hasNativeEditorSupport": False, "id": uid,
                             "type": "muse_sampler_sound_pack", "vendor": "MuseSounds"},
            "unitConfiguration": {}}


GRAND_PIANO = _muse("167", "Grand Piano", "Muse Keys", "keyboards.piano")
# Reihenfolge zählt: "mezzo" vor "alt", "bari" vor "bass" ist egal, beides Basses.
CHOIR = [(("sopran", "mezzo", "treble", "diskant"), _muse("19", "Sopranos", "Muse Choir", "voices.choir.soprano")),
         (("alt", "contralto"), _muse("20", "Altos", "Muse Choir", "voices.choir.alto")),
         (("tenor",), _muse("21", "Tenors", "Muse Choir", "voices.choir.tenor")),
         (("bari", "bass"), _muse("22", "Basses", "Muse Choir", "voices.choir.bass"))]
SOUNDS = {"original": "Original", "choir": "Muse Choir", "piano": "Grand Piano"}
FORMATS = {"mp3": "MP3", "midi": "MIDI", "both": "MP3 + MIDI"}


def choir_voice(instrument_id: str, name: str) -> dict | None:
    """Passende Muse-Choir-Stimme; zuerst nach Instrument, dann nach Stimmname. None = kein Chorpart."""
    for text in (instrument_id.lower(), name.lower()):
        for keys, res in CHOIR:
            if any(k in text for k in keys):
                return res
    return None


def apply_sound(audio: dict, names: dict[str, str], sound: str) -> dict:
    """Kopie von audio mit ersetztem Klang pro Track."""
    a = json.loads(json.dumps(audio))
    if sound == "original":
        return a
    for t in a["tracks"]:
        if t.get("instrumentId") == "metronome":
            continue
        res = GRAND_PIANO if sound == "piano" else choir_voice(t.get("instrumentId", ""), names.get(t["partId"], ""))
        if res is not None:
            t["in"] = json.loads(json.dumps(res))
    return a


def default_sampler() -> Path:
    """Wo Muse Hub die MuseSampler-Bibliothek installiert."""
    return Path(os.environ.get("LOCALAPPDATA", "")) / "MuseSampler"


def missing_requirements(mscore: str = MSCORE, sampler: Path | None = None) -> list[str]:
    """Was für den Export fehlt, als Klartext; leer = alles da.

    Muse Sounds = MuseSampler-Bibliothek (von Muse Hub unter %LOCALAPPDATA%\\MuseSampler installiert)
    plus Instrumente; deren Ordner steht in MuseSampler\\.config. Choir und Keys braucht die Klang-Auswahl.
    """
    missing = []
    if not Path(mscore).is_file():
        missing.append(f"MuseScore 4 nicht gefunden ({mscore})")
    sampler = sampler or default_sampler()
    if not (sampler / "lib" / "MuseSamplerCoreLib.dll").is_file():
        return missing + ["Muse Sounds nicht installiert (über Muse Hub installieren)"]
    try:
        instruments = Path((sampler / ".config").read_text(encoding="utf-8").strip())
    except OSError:
        instruments = None
    if instruments is None or not instruments.is_dir():
        return missing + ["Keine Muse-Sounds-Instrumente gefunden (über Muse Hub installieren)"]
    for pack, sound in (("Muse Choir", "Muse Choir"), ("Muse Keys", "Grand Piano")):
        if not (instruments / pack).is_dir():
            missing.append(f"{pack} nicht installiert, Klang „{sound}“ klingt nicht wie erwartet")
    return missing


@dataclass
class Options:
    others_db: float = -25.0
    flat_dynamic: str | None = "mf"  # None = Original-Dynamik behalten
    sound: str = "original"  # Schlüssel aus SOUNDS
    tempos: tuple[int, ...] = (100,)  # eine Fassung pro Tempo, Prozent vom Original
    merge_unison: bool = True  # gleicher Ton in mehreren Parts erklingt nur einmal
    format: str = "mp3"  # Schlüssel aus FORMATS
    accompaniment: bool = True  # Begleitung leise mitspielen statt stumm
    bitrate: int = 128  # kbps, aus BITRATES
    mscore: str = MSCORE


@dataclass
class Result:
    out: Path
    peak_db: float | None  # None = nicht gemessen
    gain: float

    @property
    def ok(self) -> bool:
        return self.out.exists() and (self.peak_db is None or self.peak_db > -60)


class Cancelled(Exception):
    pass


def _score_parts(root: ET.Element):
    """(partId, Instrument-Element, Part-Element). MS3-Dateien haben keine IDs; MS4 nummeriert beim Umwandeln 1..N."""
    return [(p.get("id") or str(i), p.find("Instrument"), p)
            for i, p in enumerate(root.find("Score").findall("Part"), 1)]


def _parts(z: zipfile.ZipFile):
    mscx = next(n for n in z.namelist() if n.endswith(".mscx") and "/" not in n)
    return _score_parts(ET.fromstring(z.read(mscx)))


def _accompaniment(parts) -> set[str]:
    """partIds der Begleitung: Parts ohne Gesangsstimme (instrumentId "voice.*") neben solchen mit.

    Ohne jede Gesangsstimme ist nichts Begleitung, dann bekommt jedes Instrument seinen Track.
    """
    sung = {pid for pid, inst, _ in parts
            if inst is not None and (inst.findtext("instrumentId") or "").startswith("voice.")}
    return {pid for pid, _, _ in parts} - sung if sung else set()


def accompaniment(z: zipfile.ZipFile) -> set[str]:
    return _accompaniment(_parts(z))


def part_names(z: zipfile.ZipFile) -> dict[str, str]:
    names, seen = {}, set()
    for pid, _, p in _parts(z):
        name = (p.findtext(".//longName") or p.findtext(".//trackName") or f"Part {pid}").strip()
        if name in seen:
            name = f"{name} ({pid})"
        seen.add(name)
        names[pid] = name
    return names


def load_audio(z: zipfile.ZipFile) -> dict | None:
    """audiosettings.json; fehlen die Tracks (frisch umgewandelt), werden sie aus den Parts angelegt.

    Einträge ohne "in" lassen MuseScore den Klang selbst wählen wie beim Öffnen der Datei,
    übernehmen aber die Lautstärke. None = MuseScore-3-Datei, muss erst umgewandelt werden.
    """
    if "audiosettings.json" not in z.namelist():
        return None
    audio = json.loads(z.read("audiosettings.json"))
    if not audio.get("tracks"):
        audio["tracks"] = [{"partId": pid, "instrumentId": inst.get("id", "") if inst is not None else "",
                            "out": {"volumeDb": 0, "balance": 0, "fxChain": {},
                                    "auxSends": [{"active": True, "signalAmount": 0.3}] * 2},
                            "soloMuteState": {"mute": False, "solo": False}}
                           for pid, inst, _ in _parts(z)]
    return audio


def convert(score: Path, dst: Path, opts: Options) -> Path:
    """MuseScore-3-Partitur ins MS4-Format bringen, damit es audiosettings.json gibt."""
    subprocess.run([opts.mscore, "-o", str(dst), str(score)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return dst


def flatten_dynamics(mscx: str, level: str) -> str:
    """Alle Dynamikzeichen auf `level` setzen, Crescendo-/Decrescendo-Gabeln entfernen."""
    mscx = re.sub(r"\s*<Spanner type=\"HairPin\">.*?</Spanner>", "", mscx, flags=re.S)
    mscx = re.sub(r"(<Dynamic>.*?<subtype>)\w+(</subtype>)", rf"\g<1>{level}\g<2>", mscx, flags=re.S)
    return re.sub(r"(<Dynamic>.*?<velocity>)\d+(</velocity>)", rf"\g<1>{VELOCITY[level]}\g<2>", mscx, flags=re.S)


def slow_tempo(mscx: str, percent: int) -> str:
    """Alle Tempoangaben auf `percent` Prozent; Gabeln wie rit./accel. sind relativ und skalieren mit.

    Beginnt die Partitur ohne Tempoangabe, spielt MuseScore 120 BPM; dafür kommt eine
    unsichtbare Angabe vor den ersten Akkord bzw. die erste Pause.
    """
    if percent == 100:
        return mscx
    factor = percent / 100
    first = re.search(r"<Measure\b.*?</Measure>", mscx, flags=re.S)
    if first and "<Tempo>" not in first.group(0):
        # Originaltempo einfügen, skaliert wird es unten mit allen anderen.
        hidden = (f"<Tempo><tempo>{DEFAULT_TEMPO:g}</tempo><visible>0</visible>"
                  f"<text><sym>metNoteQuarterUp</sym> = {DEFAULT_TEMPO * 60:g}</text></Tempo>")
        rest = re.compile(r"<(?:Chord|Rest)>").search(mscx, first.start(), first.end())
        if rest:
            mscx = mscx[:rest.start()] + hidden + mscx[rest.start():]
    return re.sub(r"(<Tempo>.*?<tempo>)([\d.]+)(</tempo>)",
                  lambda m: f"{m[1]}{float(m[2]) * factor:.6g}{m[3]}", mscx, flags=re.S)


DURATIONS = {"long": Fraction(4), "breve": Fraction(2), "whole": Fraction(1), "half": Fraction(1, 2),
             "quarter": Fraction(1, 4), "eighth": Fraction(1, 8), "16th": Fraction(1, 16),
             "32nd": Fraction(1, 32), "64th": Fraction(1, 64), "128th": Fraction(1, 128),
             "256th": Fraction(1, 256), "512th": Fraction(1, 512), "1024th": Fraction(1, 1024)}
GRACE = {"acciaccatura", "appoggiatura", "grace4", "grace16", "grace32", "grace8after", "grace16after",
         "grace32after"}


def _sounding_notes(root: ET.Element):
    """(System-Nr., Start, Ende, Tonhöhe, [Notennummern]) pro erklingendem Ton.

    Gebundene Noten sind ein Ton. Notennummer = Position unter allen <Note> im Dokument.
    Vorschläge und Noten mit <play>0</play> zählen nicht.
    """
    number = {id(n): i for i, n in enumerate(root.iter("Note"))}
    sig = Fraction(4, 4)
    for el in root.iter("TimeSig"):  # Taktart vor dem ersten Takt (falls schon im Kopf)
        sig = Fraction(int(el.findtext("sigN")), int(el.findtext("sigD")))
        break
    for staff_no, staff in enumerate(root.find("Score").findall("Staff"), 1):
        start, measure_sig, open_ties, tones = Fraction(0), sig, {}, []
        for measure in staff.findall("Measure"):
            for voice_no, voice in enumerate(measure.findall("voice")):
                tick, ratio = start, [Fraction(1)]
                for el in voice:
                    if el.tag == "TimeSig":
                        measure_sig = Fraction(int(el.findtext("sigN")), int(el.findtext("sigD")))
                    elif el.tag == "Tuplet":
                        ratio.append(ratio[-1] * int(el.findtext("normalNotes")) / int(el.findtext("actualNotes")))
                    elif el.tag == "endTuplet":
                        ratio.pop()
                    elif el.tag == "location":
                        tick += Fraction(el.findtext("fractions", "0"))
                    elif el.tag in ("Chord", "Rest"):
                        if any(c.tag in GRACE for c in el):
                            continue
                        kind = el.findtext("durationType")
                        if kind == "measure":
                            length = Fraction(el.findtext("duration", str(measure_sig)))
                        else:
                            dots = int(el.findtext("dots", "0"))
                            length = DURATIONS[kind] * (2 - Fraction(1, 2 ** dots)) * ratio[-1]
                        for note in el.findall("Note") if el.tag == "Chord" else ():
                            if note.findtext("play") == "0":
                                continue
                            pitch = int(note.findtext("pitch"))
                            tied_on = any(s.find("next") is not None for s in note.findall("Spanner[@type='Tie']"))
                            tone = open_ties.pop((voice_no, tick, pitch), None)
                            if tone is None:
                                tone = [staff_no, tick, tick + length, pitch, []]
                                tones.append(tone)
                            tone[2] = tick + length
                            tone[4].append(number[id(note)])
                            if tied_on:
                                open_ties[(voice_no, tick + length, pitch)] = tone
                        tick += length
            start += Fraction(measure.get("len")) if measure.get("len") else measure_sig
        yield from tones


def _staff_parts(root: ET.Element) -> list[str]:
    return [pid for pid, _, p in _score_parts(root) for _ in p.findall("Staff")]


def staff_parts(mscx: str) -> list[str]:
    """partId pro System, in Partitur-Reihenfolge."""
    return _staff_parts(ET.fromstring(mscx))


def scale_midi(path: Path, parts: list[str], target: str | None, others_db: float):
    """Andere Stimmen leiser über die Velocity jeder Note; Kanallautstärke (CC7) ignorieren manche Player.

    MuseScore schreibt eine Spur pro System, `parts` ordnet sie den Parts zu. Note-Enden
    (Velocity 0) bleiben, jede Note bleibt mit mindestens Velocity 1 hörbar.
    """
    if target is None:
        return
    import mido
    mid = mido.MidiFile(path)
    if len(mid.tracks) != len(parts):
        raise RuntimeError(f"{path.name}: {len(mid.tracks)} Spuren, aber {len(parts)} Notensysteme")
    factor = 10 ** (others_db / 20)
    for track, part in zip(mid.tracks, parts):
        if part == target:
            continue
        for i, msg in enumerate(track):
            if msg.type == "note_on" and msg.velocity:
                track[i] = msg.copy(velocity=max(1, round(msg.velocity * factor)))
    mid.save(path)


def _mute_notes(mscx: str, root: ET.Element, mute: set[int]) -> str:
    """<play>0</play> in die Noten mit diesen Nummern; der Text bleibt sonst unverändert."""
    # Notennummern gelten für den Text nur, wenn jede <Note> dort genau so steht.
    if not mute or mscx.count("<Note>") != sum(1 for _ in root.iter("Note")):
        return mscx
    count = iter(range(mscx.count("<Note>")))
    return re.sub(r"<Note>", lambda m: "<Note><play>0</play>" if next(count) in mute else m[0], mscx)


def mute_accompaniment(mscx: str) -> str:
    """Alle Noten der Begleitung stumm."""
    root = ET.fromstring(mscx)
    staff_part, parts = _staff_parts(root), _accompaniment(_score_parts(root))
    number = {id(n): i for i, n in enumerate(root.iter("Note"))}
    staves = root.find("Score").findall("Staff")
    mute = {number[id(n)] for no, staff in enumerate(staves) if no < len(staff_part) and staff_part[no] in parts
            for n in staff.iter("Note")}
    return _mute_notes(mscx, root, mute)


def merge_unison(mscx: str, keep: str | None) -> str:
    """Singen mehrere Parts denselben Ton, erklingt er nur einmal: Kopien bekommen <play>0</play>.

    Gleich heißt gleicher Einsatz und gleiche Tonhöhe; stumm wird eine Kopie nur, wenn der
    behaltene Ton mindestens so lange klingt. Behalten wird der Part `keep`, sonst der oberste.
    Innerhalb eines Parts bleibt alles, wie es ist, die Begleitung bleibt ganz außen vor.
    Der Text wird nur um die <play>-Tags ergänzt.
    """
    root = ET.fromstring(mscx)
    staff_part = _staff_parts(root)
    backing = _accompaniment(_score_parts(root))
    by_onset: dict[tuple, list] = {}
    for staff_no, begin, end, pitch, notes in _sounding_notes(root):
        part = staff_part[staff_no - 1] if staff_no <= len(staff_part) else str(staff_no)
        if part not in backing:
            by_onset.setdefault((begin, pitch), []).append((part, end, notes))
    mute = set()
    for tones in by_onset.values():
        if len({part for part, _, _ in tones}) < 2:
            continue
        order = [p for p in staff_part if p == keep] + staff_part
        kept = []
        for part, end, notes in sorted(tones, key=lambda t: order.index(t[0]) if t[0] in order else len(order)):
            if any(p != part and e >= end for p, e in kept):
                mute.update(notes)
            else:
                kept.append((part, end))
    return _mute_notes(mscx, root, mute)


def write_variant(src: Path, dst: Path, audio: dict, target: str | None, opts: Options, master_db: float = 0.0,
                  tempo: int = 100):
    a = json.loads(json.dumps(audio))
    a["master"]["volumeDb"] = master_db
    for t in a["tracks"]:
        if t.get("instrumentId") == "metronome":
            continue
        t["out"]["volumeDb"] = TARGET_DB if target is None or t["partId"] == target else opts.others_db
        t["soloMuteState"] = {"mute": False, "solo": False}
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "audiosettings.json":
                data = json.dumps(a, indent=4).encode()
            elif item.filename.endswith(".mscx") and "/" not in item.filename:
                mscx = data.decode("utf-8")
                if opts.flat_dynamic:
                    mscx = flatten_dynamics(mscx, opts.flat_dynamic)
                if opts.merge_unison:
                    mscx = merge_unison(mscx, target)
                if not opts.accompaniment:
                    mscx = mute_accompaniment(mscx)
                data = slow_tempo(mscx, tempo).encode("utf-8")
            zout.writestr(item, data)


def wav_peak(path: Path) -> float:
    """Peak einer Float-WAV (MuseScore exportiert IEEE float, Format 3)."""
    b = path.read_bytes()
    i = 12
    while i < len(b):
        cid, size = b[i:i + 4], struct.unpack("<I", b[i + 4:i + 8])[0]
        if cid == b"data":
            a = array.array("f", b[i + 8:i + 8 + size // 4 * 4])
            return max(max(a, default=0.0), -min(a, default=0.0))
        i += 8 + size + (size & 1)
    raise ValueError(f"Kein data-Chunk in {path}")


def render(jobs: list[dict], jobfile: Path, opts: Options,
           tick: Callable[[int], None] = lambda n: None, cancelled: Callable[[], bool] = lambda: False):
    """Alle Jobs in einem MuseScore-Aufruf; tick(n) meldet, wie viele Ausgaben schon existieren."""
    for j in jobs:
        Path(j["out"]).unlink(missing_ok=True)
    jobfile.write_text(json.dumps(jobs, ensure_ascii=False), encoding="utf-8")
    cmd = [opts.mscore, "-j", str(jobfile), "--sound-profile", "Muse Sounds", "-b", str(opts.bitrate)]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    while proc.poll() is None:
        if cancelled():
            proc.kill(); proc.wait()
            raise Cancelled()
        tick(sum(Path(j["out"]).exists() for j in jobs))
        time.sleep(0.3)
    if proc.returncode != 0:
        raise RuntimeError(f"MuseScore beendet mit Code {proc.returncode}")
    tick(len(jobs))


def safe(s: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", s).strip()


def voices(score: Path) -> list[tuple[str, str | None]]:
    """(Name, partId) pro Variante, beginnend mit ("Gesamt", None). Die Begleitung bekommt keinen Track."""
    with zipfile.ZipFile(score) as z:
        audio = load_audio(z)
        names = part_names(z)
        backing = accompaniment(z)
    names = {pid: n for pid, n in names.items() if pid not in backing}
    if audio is None:  # MS3: nach dem Umwandeln gibt es genau einen Track pro Part
        return [("Gesamt", None)] + [(n, pid) for pid, n in names.items()]
    track_ids = {t["partId"] for t in audio["tracks"] if t.get("instrumentId") != "metronome"} - backing
    part_ids = [pid for pid in names if pid in track_ids] + sorted(track_ids - names.keys())
    return [("Gesamt", None)] + [(names.get(pid, pid), pid) for pid in part_ids]


def plan(score: Path, tmp: Path, opts: Options) -> list[dict]:
    out_dir = score.parent / safe(score.stem)
    source = score
    with zipfile.ZipFile(score) as z:
        audio = load_audio(z)
    if audio is None:
        source = convert(score, tmp / f"{safe(score.stem)}__ms4.mscz", opts)
        with zipfile.ZipFile(source) as z:
            audio = load_audio(z)
    with zipfile.ZipFile(source) as z:
        audio = apply_sound(audio, part_names(z), opts.sound)
    jobs = []
    for tempo in sorted(set(opts.tempos), reverse=True):
        for label, pid in voices(source):
            v = tmp / f"{safe(score.stem)}__{safe(label)}__{tempo}.mscz"
            speed = "" if tempo == 100 else f" ({tempo}%)"
            # MIDI hat keinen Klang, der spielt in der App; darum dort kein Klang im Namen.
            outs = {"mp3": ("" if opts.sound == "original" else f" ({SOUNDS[opts.sound]})") + speed + ".mp3",
                    "midi": speed + ".mid"}
            for fmt in ("mp3", "midi") if opts.format == "both" else (opts.format,):
                jobs.append({"in": str(v), "out": str(out_dir / f"{safe(score.stem)} - {safe(label)}{outs[fmt]}"),
                             "wav": str(v.with_suffix(".wav")), "score": source, "audio": audio, "pid": pid,
                             "tempo": tempo, "key": (str(score), pid), "midi": fmt == "midi"})
    return jobs


def export(scores: list[Path], opts: Options,
           progress: Callable[[str, int, int], None] = lambda text, done, total: None,
           cancelled: Callable[[], bool] = lambda: False) -> list[Result]:
    """Rendert alle Übe-Tracks. progress(text, erledigt, gesamt) zählt beide Durchläufe."""
    with tempfile.TemporaryDirectory() as td:
        progress("Partituren vorbereiten", 0, 1)
        jobs = []
        for s in scores:
            if cancelled():
                raise Cancelled()
            jobs += plan(s, Path(td), opts)
        # Eingeebnete Dynamik heißt fester Pegel: kein Messdurchlauf, Master bleibt bei 0 dB.
        # Gemessen wird nur die schnellste Fassung, die langsameren übernehmen ihren Pegel.
        # MIDI hat keinen Pegel; bei "beides" teilen sich MP3 und MIDI dieselbe Variante.
        mp3s = [j for j in jobs if not j["midi"]]
        probes = [j for j in mp3s if j["tempo"] == max(opts.tempos)] if opts.flat_dynamic is None else []
        measured = len(probes)
        total = measured + len(jobs)
        for j in jobs:
            Path(j["out"]).parent.mkdir(exist_ok=True)
            write_variant(j["score"], Path(j["in"]), j["audio"], j["pid"], opts, tempo=j["tempo"])
            j["peak_db"], j["gain"] = None, 0.0
        jobfile = Path(td) / "job.json"
        if probes:
            progress(f"Pegel messen ({measured} Tracks)", 0, total)
            render([{"in": j["in"], "out": j["wav"]} for j in probes], jobfile, opts,
                   lambda n: progress(f"Pegel messen ({measured} Tracks)", n, total), cancelled)
            levels = {}
            for j in probes:
                peak = wav_peak(Path(j["wav"]))
                peak_db = 20 * math.log10(peak) if peak > 0 else -math.inf
                levels[j["key"]] = peak_db, min(MAX_GAIN_DB, PEAK_DBFS - peak_db)
            for j in mp3s:
                j["peak_db"], j["gain"] = levels[j["key"]]
                write_variant(j["score"], Path(j["in"]), j["audio"], j["pid"], opts, j["gain"], j["tempo"])
        # Getrennte Aufrufe: mischt einer Audio und MIDI, stürzt MuseScore ab.
        mids = [j for j in jobs if j["midi"]]
        done = measured
        for text, batch in (("MP3s rendern", mp3s), ("MIDI exportieren", mids)):
            if batch:
                progress(text, done, total)
                render([{"in": j["in"], "out": j["out"]} for j in batch], jobfile, opts,
                       lambda n, text=text, done=done: progress(text, done + n, total), cancelled)
                done += len(batch)
        for j in mids:
            with zipfile.ZipFile(j["in"]) as z:
                mscx = next(n for n in z.namelist() if n.endswith(".mscx") and "/" not in n)
                parts = staff_parts(z.read(mscx).decode("utf-8"))
            scale_midi(Path(j["out"]), parts, j["pid"], opts.others_db)
    return [Result(Path(j["out"]), j["peak_db"], j["gain"]) for j in jobs]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    arg = (Path(args[0]) if args else Path.cwd()).resolve()
    scores = [arg] if arg.is_file() else sorted(arg.glob("*.mscz"))
    if not scores:
        sys.exit(f"Keine .mscz in {arg}")
    opts, sampler = Options(), None
    for a in sys.argv[1:]:
        if a.startswith("--sound="):
            opts.sound = a.split("=", 1)[1]
            if opts.sound not in SOUNDS:
                sys.exit(f"--sound muss einer von {', '.join(SOUNDS)} sein")
        elif a.startswith("--tempo="):
            opts.tempos = tuple(int(t) for t in a.split("=", 1)[1].split(",") if t.strip())
            if not opts.tempos or not all(0 < t <= 100 for t in opts.tempos):
                sys.exit("--tempo erwartet Prozentwerte bis 100, z. B. --tempo=100,80")
        elif a.startswith("--format="):
            opts.format = a.split("=", 1)[1]
            if opts.format not in FORMATS:
                sys.exit(f"--format muss einer von {', '.join(FORMATS)} sein")
        elif a.startswith("--bitrate="):
            opts.bitrate = int(a.split("=", 1)[1]) if a.split("=", 1)[1].isdigit() else 0
            if opts.bitrate not in BITRATES:
                sys.exit(f"--bitrate muss einer von {', '.join(map(str, BITRATES))} sein")
        elif a == "--keep-unison":
            opts.merge_unison = False
        elif a == "--no-accompaniment":
            opts.accompaniment = False
        elif a.startswith("--mscore="):
            opts.mscore = a.split("=", 1)[1]
        elif a.startswith("--sampler="):
            sampler = Path(a.split("=", 1)[1])
    for m in missing_requirements(opts.mscore, sampler):
        print(f"Warnung: {m}", file=sys.stderr)
    if "--dry-run" in sys.argv:
        with tempfile.TemporaryDirectory() as td:
            jobs = [{"in": j["in"], "out": j["out"]} for s in scores for j in plan(s, Path(td), opts)]
        print(json.dumps(jobs, indent=2, ensure_ascii=False)); return
    last = [None]

    def progress(text, done, total):
        if text != last[0]:
            print(f"{text} ..."); last[0] = text

    for r in export(scores, opts, progress):
        level = "" if r.peak_db is None else f"Peak {r.peak_db:6.1f} dBFS  Gain {r.gain:+5.1f} dB  "
        print(f"{'OK ' if r.ok else '?? '}{level}{r.out.name}")


if __name__ == "__main__":
    main()
