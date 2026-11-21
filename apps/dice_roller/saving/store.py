"""Reads and writes the saved record on the badge, with Badgeware's State
helper (/state/<STATE_NAME>.json). The only file that touches State."""

from saving.record import STATE_NAME, defaults, repair


def load():
    """The saved record, repaired; the defaults if there is none."""
    data = defaults()
    State.load(STATE_NAME, data)
    return repair(data)


def save(record):
    State.save(STATE_NAME, record)
