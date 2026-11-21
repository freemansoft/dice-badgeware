"""The badge's buttons, as the names the game uses (game/controls.py)."""

from game.controls import A, B, C, DOWN, UP

_NAMES = {
    BUTTON_A: A,
    BUTTON_B: B,
    BUTTON_C: C,
    BUTTON_UP: UP,
    BUTTON_DOWN: DOWN,
}


def _names(buttons):
    return {_NAMES[b] for b in buttons if b in _NAMES}


def pressed():
    """Buttons that went down since the last poll."""
    return _names(badge.pressed())


def held():
    """Buttons down now."""
    return _names(badge.held())


def woken_by_button():
    """True when a button press woke the badge from sleep (so that press,
    not a menu launch, is the first one the app sees)."""
    return badge.woken_by_button()
