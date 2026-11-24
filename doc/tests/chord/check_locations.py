"""Run with the path to a Verovio CLI binary."""
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET

fixture = Path(__file__).resolve().with_name("explicit-locations.mei")
with tempfile.TemporaryDirectory() as tmp:
    svg = Path(tmp) / "chords.svg"
    subprocess.run([sys.argv[1], "-r", str(fixture.parents[3] / "data"), "-o", str(svg), str(fixture)], check=True)
    root = ET.parse(svg)
    heads = {}
    for note in root.findall(".//{*}g[@class='note']"):
        use = note.find("./{*}g[@class='notehead']/{*}use")
        heads[note.get("id")] = tuple(map(int, re.match(r"translate\((-?\d+), (-?\d+)\)", use.get("transform")).groups()))

for direction in ("up", "down"):
    c, e, g = (heads[f"{direction}-{pitch}"] for pitch in "ceg")
    step = e[1] - g[1]
    assert step > 0 and c[1] - e[1] == 2 * step
    assert abs(e[0] - g[0]) >= 2 * step, (direction, e, g)
assert heads["pair-c"][1] == heads["pair-cs"][1]
assert abs(heads["pair-c"][0] - heads["pair-cs"][0]) >= 2 * step
assert heads["wide-c"][0] == heads["wide-d"][0]
print("Chord geometry passed for both stem directions, coincident heads, and widely spaced heads.")
