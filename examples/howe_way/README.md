# Howe–Way as a derived MEI score

Keep the original MEI as the editable score. This Python 3.9+ example generates a separate display copy for Verovio. It uses existing MEI attributes for staff lines, visibility, staff location, notehead shape and stems. The C++ chord fix on this branch applies equally to conventional MEI with explicit staff locations.

From the repository root, with the Verovio CLI on the path:

```sh
python3 examples/howe_way/project.py examples/howe_way/piano.mei /tmp/piano-display.mei --reference 1=4 --reference 2=2
verovio -r data -o /tmp/piano.svg /tmp/piano-display.mei
python3 examples/howe_way/check_projection.py "$(command -v verovio)"
python3 doc/tests/chord/check_locations.py "$(command -v verovio)"
```

Each staff reference sets the octave of C on the bottom line (default 4). Given the semitone distance from that C, floor division by two gives the staff location. Even distances select the hollow head and odd distances select the filled head. A4 below a C5 reference, for example, is at location −2 with a filled head. The design follows the [Music Notation Project's description of Hilbert A. Howe's notation](https://musicnotation.org/wiki/notation-systems/howe-way-music-notationby-hilbert-howe/).

## Supported input

Use one measured CMN score with pitched five-line staves, explicit note or chord durations, and identified notes if SVG lookup is needed. Notes retain their IDs, pitch names and octaves. The example handles plain notes, chords, rests, spaces, full-measure rests, beams, augmentation dots, common sharp/flat key signatures and per-staff reference octaves. Within each measure of each staff, layers share accidental carry in rhythmic order. Simultaneous notes read the incoming context together. Conflicting explicit signs require a fresh sign or gestural accidental on a subsequent affected note. The logical staff supplies the pitch context and the destination staff supplies the display reference.

Written accidentals are represented as gestural values in the display copy to suppress the glyph. Existing gestural values are retained. The source remains authoritative for editorial spellings and accidental display. Encoded performance overrides such as MIDI pitch numbers do not move the written head. The fixture checks equality of Verovio's two MIDI exports, which compares what this renderer plays for each encoding.

## Limits

The projector is a working example for the documented subset. Ties across barlines, transposition, tuplets, grace notes, editorial alternatives, microtones and arbitrary MEI scores need separate handling. Use simple key signatures on score or staff definitions, or a simple keySig change in a layer. Whole notes still need the split stem and the third line from the top still needs its heavier stroke. Dense chords containing two coincident pairs on adjacent staff locations can need additional head columns and revised stem attachment. These features remain outside the generic chord-grouping change.
