"""Tests für die Logik ohne MuseScore: Partituren werden als kleine ZIPs nachgebaut."""
import array
import json
import struct
import zipfile
from pathlib import Path

import pytest

from partfocus import core

MSCX_MS4 = """<?xml version="1.0" encoding="UTF-8"?>
<museScore version="4.70"><Score>
  <Part id="1"><Instrument id="soprano"><longName>Sopran 1</longName></Instrument></Part>
  <Part id="2"><Instrument id="alto"><longName>Alt</longName></Instrument></Part>
  <Part id="3"><Instrument id="piano"><longName>Klavier</longName></Instrument></Part>
  <Staff id="1"><Measure>
    <Dynamic>
      <subtype>pp</subtype>
      <velocity>33</velocity>
      </Dynamic>
    <Spanner type="HairPin">
      <HairPin><subtype>0</subtype></HairPin>
      <next><location><measures>2</measures></location></next>
      </Spanner>
    <Dynamic>
      <subtype>ff</subtype>
      <velocity>112</velocity>
      </Dynamic>
    <Spanner type="HairPin">
      <prev><location><measures>-2</measures></location></prev>
      </Spanner>
  </Measure></Staff>
</Score></museScore>
"""

MSCX_MS3 = """<?xml version="1.0" encoding="UTF-8"?>
<museScore version="3.01"><Score>
  <Part><Instrument><longName>Soprano</longName></Instrument></Part>
  <Part><Instrument><longName>Bass</longName></Instrument></Part>
</Score></museScore>
"""


def _track(pid, iid, uid="1"):
    return {"partId": pid, "instrumentId": iid,
            "in": {"resourceMeta": {"id": uid, "type": "fluid_soundfont"}},
            "out": {"volumeDb": 0, "balance": 0, "fxChain": {}, "auxSends": []},
            "soloMuteState": {"mute": True, "solo": False}}


def make_score(path: Path, mscx: str, audio: dict | None) -> Path:
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(f"{path.stem}.mscx", mscx)
        z.writestr("META-INF/container.xml", "<container/>")
        if audio is not None:
            z.writestr("audiosettings.json", json.dumps(audio))
    return path


@pytest.fixture
def ms4(tmp_path):
    audio = {"activeSoundProfile": "MuseSounds", "aux": [], "master": {"volumeDb": 0},
             "tracks": [_track("999", "metronome"), _track("1", "soprano"),
                        _track("2", "alto"), _track("3", "piano")]}
    return make_score(tmp_path / "Lied.mscz", MSCX_MS4, audio)


@pytest.fixture
def ms3(tmp_path):
    return make_score(tmp_path / "Alt.mscz", MSCX_MS3, None)


def read_variant(path: Path) -> tuple[dict, str]:
    with zipfile.ZipFile(path) as z:
        mscx = next(n for n in z.namelist() if n.endswith(".mscx"))
        return json.loads(z.read("audiosettings.json")), z.read(mscx).decode()


# --- Dynamik ---------------------------------------------------------------

def test_flatten_dynamics_sets_one_level_and_drops_hairpins():
    flat = core.flatten_dynamics(MSCX_MS4, "mf")
    assert flat.count("<subtype>mf</subtype>") == 2
    assert flat.count("<velocity>80</velocity>") == 2
    assert "HairPin" not in flat
    assert "<subtype>pp</subtype>" not in flat


def test_flatten_dynamics_keeps_xml_valid():
    import xml.etree.ElementTree as ET

    ET.fromstring(core.flatten_dynamics(MSCX_MS4, "p"))


# --- Tempo -----------------------------------------------------------------

MSCX_TEMPO = """<museScore version="4.70"><Score>
  <Staff id="1">
    <Measure><voice>
      <TimeSig><sigN>3</sigN><sigD>4</sigD></TimeSig>
      <Tempo><tempo>2</tempo><text>= 120</text></Tempo>
      <Rest><durationType>measure</durationType></Rest>
      </voice></Measure>
    <Measure><voice>
      <Tempo><tempo>0.833333</tempo><text>= 50</text></Tempo>
      <Chord><durationType>quarter</durationType></Chord>
      </voice></Measure>
  </Staff>
</Score></museScore>
"""


def test_slow_tempo_scales_every_tempo_marking():
    slow = core.slow_tempo(MSCX_TEMPO, 80)
    assert "<tempo>1.6</tempo>" in slow
    assert "<tempo>0.666666</tempo>" in slow  # 0.833333 * 0.8
    assert slow.count("<Tempo>") == 2


def test_slow_tempo_adds_hidden_marking_when_score_starts_without_one():
    import xml.etree.ElementTree as ET

    mscx = MSCX_TEMPO.replace("<Tempo><tempo>2</tempo><text>= 120</text></Tempo>", "")
    slow = core.slow_tempo(mscx, 80)
    first = ET.fromstring(slow).find(".//Measure/voice")
    tempo = first.find("Tempo")
    assert float(tempo.findtext("tempo")) == pytest.approx(1.6)  # 120 BPM ist der MuseScore-Standard
    assert tempo.findtext("visible") == "0"
    assert [e.tag for e in first].index("Tempo") < [e.tag for e in first].index("Rest")


def test_slow_tempo_keeps_full_speed_untouched():
    assert core.slow_tempo(MSCX_TEMPO, 100) == MSCX_TEMPO


# --- Stimmen ---------------------------------------------------------------

def test_voices_skip_metronome_and_start_with_gesamt(ms4):
    assert core.voices(ms4) == [("Gesamt", None), ("Sopran 1", "1"), ("Alt", "2"), ("Klavier", "3")]


def test_ms3_score_numbers_parts_like_musescore4(ms3):
    assert core.voices(ms3) == [("Gesamt", None), ("Soprano", "1"), ("Bass", "2")]


def test_load_audio_builds_tracks_when_empty(tmp_path):
    audio = {"master": {"volumeDb": 0}, "tracks": []}
    score = make_score(tmp_path / "Neu.mscz", MSCX_MS4, audio)
    with zipfile.ZipFile(score) as z:
        tracks = core.load_audio(z)["tracks"]
    assert [(t["partId"], t["instrumentId"]) for t in tracks] == [("1", "soprano"), ("2", "alto"), ("3", "piano")]
    assert all("in" not in t for t in tracks)  # MuseScore wählt den Klang selbst


def test_load_audio_is_none_for_ms3(ms3):
    with zipfile.ZipFile(ms3) as z:
        assert core.load_audio(z) is None


# --- Varianten -------------------------------------------------------------

def test_write_variant_sets_levels_and_master(ms4, tmp_path):
    with zipfile.ZipFile(ms4) as z:
        audio = core.load_audio(z)
    opts = core.Options(others_db=-30, flat_dynamic="mf")
    dst = tmp_path / "v.mscz"
    core.write_variant(ms4, dst, audio, "2", opts, master_db=4.5)
    a, mscx = read_variant(dst)
    vols = {t["partId"]: t["out"]["volumeDb"] for t in a["tracks"]}
    assert vols == {"999": 0, "1": -30, "2": 0.0, "3": -30}
    assert a["master"]["volumeDb"] == 4.5
    assert all(not t["soloMuteState"]["mute"] for t in a["tracks"] if t["partId"] != "999")
    assert "HairPin" not in mscx


def test_write_variant_keeps_dynamics_when_asked(ms4, tmp_path):
    with zipfile.ZipFile(ms4) as z:
        audio = core.load_audio(z)
    dst = tmp_path / "v.mscz"
    core.write_variant(ms4, dst, audio, None, core.Options(flat_dynamic=None))
    assert "<subtype>pp</subtype>" in read_variant(dst)[1]


def test_write_variant_slows_tempo(tmp_path):
    audio = {"master": {"volumeDb": 0}, "tracks": []}
    score = make_score(tmp_path / "T.mscz", MSCX_TEMPO, audio)
    dst = tmp_path / "v.mscz"
    core.write_variant(score, dst, audio, None, core.Options(), tempo=70)
    assert "<tempo>1.4</tempo>" in read_variant(dst)[1]


# --- Unisono ---------------------------------------------------------------

def _chord(pitch, dur="quarter", tie="", extra=""):
    return (f"<Chord>{extra}<durationType>{dur}</durationType>"
            f"<Note>{tie}<pitch>{pitch}</pitch><tpc>14</tpc></Note></Chord>")


TIE_NEXT = '<Spanner type="Tie"><Tie/><next><location><fractions>1/2</fractions></location></next></Spanner>'
TIE_PREV = '<Spanner type="Tie"><prev><location><fractions>-1/2</fractions></location></prev></Spanner>'


def _unison_score(*staves):
    """Ein Part pro System; jedes System ist eine Liste von Takten, jeder Takt ein voice-Inhalt."""
    parts = "".join(f'<Part id="{i}"><Staff/><Instrument id="voice"/></Part>' for i in range(1, len(staves) + 1))
    body = "".join(f'<Staff id="{i}">' + "".join(f"<Measure><voice>{m}</voice></Measure>" for m in measures)
                   + "</Staff>" for i, measures in enumerate(staves, 1))
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<museScore version="4.70"><Score>' \
           f'<TimeSig><sigN>4</sigN><sigD>4</sigD></TimeSig>{parts}{body}</Score></museScore>\n'


def _muted(mscx):
    """Pro System die Tonhöhen der stummen Noten."""
    import xml.etree.ElementTree as ET
    root = ET.fromstring(mscx)
    return [[int(n.findtext("pitch")) for n in s.iter("Note") if n.findtext("play") == "0"]
            for s in root.find("Score").findall("Staff")]


def test_merge_unison_mutes_copies_in_lower_parts():
    m = _chord(60) + _chord(62) + _chord(64) + _chord(65)
    other = _chord(60) + _chord(67) + _chord(64) + _chord(69)
    # Part 3 verdoppelt auch Part 2 (67, 69), dort klingt nichts mehr.
    assert _muted(core.merge_unison(_unison_score([m], [other], [other]), None)) == [[], [60, 64], [60, 67, 64, 69]]


def test_merge_unison_keeps_the_target_part():
    m = _chord(60) + _chord(62) + _chord(64) + _chord(65)
    assert _muted(core.merge_unison(_unison_score([m], [m]), "2")) == [[60, 62, 64, 65], []]


def test_merge_unison_never_mutes_the_target():
    # Der obere Part hält den Ton länger und deckt die Zielstimme ab, trotzdem bleibt sie hörbar.
    top = _chord(60, "whole")
    target = _chord(60) + _chord(62) + _chord(64, "half")
    for staves in ([top], [target]), ([target], [top]):
        pid = "2" if staves[1] == [target] else "1"
        muted = _muted(core.merge_unison(_unison_score(*staves), pid))
        assert muted[int(pid) - 1] == []


def test_merge_unison_needs_same_onset_and_covering_length():
    # Oben halbe Note, unten Viertel auf demselben Ton: unten ist abgedeckt.
    # Unten halbe, oben Viertel: oben bleibt hörbar, unten auch, sonst bräche der Ton ab.
    top = _chord(60, "half") + _chord(62) + _chord(64)
    low = _chord(60) + _chord(60) + _chord(62, "half")
    assert _muted(core.merge_unison(_unison_score([top], [low]), None)) == [[], [60]]


def test_merge_unison_treats_tied_notes_as_one():
    tied = _chord(60, "half", TIE_NEXT) + _chord(60, "half", TIE_PREV)
    plain = _chord(60, "half") + _chord(60, "half")
    one_long = core.merge_unison(_unison_score([tied], [tied]), None)
    assert _muted(one_long) == [[], [60, 60]]
    # Ein langer Ton deckt zwei kurze ab, zwei kurze aber nicht den langen.
    assert _muted(core.merge_unison(_unison_score([tied], [plain]), None)) == [[], [60]]
    assert _muted(core.merge_unison(_unison_score([plain], [tied]), None)) == [[], []]


def test_merge_unison_counts_dots_tuplets_rests_and_measures():
    top = [_chord(60, "half", extra="<dots>1</dots>") + _chord(62),
           "<Tuplet><normalNotes>2</normalNotes><actualNotes>3</actualNotes></Tuplet>"
           + _chord(64, "eighth") * 3 + "<endTuplet/>" + "<Rest><durationType>quarter</durationType></Rest>"
           + _chord(65, "half")]
    low = [_chord(59, "half", extra="<dots>1</dots>") + _chord(62),
           _chord(64, "quarter") + "<location><fractions>1/4</fractions></location>" + _chord(65, "half")]
    assert _muted(core.merge_unison(_unison_score(top, low), None)) == [[], [62, 65]]


def test_merge_unison_ignores_grace_notes_and_silent_notes():
    grace = _chord(60, "eighth", extra="<acciaccatura/>")
    top = grace + _chord(62).replace("<Note>", "<Note><play>0</play>") + _chord(64, "half")
    low = grace + _chord(62) + _chord(64, "half")
    assert _muted(core.merge_unison(_unison_score([top], [low]), None)) == [[62], [64]]


def test_merge_unison_leaves_one_part_alone():
    m = _chord(60) + _chord(60)
    two_voices = f'<Measure><voice>{m}</voice><voice>{m}</voice></Measure>'
    mscx = _unison_score([m]).replace(f"<Measure><voice>{m}</voice></Measure>", two_voices)
    assert core.merge_unison(mscx, None) == mscx


def test_merge_unison_keeps_the_text_otherwise_unchanged():
    m = _chord(60) + _chord(62)
    mscx = _unison_score([m], [m])
    out = core.merge_unison(mscx, None)
    assert out.replace("<play>0</play>", "") == mscx


def test_write_variant_merges_unison_when_asked(tmp_path):
    m = _chord(60) + _chord(62)
    audio = {"master": {"volumeDb": 0}, "tracks": []}
    score = make_score(tmp_path / "U.mscz", _unison_score([m], [m]), audio)
    dst = tmp_path / "v.mscz"
    core.write_variant(score, dst, audio, "2", core.Options())
    assert _muted(read_variant(dst)[1]) == [[60, 62], []]
    core.write_variant(score, dst, audio, "2", core.Options(merge_unison=False))
    assert "<play>" not in read_variant(dst)[1]


# --- Bitrate ---------------------------------------------------------------

def test_render_passes_bitrate_to_musescore(tmp_path, monkeypatch):
    calls = []

    class Done:
        returncode = 0

        def __init__(self, cmd, **kwargs):
            calls.append(cmd)

        def poll(self):
            return 0

    monkeypatch.setattr(core.subprocess, "Popen", Done)
    core.render([{"in": "a.mscz", "out": str(tmp_path / "a.mp3")}], tmp_path / "job.json", core.Options(bitrate=96))
    assert calls[0][calls[0].index("-b") + 1] == "96"


def test_default_bitrate_is_selectable():
    assert core.Options().bitrate == 128 and core.Options().bitrate in core.BITRATES


# --- Begleitung ------------------------------------------------------------

def _backed_score(*staves, piano=1):
    """Wie _unison_score, die letzten `piano` Systeme gehören zu einem Klavier-Part (id "9")."""
    mscx = _unison_score(*staves)
    singers = len(staves) - piano
    parts = "".join(f'<Part id="{i}"><Staff/><Instrument id="voice"/></Part>' for i in range(1, len(staves) + 1))
    real = "".join(f'<Part id="{i}"><Staff/><Instrument id="soprano"><instrumentId>voice.soprano</instrumentId>'
                   f'</Instrument></Part>' for i in range(1, singers + 1))
    real += ('<Part id="9">' + "<Staff/>" * piano
             + '<Instrument id="piano"><instrumentId>keyboard.piano</instrumentId></Instrument></Part>')
    return mscx.replace(parts, real)


def test_accompaniment_needs_sung_parts_beside_it():
    assert core.staff_parts(_backed_score([""], [""], [""], piano=2)) == ["1", "9", "9"]
    import xml.etree.ElementTree as ET
    assert core._accompaniment(core._score_parts(ET.fromstring(_backed_score([""], [""])))) == {"9"}
    # Nur Instrumente: jedes bleibt eine eigene Stimme.
    assert core._accompaniment(core._score_parts(ET.fromstring(_unison_score([""], [""])))) == set()


def test_voices_leave_out_accompaniment(tmp_path):
    audio = {"master": {"volumeDb": 0}, "tracks": [_track("1", "soprano"), _track("2", "soprano"),
                                                   _track("9", "piano")]}
    score = make_score(tmp_path / "K.mscz", _backed_score([""], [""], [""]), audio)
    assert core.voices(score) == [("Gesamt", None), ("Part 1", "1"), ("Part 2", "2")]
    assert core.voices(make_score(tmp_path / "K3.mscz", _backed_score([""], [""]), None)) == \
        [("Gesamt", None), ("Part 1", "1")]


def test_merge_unison_leaves_accompaniment_alone():
    m = _chord(60) + _chord(62)
    # Das Klavier verdoppelt den Chor, stumm wird aber nur der untere Sänger.
    assert _muted(core.merge_unison(_backed_score([m], [m], [m]), None)) == [[], [60, 62], []]
    assert _muted(core.merge_unison(_backed_score([m], [m], [m]), "9")) == [[], [60, 62], []]


def test_mute_accompaniment_silences_every_piano_staff():
    m = _chord(60) + _chord(62)
    mscx = _backed_score([m], [m], [m], piano=2)
    assert _muted(core.mute_accompaniment(mscx)) == [[], [60, 62], [60, 62]]
    assert core.mute_accompaniment(_unison_score([m], [m])) == _unison_score([m], [m])


def test_write_variant_plays_accompaniment_quietly_or_not_at_all(tmp_path):
    m = _chord(60)
    audio = {"master": {"volumeDb": 0}, "tracks": [_track("1", "soprano"), _track("9", "piano")]}
    score = make_score(tmp_path / "K.mscz", _backed_score([m], [m]), audio)
    dst = tmp_path / "v.mscz"
    core.write_variant(score, dst, audio, "1", core.Options(others_db=-20))
    a, mscx = read_variant(dst)
    assert {t["partId"]: t["out"]["volumeDb"] for t in a["tracks"]} == {"1": 0.0, "9": -20}
    assert "<play>" not in mscx
    core.write_variant(score, dst, audio, "1", core.Options(accompaniment=False))
    assert _muted(read_variant(dst)[1]) == [[], [60]]


# --- Klang -----------------------------------------------------------------

@pytest.mark.parametrize("iid, name, expected", [
    ("soprano", "", "Sopranos"),
    ("voice", "Mezzosopran", "Sopranos"),
    ("", "Alt 2", "Altos"),
    ("tenor", "", "Tenors"),
    ("baritone", "", "Basses"),
    ("", "Bass", "Basses"),
    ("piano", "Klavier", None),
])
def test_choir_voice(iid, name, expected):
    res = core.choir_voice(iid, name)
    assert (res and res["resourceMeta"]["attributes"]["museName"]) == expected


def test_apply_sound(ms4):
    with zipfile.ZipFile(ms4) as z:
        audio, names = core.load_audio(z), core.part_names(z)
    choir = {t["partId"]: t["in"]["resourceMeta"]["id"] for t in core.apply_sound(audio, names, "choir")["tracks"]}
    assert choir == {"999": "1", "1": "19", "2": "20", "3": "1"}  # Metronom und Klavier bleiben
    piano = {t["partId"]: t["in"]["resourceMeta"]["id"] for t in core.apply_sound(audio, names, "piano")["tracks"]}
    assert piano == {"999": "1", "1": "167", "2": "167", "3": "167"}
    assert core.apply_sound(audio, names, "original") == audio


def test_plan_names_outputs_with_sound_suffix(ms4, tmp_path):
    jobs = core.plan(ms4, tmp_path, core.Options(sound="piano"))
    assert [Path(j["out"]).name for j in jobs][:2] == ["Lied - Gesamt (Grand Piano).mp3",
                                                      "Lied - Sopran 1 (Grand Piano).mp3"]
    assert Path(jobs[0]["out"]).parent == ms4.parent / "Lied"


def test_plan_adds_slower_versions(ms4, tmp_path):
    jobs = core.plan(ms4, tmp_path, core.Options(sound="choir", tempos=(100, 80, 60)))
    names = [Path(j["out"]).name for j in jobs]
    assert len(names) == 12 and len(set(names)) == 12
    assert len({j["in"] for j in jobs}) == 12
    assert names[0] == "Lied - Gesamt (Muse Choir).mp3"
    assert "Lied - Alt (Muse Choir) (80%).mp3" in names
    assert "Lied - Klavier (Muse Choir) (60%).mp3" in names
    assert sorted(j["tempo"] for j in jobs) == [60] * 4 + [80] * 4 + [100] * 4


# --- Pegel -----------------------------------------------------------------

def write_float_wav(path: Path, samples: list[float]) -> Path:
    data = array.array("f", samples).tobytes()
    fmt = struct.pack("<HHIIHH", 3, 2, 44100, 44100 * 8, 8, 32)
    body = b"WAVE" + b"fmt " + struct.pack("<I", len(fmt)) + fmt
    body += b"LIST" + struct.pack("<I", 3) + b"abc\0"  # ungerade Größe: Padding-Byte
    body += b"data" + struct.pack("<I", len(data)) + data
    path.write_bytes(b"RIFF" + struct.pack("<I", len(body)) + body)
    return path


def test_wav_peak_reads_float_wav(tmp_path):
    wav = write_float_wav(tmp_path / "x.wav", [0.1, -0.2, 1.75, -0.5])
    assert core.wav_peak(wav) == pytest.approx(1.75)


def test_wav_peak_negative_peak(tmp_path):
    wav = write_float_wav(tmp_path / "x.wav", [0.1, -0.9])
    assert core.wav_peak(wav) == pytest.approx(0.9)


def fake_render(calls):
    def render(jobs, jobfile, opts, tick=lambda n: None, cancelled=lambda: False):
        calls.append([Path(j["out"]).suffix for j in jobs])
        for j in jobs:
            out = Path(j["out"])
            if out.suffix == ".wav":
                write_float_wav(out, [0.25, -0.5])
            else:
                out.write_bytes(b"mp3")
    return render


def test_export_measures_peak_with_original_dynamics(ms4, monkeypatch):
    calls = []
    monkeypatch.setattr(core, "render", fake_render(calls))
    results = core.export([ms4], core.Options(flat_dynamic=None))
    assert calls == [[".wav"] * 4, [".mp3"] * 4]
    assert results[0].gain == pytest.approx(core.PEAK_DBFS + 6.0206, abs=1e-3)
    assert all(r.ok for r in results)


def test_export_skips_measuring_with_flat_dynamics(ms4, monkeypatch):
    calls = []
    monkeypatch.setattr(core, "render", fake_render(calls))
    results = core.export([ms4], core.Options(flat_dynamic="mf"))
    assert calls == [[".mp3"] * 4]
    assert all(r.ok and r.peak_db is None and r.gain == 0.0 for r in results)


def test_plan_without_full_speed(ms4, tmp_path):
    jobs = core.plan(ms4, tmp_path, core.Options(tempos=(70,)))
    assert [Path(j["out"]).name for j in jobs] == ["Lied - Gesamt (70%).mp3", "Lied - Sopran 1 (70%).mp3",
                                                   "Lied - Alt (70%).mp3", "Lied - Klavier (70%).mp3"]


def test_export_measures_only_fastest_tempo_and_reuses_gain(ms4, monkeypatch):
    calls = []
    monkeypatch.setattr(core, "render", fake_render(calls))
    results = core.export([ms4], core.Options(flat_dynamic=None, tempos=(80, 60)))
    assert calls == [[".wav"] * 4, [".mp3"] * 8]
    assert len({r.gain for r in results}) == 1 and results[0].gain != 0.0
    assert all(r.ok for r in results)


# --- MIDI ------------------------------------------------------------------

def write_midi(path: Path, tracks: int, velocity: int = 80) -> Path:
    """So wie MuseScore exportiert: eine Spur pro System, Note-Ende als note_on mit Velocity 0."""
    import mido
    mid = mido.MidiFile(ticks_per_beat=480)
    for ch in range(tracks):
        mid.tracks.append(mido.MidiTrack([
            mido.Message("control_change", channel=ch, control=7, value=100),
            mido.Message("note_on", channel=ch, note=60, velocity=velocity),
            mido.Message("note_on", channel=ch, note=60, velocity=0, time=480),
            mido.MetaMessage("end_of_track")]))
    mid.save(path)
    return path


def midi_velocities(path: Path) -> list[list[int]]:
    import mido
    return [[m.velocity for m in t if m.type == "note_on"] for t in mido.MidiFile(path).tracks]


def test_staff_parts_lists_part_per_staff():
    mscx = ('<museScore><Score><Part id="1"><Staff id="1"/><Staff id="2"/></Part>'
            '<Part id="7"><Staff id="3"/></Part></Score></museScore>')
    assert core.staff_parts(mscx) == ["1", "1", "7"]


def test_scale_midi_lowers_other_parts_only(tmp_path):
    mid = write_midi(tmp_path / "x.mid", 3)
    core.scale_midi(mid, ["1", "2", "2"], "1", -20.0)
    assert midi_velocities(mid) == [[80, 0], [8, 0], [8, 0]]


def test_scale_midi_keeps_quiet_notes_audible(tmp_path):
    mid = write_midi(tmp_path / "x.mid", 2, velocity=16)
    core.scale_midi(mid, ["1", "2"], "1", -40.0)
    assert midi_velocities(mid) == [[16, 0], [1, 0]]


def test_scale_midi_leaves_gesamt_untouched(tmp_path):
    mid = write_midi(tmp_path / "x.mid", 2)
    before = mid.read_bytes()
    core.scale_midi(mid, ["1", "2"], None, -20.0)
    assert mid.read_bytes() == before


def test_scale_midi_refuses_unexpected_track_count(tmp_path):
    mid = write_midi(tmp_path / "x.mid", 3)
    with pytest.raises(RuntimeError, match="3 Spuren"):
        core.scale_midi(mid, ["1", "2"], "1", -20.0)


@pytest.fixture
def choir(tmp_path):
    """Zwei Parts mit je einem System, wie MS4 sie schreibt."""
    mscx = _unison_score(["<Rest><durationType>measure</durationType></Rest>"] * 1,
                         ["<Rest><durationType>measure</durationType></Rest>"] * 1)
    audio = {"master": {"volumeDb": 0}, "tracks": [_track("1", "soprano"), _track("2", "alto")]}
    return make_score(tmp_path / "Chor.mscz", mscx, audio)


def test_plan_midi_names_outputs_without_sound(ms4, tmp_path):
    jobs = core.plan(ms4, tmp_path, core.Options(sound="choir", format="midi", tempos=(100, 80)))
    names = [Path(j["out"]).name for j in jobs]
    assert names[:2] == ["Lied - Gesamt.mid", "Lied - Sopran 1.mid"]
    assert "Lied - Alt (80%).mid" in names and len(names) == 8


def test_plan_both_formats_share_one_variant(ms4, tmp_path):
    jobs = core.plan(ms4, tmp_path, core.Options(sound="piano", format="both"))
    names = [Path(j["out"]).name for j in jobs]
    assert names[:2] == ["Lied - Gesamt (Grand Piano).mp3", "Lied - Gesamt.mid"]
    assert len(names) == 8 and len({j["in"] for j in jobs}) == 4


def fake_midi_render(calls, tracks):
    def render(jobs, jobfile, opts, tick=lambda n: None, cancelled=lambda: False):
        calls.append([Path(j["out"]).suffix for j in jobs])
        for j in jobs:
            out = Path(j["out"])
            if out.suffix == ".mid":
                write_midi(out, tracks)
            elif out.suffix == ".wav":
                write_float_wav(out, [0.25, -0.5])
            else:
                out.write_bytes(b"mp3")
    return render


def test_export_midi_skips_measuring_and_lowers_other_parts(choir, monkeypatch):
    calls = []
    monkeypatch.setattr(core, "render", fake_midi_render(calls, 2))
    results = core.export([choir], core.Options(format="midi", flat_dynamic=None, others_db=-20))
    assert calls == [[".mid"] * 3]
    assert [r.out.name for r in results] == ["Chor - Gesamt.mid", "Chor - Part 1.mid", "Chor - Part 2.mid"]
    assert [midi_velocities(r.out) for r in results] == [[[80, 0], [80, 0]], [[80, 0], [8, 0]],
                                                         [[8, 0], [80, 0]]]
    assert all(r.ok and r.peak_db is None for r in results)


def test_export_both_measures_mp3_only(choir, monkeypatch):
    calls = []
    monkeypatch.setattr(core, "render", fake_midi_render(calls, 2))
    results = core.export([choir], core.Options(format="both", flat_dynamic=None))
    # MuseScore stürzt ab, wenn ein Aufruf Audio und MIDI mischt: MIDI kommt getrennt.
    assert calls == [[".wav"] * 3, [".mp3"] * 3, [".mid"] * 3]
    assert [r.peak_db is None for r in results] == [False, True] * 3
    assert all(r.ok for r in results)


# --- Voraussetzungen ---------------------------------------------------------

def make_sampler(tmp_path: Path, packs=("Muse Choir", "Muse Keys")) -> Path:
    sampler, instruments = tmp_path / "MuseSampler", tmp_path / "Instruments"
    (sampler / "lib").mkdir(parents=True)
    (sampler / "lib" / "MuseSamplerCoreLib.dll").write_bytes(b"")
    (sampler / ".config").write_text(f"{instruments}\n", encoding="utf-8")
    for p in packs:
        (instruments / p).mkdir(parents=True)
    return sampler


@pytest.fixture
def mscore(tmp_path):
    exe = tmp_path / "MuseScore4.exe"
    exe.write_bytes(b"")
    return str(exe)


def test_requirements_all_present(tmp_path, mscore):
    assert core.missing_requirements(mscore, make_sampler(tmp_path)) == []


def test_requirements_missing_musescore(tmp_path):
    missing = core.missing_requirements(str(tmp_path / "nope.exe"), make_sampler(tmp_path))
    assert len(missing) == 1 and "MuseScore 4" in missing[0]


def test_requirements_missing_muse_sounds(tmp_path, mscore):
    missing = core.missing_requirements(mscore, tmp_path / "MuseSampler")
    assert len(missing) == 1 and "Muse Sounds" in missing[0]


def test_requirements_missing_instruments_folder(tmp_path, mscore):
    sampler = make_sampler(tmp_path)
    (sampler / ".config").unlink()
    assert "Instrumente" in core.missing_requirements(mscore, sampler)[0]


def test_requirements_missing_pack(tmp_path, mscore):
    missing = core.missing_requirements(mscore, make_sampler(tmp_path, packs=("Muse Keys",)))
    assert len(missing) == 1 and "Muse Choir" in missing[0]
