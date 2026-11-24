"""Run the real app in the badgeware-wasm simulator (Node) and check pixels.

Colours and positions come from apps/dice_roller/devices/tufty.py: every
die is dark red, locked dice grey, labels sit beside the five buttons on
both screens, the header is dark on the roll screen and blue on the
configure screen, and the highlighted dice-count field is a white pill.

Every step costs simulator time, so the tests share two button
sequences (CONFIG and LOCK below); each is run once and its frames
reused. The rules themselves are proved by the host tests; these prove
what only the firmware can: what is drawn where, and that each of the
five buttons reaches the app.
"""


import pytest
from devices import tufty
from game import layout
from simrun import needs_node, simulate

pytestmark = needs_node

WIDTH = 320

# frames[0] is the screen after launch; frames[i] the screen after step i.
# Into configure, highlight to die 1 and back, one more die, accept:
# 1 configure (count highlighted), 2 die 1 highlighted, 3 count again,
# 4 five dice, 5 roll screen with five dice.
CONFIG = "B,C,A,UP,B"
# 1 die 1 locked, 2 highlight on die 2, 3 after holding UP, 4 and 5 rolled.
LOCK = "UP,C,UP:1200,DOWN,DOWN"


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    """run(steps) -> the frames after each step. Each sequence boots the
    simulator once; a crash, an error in the app's log, or a step that
    draws nothing fails the test. (The Tufty redraws every frame, so a step
    with no frames pushed means the app stopped drawing; the runner would
    hand back the last frame again, which the pixel checks can't tell.)"""
    out_dir = tmp_path_factory.mktemp("sim")
    results = {}

    def _run(steps):
        if steps not in results:
            results[steps] = simulate("tufty", steps, out_dir / f"frames{len(results)}.json")
        result = results[steps]
        assert (result["width"], result["height"]) == (WIDTH, 240)
        assert all(n >= 1 for n in result["refreshes"]), result["refreshes"]
        return result["frames"]

    return _run


def rgb(frame, x, y):
    i = (y * WIDTH + x) * 3
    return tuple(frame[i:i + 3])


def probe(count, i):
    """A point inside die i's body that only the body fill covers."""
    left, top, width, height = tufty.DICE_AREA
    cx, cy, half = layout.grid_slots(width, height, count, left, top)[i]
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


def test_boots_to_four_red_dice_two_by_two(run):
    f = run(CONFIG)[0]
    assert all(is_red_die(rgb(f, *probe(4, i))) for i in range(4))
    assert is_background(rgb(f, *probe(6, 0)))
    assert max(rgb(f, 4, 4)) < 60


def test_labels_beside_every_button_on_both_screens(run):
    frames = run(CONFIG)
    assert labels_shown(frames[0])
    assert labels_shown(frames[1])


def test_b_opens_configure_and_b_returns(run):
    frames = run(CONFIG)
    header = rgb(frames[1], 4, 4)
    assert header[2] > header[0] + 60          # blue configure header
    assert max(rgb(frames[5], 4, 4)) < 60      # back to the dark roll header


def test_count_field_highlight_is_a_pill_that_c_and_a_move(run):
    _, on_count, on_die, back_on_count = run(CONFIG)[:4]
    assert min(rgb(on_count, 309, 16)) > 200       # white pill, right of the title bar
    assert min(rgb(on_die, 309, 16)) < 200         # C: gone once the highlight moves to a die
    assert min(rgb(back_on_count, 309, 16)) > 200  # A: back again


def text_pixels(frame, x0, x1):
    return bright_pixels(frame, x0, 4, x1, 28)


def test_title_bar_has_title_left_and_total_or_count_right(run):
    roll, _, config = run(CONFIG)[:3]              # config: highlight on a die, so no pill
    for frame in (roll, config):
        assert text_pixels(frame, 8, 120) >= 20     # "Roll Baby Roll" / "Setup"
        assert text_pixels(frame, 220, 316) >= 20   # total / dice count, right-aligned
    assert text_pixels(roll, 150, 210) == 0         # nothing in the middle


def test_text_is_antialiased(run):
    """Smooth edges: text drawn over the label bar has in-between shades,
    not just the bar colour and the text colour."""
    f = run(CONFIG)[0]
    x = tufty.LABEL_X["B"]
    edges = sum(
        1 for y in range(tufty.BAR_TOP + 2, 239) for px in range(x - 30, x + 30)
        if 90 < min(rgb(f, px, y)) < 190
    )
    assert edges >= 10


def test_up_locks_highlighted_die(run):
    f1 = run(LOCK)[1]
    assert is_grey_die(rgb(f1, *probe(4, 0)))
    assert is_red_die(rgb(f1, *probe(4, 1)))


def test_long_up_unlocks_all(run):
    # the hold is on die 2, so only "unlock all" can turn die 1 red again
    frames = run(LOCK)
    assert is_grey_die(rgb(frames[2], *probe(4, 0)))
    assert is_red_die(rgb(frames[3], *probe(4, 0)))
    assert is_red_die(rgb(frames[3], *probe(4, 1)))


def test_configure_five_dice(run):
    f = run(CONFIG)[5]
    assert all(is_red_die(rgb(f, *probe(5, i))) for i in range(5))


def test_down_rolls_the_dice(run):
    # Each frame is taken after the roll animation has ended. A roll that
    # repeats all four values draws the same frame (1 in 1296), so two
    # rolls are given the chance to show a change.
    before, first, second = run(LOCK)[3:]
    assert first != before or second != first

