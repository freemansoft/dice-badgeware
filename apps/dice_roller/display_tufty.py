"""Draws the dice app on the Tufty 2350 (320x240 colour LCD, HIRES).

The only Tufty-specific file. It reads DiceApp's state and draws; it
never changes it. The Tufty's run() polls, clears and pushes every frame,
so this redraws every frame and animates rolls: for ROLL_ANIM_MS after a
roll, the unlocked dice that rolled flicker through random values.

Screen layout (the Tufty's A, B, C buttons sit below the screen and UP,
DOWN on its right edge, so their labels go beside them):

    +------------------------------------+---------+
    | Roll Baby Roll / Setup    total / count |  title bar 0-31
    +------------------------------------+         |
    |                                    |  Lock   |  UP at y ~85
    |      dice area 264 x 180           |         |
    |                                    |  Roll   |  DOWN at y ~182
    +------------------------------------+---------+
    |   Left        Setup        Right             |  212-239
    +----------------------------------------------+
        A (x 52)    B (x 153)    C (x 255)

Text uses the firmware's MonaSans vector font, with 4x anti-aliasing
(Badgeware draws vector text with hard edges unless screen.antialias is
set), falling back to a pixel font if it can't be loaded. The simulator tests
(tests/test_sim.py) check the colours and positions pinned here.
"""

import random

from dice_input import A, B, C, DOWN, HOLD_LABELS, LABELS, ROLL_SCREEN, UP
from dice_layout import grid_slots

WIDTH = 320
HEIGHT = 240
HEADER_H = 32
BAR_TOP = 212
COLUMN_LEFT = 264
DICE_AREA = (0, HEADER_H, COLUMN_LEFT, BAR_TOP - HEADER_H)  # left, top, width, height
LABEL_X = {A: 52, B: 153, C: 255}   # centred over the buttons below the screen
LABEL_Y = {UP: 85, DOWN: 182}       # level with the buttons on the right edge
COLUMN_X = (COLUMN_LEFT + WIDTH) // 2
RADIUS = 12
ROLL_ANIM_MS = 500

MONA = "/system/assets/fonts/MonaSans-Medium.af"
TITLE = "Roll Baby Roll"
SETUP_TITLE = "Setup"
RIGHT_EDGE = WIDTH - 10  # right-aligned title-bar items end here
SIZE_HEADER = 20
SIZE_LABEL = 17
SIZE_HOLD = 11
SIZE_VALUE = 40
SIZE_TYPE = 13
SIZE_FACES = 26

BACKGROUND = (12, 12, 18)
ROLL_HEADER = (32, 32, 44)
CONFIG_HEADER = (20, 90, 160)
BAR = (32, 32, 44)
DIE = (150, 22, 34)          # every die: dark red
LOCKED_DIE = (85, 85, 95)    # locked: grey
HIGHLIGHT = (255, 255, 255)
DIE_TEXT = (250, 250, 250)
LOCKED_TEXT = (205, 205, 210)
LABEL_TEXT = (240, 240, 245)
HOLD_TEXT = (165, 165, 185)
PILL_TEXT = (20, 40, 80)


def _pen(rgb):
    return color.rgb(rgb[0], rgb[1], rgb[2])


class TuftyDisplay:
    def __init__(self):
        badge.mode(HIRES)
        badge.default_clear = _pen(BACKGROUND)
        screen.antialias = image.X4  # smooth edges on vector text and shapes
        self.pens = {
            name: _pen(rgb)
            for name, rgb in (
                ("roll_header", ROLL_HEADER), ("config_header", CONFIG_HEADER), ("bar", BAR),
                ("die", DIE), ("locked", LOCKED_DIE), ("highlight", HIGHLIGHT),
                ("die_text", DIE_TEXT), ("locked_text", LOCKED_TEXT), ("label", LABEL_TEXT),
                ("hold", HOLD_TEXT), ("pill_text", PILL_TEXT),
            )
        }
        try:
            self.font = font.load(MONA)
        except Exception:  # noqa: BLE001 - fall back to a ROM pixel font
            self.font = None
        left, top, width, height = DICE_AREA
        self.layouts = {n: grid_slots(width, height, n, left, top) for n in range(2, 7)}

    # -- the display contract (called by __init__.py every frame) -------------

    def begin_frame(self):
        """Before buttons are read. Nothing to do: the Tufty's run() polls
        the buttons and clears the screen before each update()."""

    def end_frame(self, app, now):
        """Draw the frame; the Tufty's run() pushes it to the LCD afterwards.
        An e-ink display would instead redraw only when app.changes moves,
        and call display.update() itself."""
        self.draw(app, now)

    def draw(self, app, now):
        if app.screen == ROLL_SCREEN:
            self._draw_roll(app, now)
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

    def _die(self, cx, cy, half, highlighted, pen):
        if highlighted:
            r = half + 4
            self._rect(cx - r, cy - r, 2 * r, 2 * r, self.pens["highlight"], RADIUS + 3)
        self._rect(cx - half, cy - half, 2 * half, 2 * half, pen, RADIUS)

    def _draw_labels(self, screen_name):
        self._rect(0, BAR_TOP, WIDTH, HEIGHT - BAR_TOP, self.pens["bar"])
        self._rect(COLUMN_LEFT, HEADER_H, WIDTH - COLUMN_LEFT, BAR_TOP - HEADER_H, self.pens["bar"])
        labels = LABELS[screen_name]
        holds = HOLD_LABELS[screen_name]
        mid_bar = (BAR_TOP + HEIGHT) // 2
        for button, x in LABEL_X.items():
            self._centred(labels[button], x, mid_bar, SIZE_LABEL, self.pens["label"])
        for button, y in LABEL_Y.items():
            if button in holds:
                self._centred(labels[button], COLUMN_X, y - 7, SIZE_LABEL, self.pens["label"])
                self._centred(holds[button], COLUMN_X, y + 11, SIZE_HOLD, self.pens["hold"])
            else:
                self._centred(labels[button], COLUMN_X, y, SIZE_LABEL, self.pens["label"])

    # -- screens --------------------------------------------------------------

    def _draw_roll(self, app, now):
        dice = app.dice.dice
        self._rect(0, 0, WIDTH, HEADER_H, self.pens["roll_header"])
        self._text(TITLE, 10, 5, SIZE_HEADER, self.pens["label"])
        total = "Total  {}".format(app.dice.total())
        w, _ = self._measure(total, SIZE_HEADER)
        self._text(total, RIGHT_EDGE - w, 5, SIZE_HEADER, self.pens["label"])
        animating = app.rolled_at is not None and now - app.rolled_at < ROLL_ANIM_MS
        for i, (cx, cy, half) in enumerate(self.layouts[len(dice)]):
            die = dice[i]
            self._die(cx, cy, half, i == app.cursor, self.pens["locked"] if die.locked else self.pens["die"])
            text_pen = self.pens["locked_text"] if die.locked else self.pens["die_text"]
            value = die.value
            if animating and i in app.rolled and not die.locked:
                value = random.randint(1, die.faces)
            self._centred(str(value), cx, cy - 4, SIZE_VALUE, text_pen)
            label = "d{} LOCK".format(die.faces) if die.locked else "d{}".format(die.faces)
            self._centred(label, cx, cy + half - 11, SIZE_TYPE, text_pen)

    def _draw_config(self, app):
        self._rect(0, 0, WIDTH, HEADER_H, self.pens["config_header"])
        self._text(SETUP_TITLE, 10, 5, SIZE_HEADER, self.pens["label"])
        field = "Dice  {}".format(app.count)
        w, _ = self._measure(field, SIZE_HEADER)
        x = RIGHT_EDGE - w
        if app.cursor == 0:
            # highlighted field: a white pill behind dark text, so the
            # highlight can never cut through the text
            self._rect(x - 8, 3, w + 16, HEADER_H - 6, self.pens["highlight"], 8)
            self._text(field, x, 5, SIZE_HEADER, self.pens["pill_text"])
        else:
            self._text(field, x, 5, SIZE_HEADER, self.pens["label"])
        for i, (cx, cy, half) in enumerate(self.layouts[app.count]):
            self._die(cx, cy, half, app.cursor == i + 1, self.pens["die"])
            self._centred("d{}".format(app.faces[i]), cx, cy, SIZE_FACES, self.pens["die_text"])
