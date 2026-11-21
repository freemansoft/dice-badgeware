#!/usr/bin/env python3
"""Generate apps/dice_roller/icon.png (24x24 RGBA) for the Badgeware menu.

Standard library only (zlib + struct), so no Pillow is needed. Edit the
ART grid and re-run:

    python3 tools/make_icon.py

Legend: "#" orange die body, "k" black outline, "o" black pip,
"." transparent.
"""

import struct
import zlib
from pathlib import Path

# An orange die showing five, rounded corners, with a black outline and
# black pips so it still reads on the Badger's greyscale e-ink (where the
# orange washes out to white).
ART = [
    "........................",
    "........................",
    "....kkkkkkkkkkkkkkkk....",
    "...k################k...",
    "..k##################k..",
    "..k##################k..",
    "..k###oo########oo###k..",
    "..k##oooo######oooo##k..",
    "..k##oooo######oooo##k..",
    "..k###oo########oo###k..",
    "..k#########oo#######k..",
    "..k########oooo######k..",
    "..k########oooo######k..",
    "..k#########oo#######k..",
    "..k###oo########oo###k..",
    "..k##oooo######oooo##k..",
    "..k##oooo######oooo##k..",
    "..k###oo########oo###k..",
    "..k##################k..",
    "..k##################k..",
    "...k################k...",
    "....kkkkkkkkkkkkkkkk....",
    "........................",
    "........................",
]

PALETTE = {
    "#": (255, 140, 0, 255),
    "k": (0, 0, 0, 255),
    "o": (0, 0, 0, 255),
    ".": (0, 0, 0, 0),
}


def _chunk(kind, data):
    body = kind + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def build_png(rows):
    height = len(rows)
    width = len(rows[0])
    raw = bytearray()
    for row in rows:
        if len(row) != width:
            raise ValueError(f"ragged row: {row!r}")
        raw.append(0)  # filter: none
        for ch in row:
            raw.extend(PALETTE[ch])
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + _chunk(b"IEND", b"")
    )


def main():
    out = Path(__file__).resolve().parent.parent / "apps" / "dice_roller" / "icon.png"
    out.write_bytes(build_png(ART))
    print("wrote", out)


if __name__ == "__main__":
    main()
