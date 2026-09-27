"""PartFocus: Übe-Tracks aus MuseScore-Partituren (.mscz) mit Muse Sounds.

Pro Stimme eine MP3 (Zielstimme 0 dB, Rest Options.others_db) plus "Gesamt" (alle gleich laut).
Dynamik wird eingeebnet: alle Dynamikzeichen -> Options.flat_dynamic, Gabeln entfernt.
Klang wählbar: Original, Muse Choir (Stimme nach Name/Instrument) oder Grand Piano für alle.
MuseScore-3-Dateien (ohne audiosettings.json) werden vorher mit MuseScore 4 umgewandelt.
Zwei Durchläufe: erst WAV zum Peak-Messen, dann MP3 mit Master-Gain auf PEAK_DBFS.
Aufruf:  partfocus-cli [datei.mscz | ordner] [--sound=original|choir|piano] [--dry-run]
         [--mscore=MuseScore4.exe] [--sampler=MuseSampler-Ordner]
Ausgabe: <ordner>/<stück>/<stück> - <Stimme>[ (<Klang>)].mp3
GUI:     partfocus
"""
import array, json, math, os, re, struct, subprocess, sys, tempfile, time, zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

MSCORE = r"C:\Program Files\MuseScore 4\bin\MuseScore4.exe"
TARGET_DB = 0.0
PEAK_DBFS = -1.0
MAX_GAIN_DB = 24.0
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
    bitrate: int = 192
    mscore: str = MSCORE


@dataclass
class Result:
    out: Path
    peak_db: float
    gain: float

    @property
    def ok(self) -> bool:
        return self.out.exists() and self.peak_db > -60


class Cancelled(Exception):
    pass


def _parts(z: zipfile.ZipFile):
    """(partId, Instrument-Element, Part-Element). MS3-Dateien haben keine IDs; MS4 nummeriert beim Umwandeln 1..N."""
    mscx = next(n for n in z.namelist() if n.endswith(".mscx") and "/" not in n)
    root = ET.fromstring(z.read(mscx))
    return [(p.get("id") or str(i), p.find("Instrument"), p) for i, p in enumerate(root.iter("Part"), 1)]


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


def write_variant(src: Path, dst: Path, audio: dict, target: str | None, opts: Options, master_db: float = 0.0):
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
            elif opts.flat_dynamic and item.filename.endswith(".mscx") and "/" not in item.filename:
                data = flatten_dynamics(data.decode("utf-8"), opts.flat_dynamic).encode("utf-8")
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
    """(Name, partId) pro Variante, beginnend mit ("Gesamt", None)."""
    with zipfile.ZipFile(score) as z:
        audio = load_audio(z)
        names = part_names(z)
    if audio is None:  # MS3: nach dem Umwandeln gibt es genau einen Track pro Part
        return [("Gesamt", None)] + [(n, pid) for pid, n in names.items()]
    track_ids = {t["partId"] for t in audio["tracks"] if t.get("instrumentId") != "metronome"}
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
    for label, pid in voices(source):
        v = tmp / f"{safe(score.stem)}__{safe(label)}.mscz"
        suffix = "" if opts.sound == "original" else f" ({SOUNDS[opts.sound]})"
        jobs.append({"in": str(v), "out": str(out_dir / f"{safe(score.stem)} - {safe(label)}{suffix}.mp3"),
                     "wav": str(v.with_suffix(".wav")), "score": source, "audio": audio, "pid": pid})
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
        total = 2 * len(jobs)
        for j in jobs:
            Path(j["out"]).parent.mkdir(exist_ok=True)
            write_variant(j["score"], Path(j["in"]), j["audio"], j["pid"], opts)
        jobfile = Path(td) / "job.json"
        progress(f"Pegel messen ({len(jobs)} Tracks)", 0, total)
        render([{"in": j["in"], "out": j["wav"]} for j in jobs], jobfile, opts,
               lambda n: progress(f"Pegel messen ({len(jobs)} Tracks)", n, total), cancelled)
        for j in jobs:
            peak = wav_peak(Path(j["wav"]))
            j["peak_db"] = 20 * math.log10(peak) if peak > 0 else -math.inf
            j["gain"] = min(MAX_GAIN_DB, PEAK_DBFS - j["peak_db"])
            write_variant(j["score"], Path(j["in"]), j["audio"], j["pid"], opts, j["gain"])
        progress("MP3s rendern", len(jobs), total)
        render([{"in": j["in"], "out": j["out"]} for j in jobs], jobfile, opts,
               lambda n: progress("MP3s rendern", len(jobs) + n, total), cancelled)
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
        print(f"{'OK ' if r.ok else '?? '}Peak {r.peak_db:6.1f} dBFS  Gain {r.gain:+5.1f} dB  {r.out.name}")


if __name__ == "__main__":
    main()
