"""The game: which screen is showing, the highlight, the dice and the
setup being edited. Displays read it; actions change it.

Pure Python, no Badgeware names, and nothing about saving: it starts from
a record (see saving/record.py), showing the record's last roll if it has
one, and take_save_point() says when a save is due: after every roll,
lock, unlock and accept, so a restart (or a Badger waking from sleep)
shows what was on screen. What gets saved is saving's business.

`changes` goes up whenever anything visible changes, so a display that
must not redraw every frame (e-ink) can redraw only when it moves. A roll
changes the values at once and records which dice rolled and when; any
roll animation is the display's.
"""

from game.controls import (
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
from game.dice import MAX_COUNT, MAX_FACES, MIN_COUNT, MIN_FACES, DiceSet


def _clamp(value, low, high):
    return max(low, min(high, value))


class DiceApp:
    def __init__(self, record, randint):
        """record: an already repaired saved record ({"count", "faces"},
        plus "values" and "locked" when it holds a roll)."""
        self.randint = randint
        self.count = record["count"]
        self.faces = list(record["faces"])
        self.screen = ROLL_SCREEN
        self.cursor = 0
        self.changes = 0
        self.rolled = []
        self.rolled_at = None
        self._save_point = False
        if "values" in record:
            self.dice = DiceSet(self.faces[: self.count])
            for i, die in enumerate(self.dice.dice):
                die.value = record["values"][i]
                die.locked = record["locked"][i]
        else:
            self._new_dice()

    def take_save_point(self):
        """True once after each roll, lock, unlock or accept: the moments
        worth saving."""
        due = self._save_point
        self._save_point = False
        return due

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
            self._save_point = True
        elif action == UNLOCK_ALL:
            if not any(die.locked for die in self.dice.dice):
                return False
            self.dice.unlock_all()
            self._save_point = True
        elif action == ROLL:
            rolled = self.dice.roll_unlocked(self.randint)
            if not rolled:
                return False
            self.rolled = rolled
            self.rolled_at = now
            self._save_point = True
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
        self._save_point = True
