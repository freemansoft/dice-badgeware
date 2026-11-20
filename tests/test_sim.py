"""Run the real app in the badgeware-wasm simulator (Node) and check pixels.

Colours and positions come from apps/dice_roller/display_tufty.py: every
die is dark red, locked dice grey, labels sit beside the five buttons on
both screens, the header is dark on the roll screen and blue on the
configure screen, and the highlighted dice-count field is a white pill.
"""

import json
import shutil
import subprocess
import sys

import dice_layout
import display_tufty as tufty
import pytest
from conftest import ROOT

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")

WIDTH = 320


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    subprocess.run([sys.executable, "sim/stage.py"], cwd=ROOT, check=True, capture_output=True)
    out_dir = tmp_path_factory.mktemp("sim")

    def _run(steps):
        out = out_dir / "frames.json"
        subprocess.run(
            ["node", "sim/run_headless.mjs", "--model", "tufty", "--steps", steps, "--frames", str(out)],
            cwd=ROOT, check=False, capture_output=True, timeout=120,
        )
        return json.loads(out.read_text())

    return _run


def rgb(frame, x, y):
    i = (y * WIDTH + x) * 3
    return tuple(frame[i:i + 3])


def probe(count, i):
    """A point inside die i's body that only the body fill covers."""
    left, top, width, height = tufty.DICE_AREA
    cx, cy, half = dice_layout.grid_slots(width, height, count, left, top)[i]
    return cx - half + 8, cy - half + 8


def is_red_die(c):
    return c[0] > 110 and c[1] < 60 and c[2] < 70


def is_grey_die(c):
    return 60 < c[0] < 120 and abs(c[0] - c[1]) < 20 and abs(c[1] - c[2]) < 20


def is_background(c):
    return max(c) < 30


def bright_pixels(frame, x0, y0, x1, y1):
    return sum(1 for y in range(y0, y1) for x in range(x0, x1) if min(rgb(frame, x, y)) > 150)


def labels_shown(frame):
    """Text beside each of A, B, C (bottom bar) and UP, DOWN (right column)."""
    bottom = [bright_pixels(frame, x - 30, tufty.BAR_TOP + 2, x + 30, 239) for x in tufty.LABEL_X.values()]
    side = [bright_pixels(frame, tufty.COLUMN_LEFT + 2, y - 14, 318, y + 10) for y in tufty.LABEL_Y.values()]
    return all(n >= 5 for n in bottom + side)


def no_errors(result):
    return result["status"] == "ok" and not any("- ERROR" in line for line in result["log"])


def test_boots_to_four_red_dice_two_by_two(run):
    r = run("")
    f = r["frames"][0]
    assert no_errors(r), r["log"]
    assert (r["width"], r["height"]) == (320, 240)
    assert all(is_red_die(rgb(f, *probe(4, i))) for i in range(4))
    assert is_background(rgb(f, *probe(6, 0)))
    assert max(rgb(f, 4, 4)) < 60


def test_labels_beside_every_button_on_both_screens(run):
    r = run("B")
    roll, config = r["frames"]
    assert labels_shown(roll)
    assert labels_shown(config)


def test_b_opens_configure_and_b_returns(run):
    r = run("B,B")
    _, f1, f2 = r["frames"]
    assert no_errors(r), r["log"]
    header = rgb(f1, 4, 4)
    assert header[2] > header[0] + 60          # blue configure header
    assert max(rgb(f2, 4, 4)) < 60             # back to the dark roll header


def test_count_field_highlight_is_a_pill_behind_the_text(run):
    _, on_count, on_die = run("B,C")["frames"]
    assert min(rgb(on_count, 309, 16)) > 200   # white pill, right of the title bar
    assert min(rgb(on_die, 309, 16)) < 200     # gone once the highlight moves to a die


def text_pixels(frame, x0, x1):
    return bright_pixels(frame, x0, 4, x1, 28)


def test_title_bar_has_title_left_and_total_or_count_right(run):
    roll, config = run("B")["frames"]
    for frame in (roll, config):
        assert text_pixels(frame, 8, 120) >= 20     # "Roll Baby Roll" / "Setup"
    assert text_pixels(roll, 220, 316) >= 20        # total, right-aligned
    assert text_pixels(roll, 150, 210) == 0         # nothing in the middle


def test_text_is_antialiased(run):
    """Smooth edges: text drawn over the label bar has in-between shades,
    not just the bar colour and the text colour."""
    f = run("")["frames"][0]
    x = tufty.LABEL_X["B"]
    edges = sum(
        1 for y in range(tufty.BAR_TOP + 2, 239) for px in range(x - 30, x + 30)
        if 90 < min(rgb(f, px, y)) < 190
    )
    assert edges >= 10


def test_up_locks_highlighted_die(run):
    f1 = run("UP")["frames"][1]
    assert is_grey_die(rgb(f1, *probe(4, 0)))
    assert is_red_die(rgb(f1, *probe(4, 1)))


def test_long_up_unlocks_all(run):
    frames = run("UP,C,UP,UP:1200")["frames"]
    assert is_grey_die(rgb(frames[3], *probe(4, 0)))
    assert is_grey_die(rgb(frames[3], *probe(4, 1)))
    assert is_red_die(rgb(frames[4], *probe(4, 0)))
    assert is_red_die(rgb(frames[4], *probe(4, 1)))


def test_configure_five_dice(run):
    r = run("B,UP,B")
    f = r["frames"][-1]
    assert no_errors(r), r["log"]
    assert all(is_red_die(rgb(f, *probe(5, i))) for i in range(5))


def test_rolling_does_not_error(run):
    assert no_errors(run("DOWN,DOWN,DOWN"))
