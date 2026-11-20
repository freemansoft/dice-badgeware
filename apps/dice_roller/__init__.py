"""Dice Roller for Badgeware.

Two to six dice, 4 to 20 faces each. Roll screen: A/C move, UP locks
the highlighted die (hold UP: unlock all), DOWN rolls the unlocked dice,
B opens configure. Configure: A/C move, UP/DOWN change, B accepts.

This file is the only one that touches the badge's buttons, model and
saved state. The dice, screens, buttons and layout are plain Python
(dice*.py); drawing is per badge (display_<model>.py), picked below from
badge.model. To support another badge, write its display file and add
it to DISPLAYS.
"""

import os
import random

import dice_config
from dice_app import DiceApp
from dice_input import InputMapper
from display_tufty import TuftyDisplay

DISPLAYS = {"tufty": TuftyDisplay}

BUTTONS = {
    BUTTON_A: "A",
    BUTTON_B: "B",
    BUTTON_C: "C",
    BUTTON_UP: "UP",
    BUTTON_DOWN: "DOWN",
}

try:
    random.seed(int.from_bytes(os.urandom(4), "little"))
except Exception:  # noqa: BLE001 - keep MicroPython's own seed
    pass


def _names(buttons):
    return {BUTTONS[b] for b in buttons if b in BUTTONS}


display_class = DISPLAYS.get(badge.model)

if display_class is None:

    def update():
        screen.pen = color.rgb(255, 255, 255)
        screen.text("Dice Roller: {} not supported yet".format(badge.model), 4, 4)

else:
    config = dice_config.defaults()
    State.load(dice_config.STATE_NAME, config)
    config = dice_config.repair(config)

    app = DiceApp(config, random.randint)
    inputs = InputMapper()
    display = display_class()

    def update():
        now = badge.ticks
        pressed = _names(badge.pressed())
        held = _names(badge.held())
        for action in inputs.actions(app.screen, pressed, held, now):
            app.apply(action, now)
        saved = app.take_save()
        if saved is not None:
            State.save(dice_config.STATE_NAME, saved)
        display.draw(app, now)


run(update)
