"""Dice Roller for Badgeware.

Two to six dice, 4 to 20 faces each. Roll screen: A/C move, UP locks the
highlighted die (hold UP: unlock all), DOWN rolls the unlocked dice, B
opens Setup. Setup: A/C move, UP/DOWN change, B accepts.

This file only connects the pieces and runs the loop:

    game/     the rules and screens (plain Python, every badge)
    saving/   the saved record and reading/writing it on the badge
    devices/  buttons and one display per badge, picked by badge.model
"""

import os
import random

from devices import buttons, display_for
from game.app import DiceApp
from game.controls import InputMapper
from saving import store
from saving.record import snapshot

try:
    random.seed(int.from_bytes(os.urandom(4), "little"))
except Exception:  # noqa: BLE001 - keep MicroPython's own seed
    pass

record = store.load()
app = DiceApp(record, random.randint)
inputs = InputMapper()
view = display_for(badge.model)


def update():
    global record
    view.begin_frame()
    now = badge.ticks
    for action in inputs.actions(app.screen, buttons.pressed(), buttons.held(), now):
        app.apply(action, now)
    if app.take_save_point():
        record = snapshot(app, record)
        store.save(record)
    view.end_frame(app, now)


run(update)
