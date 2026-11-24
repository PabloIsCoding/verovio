"""Derive a six-line Howe-Way display copy from measured, pitched CMN MEI."""
import argparse
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from xml.etree import ElementTree as ET

NS = "http://www.music-encoding.org/ns/mei"
Q = "{" + NS + "}"
ET.register_namespace("", NS)
NATURAL = dict(zip("cdefgab", (0, 2, 4, 5, 7, 9, 11)))
ALTER = {"n": 0, "s": 1, "f": -1, "ss": 2, "x": 2, "ff": -2}


def key_alterations(sig):
    if sig == "0":
        return {}
    if len(sig) != 2 or sig[0] not in "1234567" or sig[1] not in "sf":
        raise ValueError(f"Unsupported key signature {sig!r}")
    order = "fcgdaeb" if sig[1] == "s" else "beadgcf"
    return dict.fromkeys(order[:int(sig[0])], ALTER[sig[1]])


def events(layer):
    """Collect exact onsets before combining voices. A chord advances time once."""
    onset = Fraction()

    def visit(parent):
        nonlocal onset
        for event in parent:
            tag = event.tag.removeprefix(Q)
            if tag == "beam":
                yield from visit(event)
            elif tag == "keySig":
                yield onset, event
            elif tag in ("note", "chord", "rest", "space"):
                if "grace" in event.attrib or "tstamp" in event.attrib:
                    raise ValueError("Grace notes and explicit timestamps are outside this demo")
                dur = int(event.attrib["dur"])
                dots = int(event.get("dots", "0"))
                if dur <= 0 or dots < 0:
                    raise ValueError("Expected a positive duration and nonnegative dots")
                yield onset, event
                onset += (2 - Fraction(1, 2**dots)) / dur
            elif tag == "mRest" and len(parent) == 1:
                continue
            else:
                raise ValueError(f"Unsupported layer event {tag!r}")

    yield from visit(layer)


def project(source, reference_octaves=None):
    """Return a new MEI root. Keys in reference_octaves are MEI staff numbers."""
    refs = {str(k): v for k, v in (reference_octaves or {}).items()}
    if any(type(v) is not int or not 0 <= v <= 9 for v in refs.values()):
        raise ValueError("Reference octaves must be integers from 0 to 9")
    root = deepcopy(source)
    scores = list(root.iter(Q + "score"))
    if len(scores) != 1:
        raise ValueError("Expected one measured score")
    keys = {}
    for element in scores[0].iter():
        if element.tag == Q + "scoreDef":
            if element.find(".//" + Q + "keySig") is not None:
                raise ValueError("Use @keysig for key signatures inside a score definition")
            if "keysig" in element.attrib:
                for n in keys:
                    keys[n] = key_alterations(element.attrib["keysig"])
                element.set("keysig.visible", "false")
            for staff in element.iter(Q + "staffDef"):
                n = staff.attrib["n"]
                if staff.get("lines", "5") != "5" or staff.get("notationtype", "cmn") != "cmn" or staff.get("clef.shape") in ("perc", "TAB"):
                    raise ValueError(f"Expected a pitched five-line staff at staff {n}")
                if "keysig" in staff.attrib:
                    keys[n] = key_alterations(staff.attrib["keysig"])
                elif n not in keys:
                    keys[n] = key_alterations(element.get("keysig", "0"))
                staff.set("lines", "6")
                staff.set("clef.visible", "false")
                if "keysig" in staff.attrib:
                    staff.set("keysig.visible", "false")
        elif element.tag == Q + "clef":
            element.set("visible", "false")
        elif element.tag == Q + "staff":
            n = element.attrib["n"]
            by_time = defaultdict(list)
            for layer in element.findall(Q + "layer"):
                for time, event in events(layer):
                    by_time[time].append(event)
            carry = {}
            for time in sorted(by_time):
                changes = defaultdict(set)
                for event in by_time[time]:
                    if event.tag == Q + "keySig":
                        keys[n] = key_alterations(event.attrib["sig"])
                        event.set("visible", "false")
                        carry.clear()
                for event in by_time[time]:
                    if event.tag not in (Q + "note", Q + "chord"):
                        continue
                    if event.get("dur") == "2":
                        event.set("stem.visible", "false")
                    for note in event.iter(Q + "note"):
                        pname, octave = note.attrib["pname"], int(note.attrib["oct"])
                        target = note.get("staff", event.get("staff", n))
                        if target not in keys:
                            raise ValueError(f"Unknown or multiple display staves: {target}")
                        accidental = note.find(Q + "accid")
                        if accidental is not None and ("accid" in note.attrib or "accid.ges" in note.attrib):
                            raise ValueError("Split child and attribute accidentals are outside this demo")
                        sign = accidental if accidental is not None else note
                        written, gestural = sign.get("accid"), sign.get("accid.ges")
                        alteration = carry.get((pname, octave), keys[n].get(pname, 0))
                        if written:
                            alteration = ALTER[written]
                            changes[pname, octave].add(alteration)
                            # Keep pitch for playback while suppressing the traditional glyph.
                            sign.set("accid.ges", gestural or ("ss" if written == "x" else written))
                            del sign.attrib["accid"]
                        elif gestural:
                            alteration = ALTER[gestural]
                        if alteration is None:
                            raise ValueError(f"Ambiguous accidental carry at {pname}{octave} on staff {n}")
                        pitch = 12 * (octave - refs.get(target, 4)) + NATURAL[pname] + alteration
                        note.set("loc", str(pitch // 2))
                        note.set("head.shape", "quarter" if pitch % 2 else "half")
                for key, signs in changes.items():
                    carry[key] = next(iter(signs)) if len(signs) == 1 else None
    if refs.keys() - keys.keys():
        raise ValueError("Reference supplied for an unknown staff")
    return root


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--reference", metavar="STAFF=OCTAVE", action="append", default=[])
    args = parser.parse_args()
    if args.source.resolve() == args.output.resolve():
        parser.error("Choose a separate output file for the projected score")
    refs = dict(arg.split("=", 1) for arg in args.reference)
    score = project(ET.parse(args.source).getroot(), {k: int(v) for k, v in refs.items()})
    ET.ElementTree(score).write(args.output, encoding="utf-8", xml_declaration=True)
