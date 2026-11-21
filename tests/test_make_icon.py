import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import make_icon

ICON = Path(__file__).resolve().parent.parent / "apps" / "dice_roller" / "icon.png"

TRANSPARENT = (0, 0, 0, 0)
ORANGE = (255, 140, 0, 255)
WHITE = (255, 255, 255, 255)


def decode(png):
    """(width, height, rows of RGBA pixels) from an 8-bit RGBA PNG with no
    row filters, checking the signature and every chunk's CRC."""
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    pos, chunks = 8, {}
    while pos < len(png):
        (length,) = struct.unpack(">I", png[pos:pos + 4])
        kind, data = png[pos + 4:pos + 8], png[pos + 8:pos + 8 + length]
        (crc,) = struct.unpack(">I", png[pos + 8 + length:pos + 12 + length])
        assert crc == zlib.crc32(kind + data) & 0xFFFFFFFF, kind
        chunks[kind] = data
        pos += 12 + length
    assert list(chunks) == [b"IHDR", b"IDAT", b"IEND"]
    width, height, depth, colour = struct.unpack(">IIBB", chunks[b"IHDR"][:10])
    assert (depth, colour) == (8, 6)  # 8-bit RGBA
    raw = zlib.decompress(chunks[b"IDAT"])
    stride = 1 + width * 4
    rows = []
    for y in range(height):
        line = raw[y * stride:(y + 1) * stride]
        assert line[0] == 0  # filter: none
        rows.append([tuple(line[1 + x * 4:5 + x * 4]) for x in range(width)])
    return width, height, rows


def test_build_png_draws_the_art():
    width, height, rows = decode(make_icon.build_png(make_icon.ART))
    assert (width, height) == (24, 24)
    assert rows[0][0] == TRANSPARENT      # outside the die
    assert rows[4][4] == ORANGE           # die body
    assert rows[11][12] == WHITE          # the centre pip
    assert rows[2][3] == TRANSPARENT and rows[2][4] == ORANGE  # rounded corner


def test_committed_icon_is_the_generated_one():
    # pixels, not bytes: another zlib may compress the same pixels differently
    assert decode(ICON.read_bytes()) == decode(make_icon.build_png(make_icon.ART))
