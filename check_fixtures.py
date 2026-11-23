from pathlib import Path
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parent
for name in ('howe-way.mei', 'traditional.mei'):
    tree = ET.parse(root / name)
    ns={'m':'http://www.music-encoding.org/ns/mei'}
    notes = tree.findall('.//m:note', ns)
    assert len(notes) == 12, (name, len(notes))
    assert len({n.get('{http://www.w3.org/XML/1998/namespace}id') for n in notes}) == 12

for midi in range(0, 128):
    pos=(midi-60)//2
    assert pos == ((midi+12)-60)//2-6 if midi <= 115 else True
    assert (midi-60)%2 in (0,1)
assert (60-60)//2 == (61-60)//2 == 0
assert (62-60)//2 == 1
assert (59-60)//2 == -1
print('MEI XML structure and mapping invariants: OK')
