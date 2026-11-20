"""Where the dice go, for any area and dice count.

The spacing copies the Badgeware home menu's icon grid (icons 40 px wide
in 48 px cells, three across and two down), scaled to fill the area the
display gives the dice. Dice are spread evenly: 2 or 3 in one centred
row; 4 as 2+2, 5 as 3+2, 6 as 3+3. Pure Python, no Badgeware names.
"""

CELL = 48  # menu cell size
HALF = 20  # menu icon half-size


def _rows(count):
    if count <= 3:
        return [count]
    return [(count + 1) // 2, count // 2]


def grid_slots(width, height, count, left=0, top=0):
    """(cx, cy, half) for each die, in reading order, inside the area
    width x height whose top-left corner is (left, top)."""
    s = min(width / (3 * CELL), height / (2 * CELL))
    rows = _rows(count)
    mid_x = left + width / 2
    mid_y = top + height / 2
    if len(rows) == 1:
        ys = [mid_y]
    else:
        ys = [mid_y - CELL / 2 * s, mid_y + CELL / 2 * s]
    half = round(HALF * s)
    slots = []
    for r, k in enumerate(rows):  # not zip(): MicroPython's has no strict=
        y = ys[r]
        for j in range(k):
            x = mid_x + (j - (k - 1) / 2) * CELL * s
            slots.append((round(x), round(y), half))
    return slots
