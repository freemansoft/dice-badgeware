"""The app's state: which screen is showing, the highlight, the dice and
the configuration being edited. Displays read it; actions change it.

Pure Python, no Badgeware names. `changes` goes up whenever anything
visible changes, so a display that must not redraw every frame (e-ink)
can redraw only when it moves. A roll changes the values at once and
records which dice rolled and when; any roll animation is the display's.

The last roll is kept: a config with "values" (see dice_config) is shown
as it was, without rolling, and take_save() hands back the config plus
the roll after every roll and every accept. Locks, highlight moves and
unaccepted setup edits are not saved on their own.
"""

from dice import MAX_DICE, MAX_FACES, MIN_FACES, DiceSet
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
        self._pending_save = None
        # the last roll for all six slots, so hidden dice keep theirs
        self._values = list(config.get("values", [1] * MAX_DICE))
        self._locked = list(config.get("locked", [False] * MAX_DICE))
        if "values" in config:
            self.dice = DiceSet(self.faces[: self.count])
            for i, die in enumerate(self.dice.dice):
                die.value = self._values[i]
                die.locked = self._locked[i]
        else:
            self._new_dice()

    def config(self):
        return {"count": self.count, "faces": list(self.faces)}

    def take_save(self):
        """The config plus the last roll, once, after a roll or an accept."""
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

    def _queue_save(self):
        for i, die in enumerate(self.dice.dice):
            self._values[i] = die.value
            self._locked[i] = die.locked
        save = self.config()
        save["values"] = list(self._values)
        save["locked"] = list(self._locked)
        self._pending_save = save

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
            self._queue_save()
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
        self._new_dice()
        self.rolled = list(range(self.count))
        self.rolled_at = now
        self.cursor = 0
        self.screen = ROLL_SCREEN
        self._queue_save()
