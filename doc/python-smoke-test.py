"""Minimal installed-wheel smoke test for the Python bindings.

This validates that the extension imports, packaged resource files are
discoverable, and a trivial render returns SVG on the active interpreter.
"""

import importlib.resources as resources
from pathlib import Path
from xml.etree import ElementTree as ET

import verovio


def run_smoke_test() -> None:
    toolkit = verovio.toolkit()
    print(toolkit.getVersion())
    toolkit.setResourcePath(str(resources.files("verovio") / "data"))
    toolkit.loadData(
        """<?xml version="1.0" encoding="UTF-8"?>
<mei xmlns="http://www.music-encoding.org/ns/mei" meiversion="5.1">
  <meiHead>
    <fileDesc>
      <titleStmt>
        <title>Verovio Python smoke test</title>
      </titleStmt>
      <pubStmt/>
    </fileDesc>
  </meiHead>
  <music>
    <body>
      <mdiv>
        <score>
          <scoreDef meter.count="4" meter.unit="4">
            <staffGrp>
              <staffDef n="1" lines="5" clef.shape="G" clef.line="2"/>
            </staffGrp>
          </scoreDef>
          <section>
            <measure n="1">
              <staff n="1">
                <layer n="1">
                  <note pname="c" oct="4" dur="4"/>
                </layer>
              </staff>
            </measure>
          </section>
        </score>
      </mdiv>
    </body>
  </music>
</mei>
"""
    )
    svg = toolkit.renderToSVG(1)
    assert "<svg" in svg, "renderToSVG did not return SVG output"


def check_notation_switch() -> None:
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "piano-pitch-context.mei"
    for breaks in ("auto", "none"):
        toolkit = verovio.toolkit()
        toolkit.setOptions({"breaks": breaks})
        assert toolkit.loadFile(str(fixture))
        initial_geometry = None
        for mode, lines in (("encoded", 5), ("howe-way", 6), ("encoded", 5)):
            assert toolkit.setOptions({"notationSystem": mode, "howeWayReferenceOctaves": {"2": 2}})
            toolkit.redoLayout()
            svg = ET.fromstring(toolkit.renderToSVG(1))
            if mode == "encoded":
                geometry = [(e.tag, e.get("d"), e.get("transform"), e.get("points")) for e in svg.iter()
                            if e.tag.rsplit("}", 1)[-1] in ("path", "use", "polygon")]
                if initial_geometry is None:
                    initial_geometry = geometry
                else:
                    assert geometry == initial_geometry, breaks
            staves = svg.findall(".//{*}g[@class='staff']")
            assert [len(s.findall("{*}path")) for s in staves] == [lines] * 4
            for note, visible in (("bass-whole", lines == 6), ("voice-f", lines == 5)):
                stem = svg.find(f".//*[@id='{note}']/{{*}}g[@class='stem']/{{*}}path")
                assert (stem is not None) == visible, (breaks, mode, note)


def main() -> None:
    try:
        run_smoke_test()
        check_notation_switch()
    except Exception as exc:
        print(f"SMOKE TEST FAIL: {exc}")
        raise

    print("SMOKE TEST PASS")


if __name__ == "__main__":
    main()
