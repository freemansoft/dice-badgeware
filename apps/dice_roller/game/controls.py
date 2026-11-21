"""Buttons to actions, the same on every badge.

__init__.py turns Badgeware's BUTTON_* constants into the names below and
calls InputMapper.actions() once per frame. Pure Python, no Badgeware names.

Roll screen:      A left, C right, UP lock (hold: unlock all), DOWN roll,
                  B configure.
Configure screen: A left, C right, UP increase, DOWN decrease, B accept.
"""

A = "A"
B = "B"
C = "C"
UP = "UP"
DOWN = "DOWN"

ROLL_SCREEN = "roll_screen"
CONFIG_SCREEN = "config_screen"

LEFT = "left"
RIGHT = "right"
LOCK = "lock"
UNLOCK_ALL = "unlock_all"
ROLL = "roll"
CONFIGURE = "configure"
INC = "inc"
DEC = "dec"
ACCEPT = "accept"

LONG_PRESS_MS = 800
# A hold only counts while it is watched. A badge that blocks for a while
# between frames (the Badger's ~1 s e-ink refresh) can't tell a held
# button from a second tap, so a gap longer than this restarts the hold.
MAX_FRAME_GAP_MS = 250
# The home menu launches an app on a B press; ignore buttons briefly so
# that press can't open the configure screen. Not after a wake from sleep:
# then the first press is the one that woke the badge, and it should act.
STARTUP_IGNORE_MS = 400

# Button order within one frame, and what each does on each screen.
ORDER = (A, C, UP, DOWN, B)
MAPS = {
    ROLL_SCREEN: {A: LEFT, C: RIGHT, UP: LOCK, DOWN: ROLL, B: CONFIGURE},
    CONFIG_SCREEN: {A: LEFT, C: RIGHT, UP: INC, DOWN: DEC, B: ACCEPT},
}

# What the screen shows next to each button, on every badge. Displays
# decide where the labels go; the words live here, beside the mapping.
LABELS = {
    ROLL_SCREEN: {A: "Left", B: "Setup", C: "Right", UP: "Lock", DOWN: "Roll"},
    CONFIG_SCREEN: {A: "Left", B: "Done", C: "Right", UP: "More", DOWN: "Less"},
}
# A second, smaller line for buttons that also do something when held.
HOLD_LABELS = {
    ROLL_SCREEN: {UP: "hold: all"},
    CONFIG_SCREEN: {},
}


class InputMapper:
    def __init__(self, ignore_ms=STARTUP_IGNORE_MS):
        self.ignore_ms = ignore_ms
        self.start = None
        self.last_frame = None
        self.up_pressed_at = None
        self.long_fired = False

    def actions(self, screen, pressed, held, now):
        """Actions for this frame. pressed: buttons that went down this
        frame; held: buttons down now."""
        if self.start is None:
            self.start = now
        if now - self.start < self.ignore_ms:
            return []

        gap = None if self.last_frame is None else now - self.last_frame
        self.last_frame = now
        if UP not in held:
            self.up_pressed_at = None
        elif self.up_pressed_at is not None and gap is not None and gap > MAX_FRAME_GAP_MS:
            self.up_pressed_at = now  # not watched in between: start again
        if UP in pressed:
            self.up_pressed_at = now
            self.long_fired = False

        mapping = MAPS[screen]
        result = [mapping[b] for b in ORDER if b in pressed]

        if (
            screen == ROLL_SCREEN
            and self.up_pressed_at is not None
            and not self.long_fired
            and now - self.up_pressed_at >= LONG_PRESS_MS
        ):
            self.long_fired = True
            result.append(UNLOCK_ALL)
        return result
