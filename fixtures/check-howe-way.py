#!/usr/bin/env python3
"""Run from any directory: python3 fixtures/check-howe-way.py /path/to/verovio."""
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CLI = Path(sys.argv.pop(1)).resolve()
XLINK = "{http://www.w3.org/1999/xlink}href"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
HOLLOW, FILLED = "E0A3", "E0A4"


def group(element, label):
    return element.find(f".//{{*}}g[@class='{label}']")


def segment(path):
    return tuple(map(int, re.fullmatch(r"M(-?\d+) (-?\d+) L(-?\d+) (-?\d+)", path.get("d")).groups()))


class Render:
    def __init__(self, source, directory):
        output = directory / (source.stem + ".svg")
        subprocess.run([str(CLI), "-r", str(ROOT / "data"), "--xml-id-seed", "1",
                        "-o", str(output), str(source)], check=True, capture_output=True)
        self.root = ET.parse(output).getroot()
        self.ids = {e.get("id"): e for e in self.root.iter() if "id" in e.attrib}

    def head(self, note):
        use = group(self.ids[note], "notehead").find("{*}use")
        x, y = map(int, re.match(r"translate\((-?\d+), (-?\d+)\)", use.get("transform")).groups())
        return x, y, use.get(XLINK)[1:].split("-")[0]

    def lines(self):
        return group(self.root, "staff").findall("{*}path")


class HoweWayTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(tmp.cleanup)
        cls.chromatic, cls.traditional, cls.chords, cls.rhythm = [
            Render(ROOT / name, Path(tmp.name)) for name in (
                "howe-way.mei", "traditional.mei", "fixtures/howe-way-chords.mei", "fixtures/howe-way-rhythm.mei")]
        lines = cls.chromatic.lines()
        cls.unit = (segment(lines[1])[1] - segment(lines[0])[1]) // 2

    def test_scale_and_staff(self):
        lines = self.chromatic.lines()
        self.assertEqual(len(lines), 6)
        widths = [int(line.get("stroke-width")) for line in lines]
        self.assertGreater(widths[2], widths[0])
        for i in range(12):
            _, y, head = self.chromatic.head(f"n{i:02}")
            self.assertEqual(y, segment(lines[-1])[1] - (i // 2) * self.unit)
            self.assertEqual(head, (HOLLOW, FILLED)[i % 2])

    def test_accidentals_and_clef(self):
        for render in (self.chromatic, self.chords, self.rhythm):
            for label in ("accid", "clef", "keySig"):
                self.assertFalse(render.root.findall(f".//{{*}}g[@class='{label}']//{{*}}use"))

    def test_chords_and_voices(self):
        for a, b, steps in (("pair_c", "pair_cs", 0), ("pair_e", "pair_f", 0), ("adj_c", "adj_d", 1),
                            ("tri_e", "tri_g", 1), ("oct_b", "oct_c", 1), ("voice_c", "voice_cs", 0)):
            with self.subTest(pair=(a, b)):
                x1, y1, head1 = self.chords.head("hw_" + a)
                x2, y2, head2 = self.chords.head("hw_" + b)
                self.assertEqual(y1 - y2, steps * self.unit)
                self.assertGreaterEqual(abs(x1 - x2), 2 * self.unit)
                if steps == 0:
                    self.assertEqual((head1, head2), (HOLLOW, FILLED))
        self.assertEqual(self.chords.head("hw_tri_c")[0], self.chords.head("hw_tri_e")[0])
        self.assertEqual(self.chords.head("hw_enh_cs")[1:], self.chords.head("hw_enh_db")[1:])

    def test_adjacent_semitone_pairs(self):
        for direction in ("up", "down"):
            heads = [self.chords.head(f"dense-{direction}-{name}") for name in ("c", "cs", "d", "ds")]
            self.assertEqual([h[2] for h in heads], [HOLLOW, FILLED, HOLLOW, FILLED])
            for i, (x, y, _) in enumerate(heads):
                for j in range(i):
                    self.assertEqual(heads[j][1] - y, (i // 2 - j // 2) * self.unit)
                    self.assertGreaterEqual(abs(x - heads[j][0]), 2 * self.unit)

    def test_wholes_and_ledgers(self):
        for stem_id, head_ids, direction in (("whole-low", ["whole-low"], "below"),
                                             ("whole-high", ["whole-high"], "above"),
                                             ("whole-chord", ["whole-root", "whole-third", "whole-fifth"], None)):
            with self.subTest(stem=stem_id):
                stem = group(self.rhythm.ids[stem_id], "stem")
                self.assertIsNotNone(stem)
                x1, y1, x2, y2 = segment(stem.find("{*}path"))
                self.assertEqual(x1, x2)
                ys = [self.rhythm.head(note)[1] for note in head_ids]
                self.assertGreater(min(ys) - min(y1, y2), 0)
                self.assertEqual(min(ys) - min(y1, y2), max(y1, y2) - max(ys))
                if direction:
                    staff = next(s for s in self.rhythm.root.iter() if s.get("class") == "staff"
                                 and s.find(f".//*[@id='{stem_id}']") is not None)
                    ledger = group(staff, "ledgerLines " + direction).find("{*}path")
                    left, y, right, _ = segment(ledger)
                    self.assertEqual(y, ys[0])
                    self.assertLess(left, self.rhythm.head(stem_id)[0])
                    self.assertGreater(right, self.rhythm.head(stem_id)[0])
        self.assertEqual(self.rhythm.head("whole-low")[2], FILLED)
        self.assertEqual(self.rhythm.head("whole-high")[2], FILLED)

    def test_halves_and_short_values(self):
        self.assertEqual(self.rhythm.head("key-fs")[1:], self.rhythm.head("key-gf")[1:])
        self.assertEqual(self.rhythm.head("key-fs")[2], HOLLOW)
        for name, glyph in (("half-c", HOLLOW), ("half-f", FILLED)):
            self.assertEqual(self.rhythm.head(name)[2], glyph)
            self.assertIsNone(group(self.rhythm.ids[name], "stem"))
        self.assertEqual(self.rhythm.head("written")[1:], self.rhythm.head("half-c")[1:])
        for name, glyph in (("dotted", HOLLOW), ("flagged", HOLLOW), ("beam-a", FILLED), ("beam-b", HOLLOW)):
            self.assertEqual(self.rhythm.head(name)[2], glyph)
            self.assertIsNotNone(group(self.rhythm.ids[name], "stem"))
        self.assertIsNotNone(group(self.rhythm.ids["flagged"], "flag"))
        self.assertIsNotNone(group(self.rhythm.ids["dotted"], "dots"))
        self.assertIsNotNone(group(self.rhythm.root, "beam").find("{*}polygon"))

    def test_semantic_pitch_and_ids(self):
        # Rendering may suppress accidental ink, but interchange and playback retain the alteration.
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            for name in ("howe-way-chords", "howe-way-rhythm"):
                source = ROOT / "fixtures" / (name + ".mei")
                control = directory / "control.mei"
                control.write_text(source.read_text().replace('type="howe-way"', 'type="control"'))
                for file in (source, control):
                    subprocess.run([str(CLI), "-r", str(ROOT / "data"), "-t", "midi", "-o",
                                    str(directory / (file.stem + ".mid")), str(file)], check=True, capture_output=True)
                midi = (directory / (name + ".mid")).read_bytes()
                self.assertTrue(midi.startswith(b"MThd"))
                self.assertEqual(midi, (directory / "control.mid").read_bytes())

                exported = directory / "export.mei"
                subprocess.run([str(CLI), "-r", str(ROOT / "data"), "-t", "mei", "-o", str(exported),
                                str(source)], check=True, capture_output=True)

                def pitches(file):
                    result = {}
                    for note in ET.parse(file).iterfind(".//{*}note"):
                        accidental = note.find("{*}accid")
                        alteration = note.get("accid") if accidental is None else accidental.get("accid")
                        gestural = note.get("accid.ges") if accidental is None else accidental.get("accid.ges")
                        result[note.get(XML_ID)] = (note.get("pname"), note.get("oct"), note.get("pnum"),
                                                    alteration, gestural)
                    return result

                self.assertEqual(pitches(source), pitches(exported))
                render = self.chords if name.endswith("chords") else self.rhythm
                self.assertEqual(set(pitches(source)), {key for key, e in render.ids.items() if e.get("class") == "note"})

    def test_traditional(self):
        self.assertEqual(len(self.traditional.lines()), 5)
        self.assertTrue(self.traditional.root.findall(".//{*}g[@class='accid']/{*}use"))
        for i in range(12):
            self.assertEqual(self.traditional.head(f"n{i:02}")[2], FILLED)


if __name__ == "__main__":
    unittest.main()
