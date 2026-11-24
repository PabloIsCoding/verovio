"""Render the conventional and projected piano fixture and compare their geometry and playback."""
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET

from project import Q, project

folder = Path(__file__).resolve().parent
source = folder / "piano.mei"
score = ET.parse(source).getroot()
original = ET.tostring(score)
derived = project(score, {"2": 2})
assert ET.tostring(score) == original
xml_id = "{http://www.w3.org/XML/1998/namespace}id"
ids = {note.attrib[xml_id] for note in score.iter(Q + "note")}
assert {note.attrib[xml_id] for note in derived.iter(Q + "note")} == ids

with tempfile.TemporaryDirectory() as directory:
    tmp = Path(directory)
    display = tmp / "display.mei"
    ET.ElementTree(derived).write(display, encoding="utf-8", xml_declaration=True)
    for file in (source, display):
        for fmt, suffix in (("svg", "svg"), ("midi", "mid")):
            subprocess.run([sys.argv[1], "-r", str(folder.parents[1] / "data"), "-t", fmt,
                            "-o", str(tmp / f"{file.stem}.{suffix}"), str(file)], check=True)
        svg = ET.parse(tmp / f"{file.stem}.svg")
        notes = {g.attrib["id"]: g for g in svg.findall(".//{*}g[@class='note']")}
        assert set(notes) == ids
    assert (tmp / "display.mid").read_bytes() == (tmp / "piano.mid").read_bytes()

positions = {}
glyphs = {}
for name, note in notes.items():
    use = note.find("./{*}g[@class='notehead']/{*}use")
    positions[name] = tuple(map(int, re.match(r"translate\((-?\d+), (-?\d+)\)", use.attrib["transform"]).groups()))
    glyphs[name] = use.attrib["{http://www.w3.org/1999/xlink}href"][1:5]

for staff in svg.findall(".//{*}g[@class='staff']"):
    assert len(staff.findall("./{*}path")) == 6
for kind in ("clef", "keySig", "accid"):
    assert not svg.findall(f".//{{*}}g[@class='{kind}']//{{*}}use")
assert svg.findall(".//{*}g[@class='ledgerLines above']/{*}path")
assert notes["voice-f"].find(".//{*}g[@class='stem']/{*}path") is None
for name in ("natural-f", "short-c"):
    assert notes[name].find(".//{*}g[@class='stem']/{*}path") is not None
assert notes["short-c"].find(".//{*}g[@class='flag']/{*}use") is not None
for name in ("key-f", "reset-f", "sharp-f", "other-staff-f", "bass-whole"):
    assert glyphs[name] == "E0A3", name
for name in ("natural-f", "carry-f", "voice-f", "changed-key-f", "other-octave-f"):
    assert glyphs[name] == "E0A4", name
assert positions["natural-f"][1] == positions["carry-f"][1] == positions["voice-f"][1]
assert positions["key-f"][1] == positions["reset-f"][1] < positions["natural-f"][1]
dx = abs(positions["tri-e"][0] - positions["tri-g"][0])
step = positions["tri-e"][1] - positions["tri-g"][1]
assert step > 0 and dx >= 2 * step
assert positions["pair-d"][1] == positions["pair-ef"][1] == positions["enh-ds"][1]
assert abs(positions["pair-d"][0] - positions["pair-ef"][0]) >= 2 * step
assert glyphs["pair-d"] == "E0A3" and glyphs["pair-ef"] == glyphs["enh-ds"] == "E0A4"
print("Piano projection geometry, note IDs and byte-identical MIDI passed.")
