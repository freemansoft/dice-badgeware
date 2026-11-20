import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import make_icon

ICON = Path(__file__).resolve().parent.parent / "apps" / "dice_roller" / "icon.png"


def png_size(png):
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    assert png[12:16] == b"IHDR"
    return struct.unpack(">II", png[16:24])


def test_build_png_is_24_by_24_png():
    # build_png refuses ragged rows, so this also proves ART is 24 x 24
    assert png_size(make_icon.build_png(make_icon.ART)) == (24, 24)


def test_committed_icon_is_24_by_24_png():
    assert png_size(ICON.read_bytes()) == (24, 24)
