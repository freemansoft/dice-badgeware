import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import make_icon


def test_art_is_24_by_24():
    assert len(make_icon.ART) == 24
    assert all(len(row) == 24 for row in make_icon.ART)


def test_build_png_is_24_by_24_png():
    png = make_icon.build_png(make_icon.ART)
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    assert png[12:16] == b"IHDR"
    assert struct.unpack(">II", png[16:24]) == (24, 24)
