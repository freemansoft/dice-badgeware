"""Draws the dice app on the Tufty 2350 (320x240 colour LCD, HIRES).

The only Tufty-specific file. It reads DiceApp's state and draws; it
never changes it. Redraws every frame (Badgeware's run() clears the
screen before each update), so it animates rolls: for ROLL_ANIM_MS after
a roll, the dice that rolled flicker through random values.

The simulator tests (tests/test_sim.py) check pixels this file pins:
header fills, die body colours, and that nothing but the body fill is
drawn at (cx - half + 8, cy - half + 8) of each die.
"""

import random

from dice_input import ROLL_SCREEN
from dice_layout import grid_slots

WIDTH = 320
HEIGHT = 240
HEADER_H = 40
RADIUS = 10
ROLL_ANIM_MS = 500
VALUE_PX = 40  # minimum height of a die's number

BACKGROUND = (10, 10, 16)
ROLL_HEADER = (28, 28, 40)
CONFIG_HEADER = (20, 90, 160)
PALETTE = [(255, 140, 0), (40, 120, 255), (230, 50, 60), (40, 190, 80), (240, 210, 40), (150, 80, 220)]
LOCKED_BODY = (50, 50, 60)
HIGHLIGHT = (255, 255, 255)
BODY_TEXT = (10, 10, 16)
LOCKED_TEXT = (170, 170, 180)
HEADER_TEXT = (240, 240, 245)
HINT_TEXT = (170, 170, 190)


def _pen(rgb):
    return color.rgb(rgb[0], rgb[1], rgb[2])


class TuftyDisplay:
    def __init__(self):
        badge.mode(HIRES)
        badge.default_clear = _pen(BACKGROUND)
        self.pens = {
            "roll_header": _pen(ROLL_HEADER),
            "config_header": _pen(CONFIG_HEADER),
            "locked": _pen(LOCKED_BODY),
            "highlight": _pen(HIGHLIGHT),
            "body_text": _pen(BODY_TEXT),
            "locked_text": _pen(LOCKED_TEXT),
            "header_text": _pen(HEADER_TEXT),
            "hint_text": _pen(HINT_TEXT),
        }
        self.palette = [_pen(rgb) for rgb in PALETTE]
        self.big = font.absolute
        self.small = font.sins
        # integer scale that makes the big font at least VALUE_PX tall
        self.big_scale = max(1, -(-VALUE_PX // self.big.height))
        self.layouts = {n: grid_slots(WIDTH, HEIGHT, n) for n in range(2, 7)}

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

    # -- helpers ------------------------------------------------------------

    def _text(self, text, x, y, fnt, scale, pen):
        screen.font = fnt
        screen.pen = pen
        screen.text(text, x, y, scale)

    def _centred(self, text, cx, cy, fnt, scale, pen):
        screen.font = fnt
        w, h = screen.measure_text(text, scale)
        screen.pen = pen
        screen.text(text, cx - w / 2, cy - h / 2, scale)

    def _header(self, pen, title, hint):
        screen.pen = pen
        screen.rectangle(0, 0, WIDTH, HEADER_H)
        self._text(title, 10, 4, self.small, 2, self.pens["header_text"])
        self._text(hint, 10, 26, self.small, 1, self.pens["hint_text"])

    def _ring(self, cx, cy, half):
        r = half + 4
        screen.pen = self.pens["highlight"]
        screen.shape(shape.rounded_rectangle(cx - r, cy - r, 2 * r, 2 * r, RADIUS + 3))

    def _body(self, cx, cy, half, pen):
        screen.pen = pen
        screen.shape(shape.rounded_rectangle(cx - half, cy - half, 2 * half, 2 * half, RADIUS))

    # -- screens ------------------------------------------------------------

    def _draw_roll(self, app, now):
        dice = app.dice.dice
        self._header(
            self.pens["roll_header"],
            "TOTAL {}".format(app.dice.total()),
            "DOWN roll   UP lock (hold: unlock all)   B setup",
        )
        animating = app.rolled_at is not None and now - app.rolled_at < ROLL_ANIM_MS
        for i, (cx, cy, half) in enumerate(self.layouts[len(dice)]):
            die = dice[i]
            if i == app.cursor:
                self._ring(cx, cy, half)
            self._body(cx, cy, half, self.pens["locked"] if die.locked else self.palette[i])
            text_pen = self.pens["locked_text"] if die.locked else self.pens["body_text"]
            value = die.value
            if animating and i in app.rolled:
                value = random.randint(1, die.faces)
            self._centred(str(value), cx, cy, self.big, self.big_scale, text_pen)
            label = "d{}".format(die.faces) + (" LOCK" if die.locked else "")
            self._centred(label, cx, cy + half - 10, self.small, 1, text_pen)

    def _draw_config(self, app):
        self._header(
            self.pens["config_header"],
            "DICE {}".format(app.count),
            "A/C move   UP/DOWN change   B done",
        )
        if app.cursor == 0:
            screen.pen = self.pens["highlight"]
            screen.shape(shape.rounded_rectangle(6, 1, 96, 22, 4).stroke(2))
        for i, (cx, cy, half) in enumerate(self.layouts[app.count]):
            if app.cursor == i + 1:
                self._ring(cx, cy, half)
            self._body(cx, cy, half, self.palette[i])
            self._centred("d{}".format(app.faces[i]), cx, cy, self.small, 3, self.pens["body_text"])
