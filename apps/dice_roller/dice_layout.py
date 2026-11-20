"""Where the dice go, for any screen size and dice count.

The spacing copies the Badgeware home menu (160x120: icons 48 px apart,
rows at y 42 and 90, half-size 20), scaled to fit the screen. Dice are
spread evenly: 2 or 3 in one centred row; 4 as 2+2, 5 as 3+2, 6 as 3+3.
Pure Python, no Badgeware names.
"""

MENU_W = 160
MENU_H = 120
STEP = 48
HALF = 20


def _rows(count):
    if count <= 3:
        return [count]
    return [(count + 1) // 2, count // 2]


def grid_slots(width, height, count):
    """(cx, cy, half) for each die, in reading order."""
    s = min(width / MENU_W, height / MENU_H)
    rows = _rows(count)
    if len(rows) == 1:
        ys = [height / 2 + 6 * s]
    else:
        ys = [height / 2 - 18 * s, height / 2 + 30 * s]
    half = round(HALF * s)
    slots = []
    for r, k in enumerate(rows):  # not zip(): MicroPython's has no strict=
        y = ys[r]
        for j in range(k):
            x = width / 2 + (j - (k - 1) / 2) * STEP * s
            slots.append((round(x), round(y), half))
    return slots
