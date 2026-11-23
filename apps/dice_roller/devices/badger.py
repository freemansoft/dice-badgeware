"""Draws the dice app on the Badger 2350 (264x176 e-ink, four greys).

The Badger 2350 display. It reads DiceApp's state and draws; it
never changes it. Unlike the Tufty, the Badger's run() loop only calls
update(), so this display pushes frames, polls and waits itself:

- it refreshes only when app.changes moves (each refresh is a full,
  blocking e-ink update of about a second; presses made during it are
  dropped, as in Pimoroni's own Badger apps);
- there is no roll animation: dice and the total show their final values;
- between presses it waits in the firmware's wait_for_button_or_alarm(),
  which on battery powers the badge off after SLEEP_AFTER_MS; the next
  press restarts the app, which shows the saved roll again.

Screen layout (A, B, C sit below the screen, UP and DOWN on its right
edge, so their labels go beside them):

    +--------------------------------+-------+
    | Roll Baby Roll / Setup   total / count |  title bar 0-21
    +--------------------------------+       |
    |                                | Lock  |  UP at y ~58
    |     dice area 212 x 129        |       |
    |                                | Roll  |  DOWN at y ~132
    +--------------------------------+-------+
    |  Left        Setup        Right        |  151-175
    +----------------------------------------+
       A (x 44)    B (x 128)    C (x 212)

Only equal-channel greys are used: the panel ORs R, G and B together and
keeps four levels, so a colour washes out (color.light_grey, 0xC0, lands
on white). The simulator tests (tests/sim/test_sim_badger.py) check the
shades and positions pinned here.
"""

from game.controls import A, B, C, DOWN, HOLD_LABELS, LABELS, ROLL_SCREEN, UP
from game.layout import grid_slots

WIDTH = 264
HEIGHT = 176
HEADER_H = 22
BAR_TOP = 151
COLUMN_LEFT = 212
DICE_AREA = (0, HEADER_H, COLUMN_LEFT, BAR_TOP - HEADER_H)  # left, top, width, height
LABEL_X = {A: 44, B: 128, C: 212}   # centred over the buttons below the screen
LABEL_Y = {UP: 58, DOWN: 132}       # level with the buttons on the right edge
# MonaSans sits low in its measured box, so the bottom labels centre a
# little above the bar's middle to keep descenders off the screen edge.
LABEL_BAR_Y = 161
COLUMN_X = (COLUMN_LEFT + WIDTH) // 2
RIGHT_EDGE = WIDTH - 6  # right-aligned title-bar items end here

# A die at (cx, cy, half) from grid_slots fills its slot: 2 * half across,
# a black outline round a white face, or a light-grey face when locked.
FRAME_OUT = 4    # highlight ring: outer edge at half + 4 ...
FRAME_W = 3      # ... and 3 px wide, in the gap just outside the die
OUTLINE = 2
RADIUS = 6

SLEEP_AFTER_MS = 30_000

MONA = "/system/assets/fonts/MonaSans-Medium.af"
TITLE = "Roll Baby Roll"
SETUP_TITLE = "Setup"
SIZE_HEADER = 14
SIZE_LABEL = 19
SIZE_HOLD = 11
SIZE_VALUE = 29
SIZE_TYPE = 10
SIZE_FACES = 19

BLACK = (0, 0, 0)
DARK = (96, 96, 96)
LIGHT = (160, 160, 160)
WHITE = (255, 255, 255)


def _pen(rgb):
    return color.rgb(rgb[0], rgb[1], rgb[2])


class BadgerDisplay:
    def __init__(self):
        # no badge.mode(HIRES): the Badger has one resolution, and mode()
        # would also reset its refresh flags
        self.pens = {"black": _pen(BLACK), "dark": _pen(DARK), "light": _pen(LIGHT), "white": _pen(WHITE)}
        badge.default_clear = self.pens["white"]
        screen.antialias = image.X4  # smooth vector text; edges snap to the four greys
        try:
            self.font = font.load(MONA)
        except Exception:  # noqa: BLE001 - fall back to a ROM pixel font
            self.font = None
        left, top, width, height = DICE_AREA
        self.layouts = {n: grid_slots(width, height, n, left, top) for n in range(2, 7)}
        self.drawn = None  # app.changes at the last refresh; None until the first

    # -- the display contract (see devices/__init__.py; called every frame) -------------

    def begin_frame(self):
        """Before buttons are read. Nothing to do: end_frame() leaves a fresh
        poll behind (from the refresh, the wait, or an explicit poll)."""

    def end_frame(self, app, _now):
        """Refresh if anything changed, then wait for the next press. No
        animation, so the time isn't needed."""
        fresh = False
        if self.drawn is None or app.changes != self.drawn:
            self.draw(app)
            badge.update()  # pushes the frame, clears the buffer, polls
            self.drawn = app.changes
            fresh = True
        if fresh and (badge.pressed() or badge.held()):
            return  # the poll inside update() saw a button: handle it next frame
        if badge.held():
            badge.poll()  # keep polling so a long press is measured
            return
        wait_for_button_or_alarm(timeout=SLEEP_AFTER_MS)

    def draw(self, app):
        self._rect(0, 0, WIDTH, HEIGHT, self.pens["white"])
        if app.screen == ROLL_SCREEN:
            self._draw_roll(app)
        else:
            self._draw_config(app)
        self._draw_labels(app.screen)

    # -- text -----------------------------------------------------------------

    def _use(self, size):
        """Select the font; return the size argument to draw it with."""
        if self.font is not None:
            screen.font = self.font
            return size
        screen.font = font.sins
        return max(1, round(size / 10))

    def _measure(self, text, size):
        return screen.measure_text(text, self._use(size))

    def _text(self, text, x, y, size, pen):
        drawn = self._use(size)
        screen.pen = pen
        screen.text(text, x, y, drawn)

    def _centred(self, text, cx, cy, size, pen):
        drawn = self._use(size)
        w, h = screen.measure_text(text, drawn)
        screen.pen = pen
        screen.text(text, cx - w / 2, cy - h / 2, drawn)

    # -- pieces ---------------------------------------------------------------

    def _rect(self, x, y, w, h, pen, radius=0):
        screen.pen = pen
        if radius:
            screen.shape(shape.rounded_rectangle(x, y, w, h, radius))
        else:
            screen.rectangle(x, y, w, h)

    def _square(self, cx, cy, r, pen, radius=RADIUS):
        self._rect(cx - r, cy - r, 2 * r, 2 * r, pen, radius)

    def _die(self, cx, cy, half, highlighted, locked):
        if highlighted:
            outer = half + FRAME_OUT
            self._square(cx, cy, outer, self.pens["black"], RADIUS + 2)
            self._square(cx, cy, outer - FRAME_W, self.pens["white"], RADIUS + 1)
        face = self.pens["light"] if locked else self.pens["white"]
        self._square(cx, cy, half, self.pens["black"])
        self._square(cx, cy, half - OUTLINE, face, RADIUS - 1)

    def _header(self, title, right, fill, pill=False):
        self._rect(0, 0, WIDTH, HEADER_H, self.pens[fill])
        self._text(title, 6, 3, SIZE_HEADER, self.pens["white"])
        w, _ = self._measure(right, SIZE_HEADER)
        x = RIGHT_EDGE - w
        if pill:
            # highlighted field: a white pill behind black text
            self._rect(x - 5, 2, w + 10, HEADER_H - 4, self.pens["white"], 6)
            self._text(right, x, 3, SIZE_HEADER, self.pens["black"])
        else:
            self._text(right, x, 3, SIZE_HEADER, self.pens["white"])

    def _draw_labels(self, screen_name):
        black = self.pens["black"]
        self._rect(0, BAR_TOP, WIDTH, 1, black)
        self._rect(COLUMN_LEFT, HEADER_H, 1, BAR_TOP - HEADER_H, black)
        labels = LABELS[screen_name]
        holds = HOLD_LABELS[screen_name]
        for button, x in LABEL_X.items():
            self._centred(labels[button], x, LABEL_BAR_Y, SIZE_LABEL, black)
        for button, y in LABEL_Y.items():
            if button in holds:
                self._centred(labels[button], COLUMN_X, y - 7, SIZE_LABEL, black)
                self._centred(holds[button], COLUMN_X, y + 11, SIZE_HOLD, self.pens["dark"])
            else:
                self._centred(labels[button], COLUMN_X, y, SIZE_LABEL, black)

    # -- screens --------------------------------------------------------------

    def _draw_roll(self, app):
        dice = app.dice.dice
        self._header(TITLE, "Total  {}".format(app.dice.total()), "black")
        black = self.pens["black"]
        for i, (cx, cy, half) in enumerate(self.layouts[len(dice)]):
            die = dice[i]
            self._die(cx, cy, half, i == app.cursor, die.locked)
            self._centred(str(die.value), cx, cy - 4, SIZE_VALUE, black)
            self._centred("d{}".format(die.faces), cx, cy + half - 10, SIZE_TYPE, black)

    def _draw_config(self, app):
        self._header(SETUP_TITLE, "Dice  {}".format(app.count), "dark", pill=app.cursor == 0)
        for i, (cx, cy, half) in enumerate(self.layouts[app.count]):
            self._die(cx, cy, half, app.cursor == i + 1, False)
            self._centred("d{}".format(app.faces[i]), cx, cy, SIZE_FACES, self.pens["black"])
