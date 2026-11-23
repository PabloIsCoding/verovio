# Rendering a piano grand staff in Howe–Way

The input in `piano-pitch-context.mei` encodes conventional treble and bass staves. From the repository root, render the same file twice with the built CLI.

```sh
build/cli/verovio -r data -o piano.svg fixtures/piano-pitch-context.mei
build/cli/verovio -r data --notation-system howe-way \
    --howe-way-reference-octaves '{"1":4,"2":2}' \
    -o piano-howe-way.svg fixtures/piano-pitch-context.mei
```

The default `notationSystem` is `"encoded"`. The global `"howe-way"` option converts five-line CMN staves and excludes percussion and tablature clefs. A staff explicitly marked `type="howe-way"` still uses the experimental notation in encoded mode.

Each key in `howeWayReferenceOctaves` is an MEI staff number. Its integer value, 0 through 9, selects the octave of the bottom-line C. Unspecified staves use C4. The example uses C4 above and C2 below, so middle C on the lower staff sits on the first upper ledger line. Use the same options in the Toolkit and call `RedoLayout()` after changing options on a loaded document.

The renderer gives an explicit written accidental precedence. An encoded gestural accidental can specify the pitch of an individual note. Otherwise, written signs carry to later onsets on the same staff and octave until a barline or a change of key signature. Notes at the same onset read the incoming accidental state. This layout pass does not change MIDI or MEI. For reliable playback with this Verovio revision, encode implied alterations with `accid.ges` where needed.

Run the CLI checks with `python3 fixtures/check-howe-way.py build/cli/verovio`.
