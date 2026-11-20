"""The app's state: which screen is showing, the highlight, the dice and
the configuration being edited. Displays read it; actions change it.

Pure Python, no Badgeware names. `changes` goes up whenever anything
visible changes, so a display that must not redraw every frame (e-ink)
can redraw only when it moves. A roll changes the values at once and
records which dice rolled and when; any roll animation is the display's.
"""

from dice import MAX_FACES, MIN_FACES, DiceSet
from dice_config import MAX_COUNT, MIN_COUNT
from dice_input import (
    ACCEPT,
    CONFIG_SCREEN,
    CONFIGURE,
    DEC,
    INC,
    LEFT,
    LOCK,
    RIGHT,
    ROLL,
    ROLL_SCREEN,
    UNLOCK_ALL,
)


def _clamp(value, low, high):
    return max(low, min(high, value))


class DiceApp:
    def __init__(self, config, randint):
        """config: an already repaired {"count", "faces"} dict."""
        self.randint = randint
        self.count = config["count"]
        self.faces = list(config["faces"])
        self.screen = ROLL_SCREEN
        self.cursor = 0
        self.changes = 0
        self.rolled = []
        self.rolled_at = None
        self._saved = self.config()
        self._pending_save = None
        self._new_dice()

    def config(self):
        return {"count": self.count, "faces": list(self.faces)}

    def take_save(self):
        """The config to save, once, after an accept that changed it."""
        pending = self._pending_save
        self._pending_save = None
        return pending

    def apply(self, action, now):
        if self.screen == ROLL_SCREEN:
            changed = self._roll_screen(action, now)
        else:
            changed = self._config_screen(action, now)
        if changed:
            self.changes += 1

    def _new_dice(self):
        self.dice = DiceSet(self.faces[: self.count])
        self.dice.roll_unlocked(self.randint)

    def _roll_screen(self, action, now):
        n = len(self.dice)
        if action == LEFT:
            self.cursor = (self.cursor - 1) % n
        elif action == RIGHT:
            self.cursor = (self.cursor + 1) % n
        elif action == LOCK:
            self.dice.toggle_lock(self.cursor)
        elif action == UNLOCK_ALL:
            self.dice.unlock_all()
        elif action == ROLL:
            rolled = self.dice.roll_unlocked(self.randint)
            if not rolled:
                return False
            self.rolled = rolled
            self.rolled_at = now
        elif action == CONFIGURE:
            self.screen = CONFIG_SCREEN
            self.cursor = 0
        else:
            return False
        return True

    def _config_screen(self, action, now):
        positions = self.count + 1  # the count field, then one per die
        if action == LEFT:
            self.cursor = (self.cursor - 1) % positions
        elif action == RIGHT:
            self.cursor = (self.cursor + 1) % positions
        elif action in (INC, DEC):
            step = 1 if action == INC else -1
            if self.cursor == 0:
                self.count = _clamp(self.count + step, MIN_COUNT, MAX_COUNT)
            else:
                i = self.cursor - 1
                self.faces[i] = _clamp(self.faces[i] + step, MIN_FACES, MAX_FACES)
        elif action == ACCEPT:
            self._accept(now)
        else:
            return False
        return True

    def _accept(self, now):
        config = self.config()
        if config != self._saved:
            self._saved = config
            self._pending_save = self.config()
        self._new_dice()
        self.rolled = list(range(self.count))
        self.rolled_at = now
        self.cursor = 0
        self.screen = ROLL_SCREEN
