#!/usr/bin/env python3
"""Check presence of MEI note IDs in a generated Verovio SVG (not appearance)."""
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

if len(sys.argv) != 2:
    raise SystemExit('Usage: check-chord-svg.py /tmp/howe-way-chords.svg')
root = ET.parse(sys.argv[1]).getroot()
ids = {el.attrib.get('id') for el in root.iter()}
expected = {
    'hw_pair_c', 'hw_pair_cs', 'hw_pair_e', 'hw_pair_f',
    'hw_adj_c', 'hw_adj_d', 'hw_tri_c', 'hw_tri_e', 'hw_tri_g',
    'hw_oct_b', 'hw_oct_c', 'hw_enh_cs', 'hw_enh_db',
    'hw_voice_c', 'hw_voice_cs',
}
missing = sorted(expected - ids)
print(f'IDs present: {len(expected) - len(missing)}/{len(expected)}')
if missing:
    print('Missing:', ', '.join(missing))
    raise SystemExit(1)
print('All expected IDs present; graphic layout still requires inspection.')
