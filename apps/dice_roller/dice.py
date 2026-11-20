"""Dice: one Die and the DiceSet on the table.

Pure Python, no Badgeware names, so it runs under CPython for tests.
`randint(lo, hi)` is passed in (inclusive, like random.randint) so tests
can make rolls predictable.
"""

MIN_FACES = 4
MAX_FACES = 20
DEFAULT_FACES = 6
MAX_DICE = 6


class Die:
    def __init__(self, faces, value=1):
        self.faces = faces
        self.value = value
        self.locked = False

    def roll(self, randint):
        """Roll unless locked. Returns True if the die rolled."""
        if self.locked:
            return False
        self.value = randint(1, self.faces)
        return True

    def toggle_lock(self):
        self.locked = not self.locked


class DiceSet:
    def __init__(self, faces_list):
        self.dice = [Die(faces) for faces in faces_list]

    def __len__(self):
        return len(self.dice)

    def roll_unlocked(self, randint):
        """Roll every unlocked die; return the indices that rolled."""
        return [i for i, die in enumerate(self.dice) if die.roll(randint)]

    def toggle_lock(self, index):
        self.dice[index].toggle_lock()

    def unlock_all(self):
        for die in self.dice:
            die.locked = False

    def total(self):
        return sum(die.value for die in self.dice)
