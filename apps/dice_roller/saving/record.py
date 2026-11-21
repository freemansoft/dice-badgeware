"""The saved record: what is kept between launches, as plain data.

Pure Python, no Badgeware names; saving/store.py reads and writes it on
the badge (/state/dice_roller.json, via Badgeware's State helper):

    {"count": 2-6, "faces": [six ints 4-20],
     "values": [six ints, each 1 up to its slot's faces],
     "locked": [six bools]}

"values" and "locked" hold the last roll and appear together, or not at
all (an older file, or before the first roll). Every list covers all six
slots, so dice dropped by lowering the count keep their faces and their
last roll. repair() makes whatever was read valid; snapshot() takes a new
record from the game at a save point.
"""

from game.dice import DEFAULT_COUNT, DEFAULT_FACES, MAX_COUNT, MAX_DICE, MAX_FACES, MIN_COUNT, MIN_FACES

STATE_NAME = "dice_roller"


def defaults():
    return {"count": DEFAULT_COUNT, "faces": [DEFAULT_FACES] * MAX_DICE}


def _whole(value, default, low, high):
    """value as an int clamped to low..high, or default if it isn't a finite number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    if value != value or value in (float("inf"), float("-inf")):
        return default
    return max(low, min(high, int(value)))


def repair(data):
    """A new, valid config built from data, whatever data is. Never raises."""
    if not isinstance(data, dict):
        return defaults()
    count = _whole(data.get("count"), DEFAULT_COUNT, MIN_COUNT, MAX_COUNT)
    faces = data.get("faces")
    if not isinstance(faces, list):
        faces = []
    faces = [_whole(f, DEFAULT_FACES, MIN_FACES, MAX_FACES) for f in faces[:MAX_DICE]]
    faces += [DEFAULT_FACES] * (MAX_DICE - len(faces))
    repaired = {"count": count, "faces": faces}
    values = data.get("values")
    if isinstance(values, list) and len(values) == MAX_DICE:
        repaired["values"] = [_whole(v, 1, 1, faces[i]) for i, v in enumerate(values)]
        locked = data.get("locked")
        if isinstance(locked, list) and len(locked) == MAX_DICE:
            repaired["locked"] = [x is True for x in locked]
        else:
            repaired["locked"] = [False] * MAX_DICE
    return repaired


def snapshot(app, previous):
    """The record to save now: the game's setup and dice, with any slots
    beyond the dice in play kept from the previous record."""
    values = list(previous.get("values", [1] * MAX_DICE))
    locked = list(previous.get("locked", [False] * MAX_DICE))
    for i, die in enumerate(app.dice.dice):
        values[i] = die.value
        locked[i] = die.locked
    return {"count": app.count, "faces": list(app.faces), "values": values, "locked": locked}
