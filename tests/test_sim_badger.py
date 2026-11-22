"""Run the real app on the Badger 2350 in the badgeware-wasm simulator.

Shades and positions come from apps/dice_roller/devices/badger.py. The
simulator, like the panel, reduces every frame to four greys (0, 85, 170,
255), so pixels are read as bands. Each boot costs several seconds, so the
tests share two sequences (SCREENS and ROLL below), each run once, plus
one relaunch from ROLL's saved record.
"""

import json

import pytest
from devices import badger
from game import layout
from simrun import needs_node, simulate

pytestmark = needs_node

W, H = badger.WIDTH, badger.HEIGHT

# 0 launch, 1 die 1 locked, 2 highlight on die 2, 3 after holding UP
# (unlock all), 4 the setup screen.
SCREENS = "UP,C,UP:2500,B"
# 1 die 1 locked, 2 the others rolled (DOWN held 2 s, so a second refresh
# ~0.8 s later would be counted too); saved after the roll.
ROLL = "UP,DOWN:2000"


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    out_dir = tmp_path_factory.mktemp("sim_badger")
    results = {}

    def _run(steps, state=None):
        key = (steps, state)
        if key not in results:
            n = len(results)
            state_path = None
            if state is not None:
                state_path = out_dir / f"state{n}.json"
                state_path.write_text(state)
            results[key] = simulate("badger", steps, out_dir / f"frames{n}.json", state_path)
        result = results[key]
        assert (result["width"], result["height"]) == (W, H)
        return result

    return _run


def shade(frame, x, y):
    v = max(frame[(y * W + x) * 3:(y * W + x) * 3 + 3])
    if v < 40:
        return "black"
    if v <= 120:
        return "dark"
    if v <= 215:
        return "light"
    return "white"


def slots(count=4):
    left, top, width, height = badger.DICE_AREA
    return layout.grid_slots(width, height, count, left, top)


def face_shade(frame, i, count=4):
    """Die i's face, inside its outline and left of its text: white, or
    light grey when locked."""
    cx, cy, half = slots(count)[i]
    return shade(frame, cx - half + 6, cy + half // 2)


def dark_pixels(frame, x0, y0, x1, y1):
    return sum(1 for y in range(y0, y1) for x in range(x0, x1) if shade(frame, x, y) in ("black", "dark"))


def labels_shown(frame):
    bottom = [dark_pixels(frame, x - 25, badger.BAR_TOP + 2, x + 25, H) for x in badger.LABEL_X.values()]
    side = [dark_pixels(frame, badger.COLUMN_LEFT + 2, y - 12, W, y + 8) for y in badger.LABEL_Y.values()]
    return all(n >= 5 for n in bottom + side)


def test_badger_boots_to_four_white_dice(run):
    frame = run(SCREENS)["frames"][0]
    assert [face_shade(frame, i) for i in range(4)] == ["white"] * 4


def test_badger_labels_beside_every_button(run):
    frames = run(SCREENS)["frames"]
    roll, setup = frames[0], frames[4]
    assert labels_shown(roll)
    assert labels_shown(setup)


def test_badger_locked_die_is_grey(run):
    frame = run(SCREENS)["frames"][1]
    assert face_shade(frame, 0) == "light"
    assert face_shade(frame, 1) == "white"


def test_badger_long_up_unlocks_all(run):
    frames = run(SCREENS)["frames"]
    assert face_shade(frames[2], 0) == "light"  # still locked before the hold
    assert [face_shade(frames[3], i) for i in range(4)] == ["white"] * 4


def test_badger_setup_header_is_dark_grey(run):
    frames = run(SCREENS)["frames"]
    roll, setup = frames[0], frames[4]
    assert shade(roll, 4, 4) == "black"
    assert shade(setup, 4, 4) == "dark"


def test_badger_roll_refreshes_once(run):
    # no animation: one e-ink refresh, straight to the final values
    assert run(ROLL)["refreshes"][2] == 1


def test_badger_relaunch_restores_the_roll(run):
    first = run(ROLL)
    state = first["state"]
    assert json.loads(state)["locked"][0] is True
    again = run("", state=state)
    assert again["frames"][0] == first["frames"][-1]


def text_height(frame, x0, y0, x1, y1):
    """Rows from the top to the bottom of the dark pixels in a box."""
    rows = [y for y in range(y0, y1) if any(shade(frame, x, y) in ("black", "dark") for x in range(x0, x1))]
    return max(rows) - min(rows) + 1 if rows else 0


def test_badger_labels_are_large(run):
    # the user found the first labels (~9 px tall) small; there is room
    frame = run(SCREENS)["frames"][0]
    bottom = [text_height(frame, x - 25, badger.BAR_TOP + 2, x + 25, H) for x in badger.LABEL_X.values()]
    roll = text_height(frame, badger.COLUMN_LEFT + 2, badger.LABEL_Y["DOWN"] - 12, W, badger.LABEL_Y["DOWN"] + 12)
    assert min([*bottom, roll]) >= 12


def test_badger_dice_are_large(run):
    # the user found the dice (38 px) much smaller than the Tufty's; each
    # die now fills its slot. Measured along die 2's centre row (die 1 is
    # highlighted, and its ring would add to the width).
    frame = run(SCREENS)["frames"][0]
    cx, cy, half = slots()[1]
    row = [x for x in range(cx - half - 2, cx + half + 2) if shade(frame, x, cy + half // 2) == "black"]
    assert max(row) - min(row) + 1 >= 50


def test_badger_highlight_clears_the_bars(run):
    # the ring round a highlighted die sits outside it (outer edge half +
    # FRAME_OUT): white must still show between it and the title bar, and
    # it must end above the line over the labels for every dice count
    frame = run(SCREENS)["frames"][0]  # die 1, top row, highlighted
    cx, _, _ = slots()[0]
    assert shade(frame, cx, badger.HEADER_H) == "white"
    for count in range(2, 7):
        for _, cy, half in slots(count):
            assert cy - half - badger.FRAME_OUT > badger.HEADER_H
            assert cy + half + badger.FRAME_OUT < badger.BAR_TOP


def ink_rows(frame, x0, y0, x1, y1):
    rows = [y for y in range(y0, y1) if any(shade(frame, x, y) in ("black", "dark") for x in range(x0, x1))]
    return min(rows), max(rows)


def test_badger_labels_fit_inside_their_bars(run):
    # big labels must not touch the screen edge or the line above the bar
    for frame in run(SCREENS)["frames"][::3]:  # the roll screen, then setup
        for x in badger.LABEL_X.values():
            top, bottom = ink_rows(frame, x - 30, badger.BAR_TOP + 1, x + 30, H)
            assert top >= badger.BAR_TOP + 3 and bottom <= H - 3
        _, bottom = ink_rows(frame, badger.COLUMN_LEFT + 1, badger.LABEL_Y["DOWN"] - 16, W, badger.BAR_TOP)
        assert bottom <= badger.BAR_TOP - 3


def test_badger_bottom_labels_clear_the_divider(run):
    # on the real panel the bottom labels touched the line above them at a
    # 4 px gap in the simulator; the line now sits higher
    frame = run(SCREENS)["frames"][0]
    tops = [ink_rows(frame, x - 30, badger.BAR_TOP + 1, x + 30, H)[0] for x in badger.LABEL_X.values()]
    assert min(tops) - badger.BAR_TOP >= 7
