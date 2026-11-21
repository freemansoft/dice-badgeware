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


def body_shade(frame, i, count=4):
    """Inside die i's body, left of its text."""
    cx, cy, half = slots(count)[i]
    body = half - badger.BODY_INSET
    return shade(frame, cx - body + 4, cy + body // 2)


def box_shade(frame, i, count=4):
    """Between die i's body and the locked box's edge: grey only when locked."""
    cx, cy, half = slots(count)[i]
    return shade(frame, cx, cy - (half - badger.LOCK_INSET) + 2)


def dark_pixels(frame, x0, y0, x1, y1):
    return sum(1 for y in range(y0, y1) for x in range(x0, x1) if shade(frame, x, y) in ("black", "dark"))


def labels_shown(frame):
    bottom = [dark_pixels(frame, x - 25, badger.BAR_TOP + 2, x + 25, H) for x in badger.LABEL_X.values()]
    side = [dark_pixels(frame, badger.COLUMN_LEFT + 2, y - 12, W, y + 8) for y in badger.LABEL_Y.values()]
    return all(n >= 5 for n in bottom + side)


def test_badger_boots_to_four_white_dice(run):
    frame = run(SCREENS)["frames"][0]
    assert [body_shade(frame, i) for i in range(4)] == ["white"] * 4
    assert [box_shade(frame, i) for i in range(4)] == ["white"] * 4


def test_badger_labels_beside_every_button(run):
    frames = run(SCREENS)["frames"]
    roll, setup = frames[0], frames[4]
    assert labels_shown(roll)
    assert labels_shown(setup)


def test_badger_lock_draws_grey_box(run):
    frame = run(SCREENS)["frames"][1]
    assert box_shade(frame, 0) == "light" and body_shade(frame, 0) == "white"
    assert box_shade(frame, 1) == "white"


def test_badger_long_up_unlocks_all(run):
    frames = run(SCREENS)["frames"]
    assert box_shade(frames[2], 0) == "light"  # still locked before the hold
    assert [box_shade(frames[3], i) for i in range(4)] == ["white"] * 4


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


def test_badger_lock_box_is_wide(run):
    # the user found the first grey band (4 px) hard to see
    frame = run(SCREENS)["frames"][1]
    cx, cy, half = slots()[0]
    band = [y for y in range(cy - half - 6, cy) if shade(frame, cx, y) == "light"]
    assert len(band) >= 8


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
