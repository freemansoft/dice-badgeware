"""The saved dice configuration: defaults, and repair of whatever was read.

Saved by __init__.py with Badgeware's State helper under STATE_NAME
(/state/dice_roller.json) as {"count": 2-6, "faces": [six ints 4-20]},
plus the last roll when there is one: "values" (six ints, each 1 up to
its slot's faces) and "locked" (six bools). Every list covers all six
slots, so dice dropped by lowering the count keep their faces and their
last roll. Pure Python, no Badgeware names.
"""

from dice import DEFAULT_FACES, MAX_DICE, MAX_FACES, MIN_FACES

STATE_NAME = "dice_roller"
MIN_COUNT = 2
MAX_COUNT = MAX_DICE
DEFAULT_COUNT = 4


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
