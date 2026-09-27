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
