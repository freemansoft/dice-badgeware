"""What display_tufty.py writes on the roll screen, against a fake screen.

The simulator tests check pixels after the roll animation has ended; these
check the text drawn during it, which the simulator can't time reliably.
"""

import builtins
import types

import dice_app
import dice_config
import display_tufty as tufty
import pytest
from dice_input import LOCK, ROLL

ROLLED_AT = 1000
REAL = 3     # every roll lands on 3
FLICKER = 6  # every flicker frame shows 6


class FakeScreen:
    def __init__(self):
        self.texts = []
        self.font = self.pen = self.antialias = None

    def measure_text(self, text, size):
        return (len(text) * size // 2, size)

    def text(self, text, x, y, size):
        self.texts.append(text)

    def rectangle(self, *args):
        pass

    def shape(self, *args):
        pass


@pytest.fixture
def screen(monkeypatch):
    fake = FakeScreen()
    fakes = {
        "screen": fake,
        "badge": types.SimpleNamespace(mode=lambda m: None, default_clear=None),
        "color": types.SimpleNamespace(rgb=lambda r, g, b: (r, g, b)),
        "shape": types.SimpleNamespace(rounded_rectangle=lambda *a: a),
        "font": types.SimpleNamespace(load=lambda path: object(), sins=object()),
        "image": types.SimpleNamespace(X4=4),
        "HIRES": 1,
    }
    for name, value in fakes.items():
        monkeypatch.setattr(builtins, name, value, raising=False)
    monkeypatch.setattr(tufty, "random", types.SimpleNamespace(randint=lambda lo, hi: FLICKER))
    return fake


def rolled_app():
    """Four d6, the first locked, just rolled at ROLLED_AT."""
    app = dice_app.DiceApp(dice_config.repair({"count": 4}), lambda lo, hi: REAL)
    app.apply(LOCK, ROLLED_AT)
    app.apply(ROLL, ROLLED_AT)
    return app


def test_total_matches_the_flickering_dice_during_the_roll(screen):
    tufty.TuftyDisplay().draw(rolled_app(), ROLLED_AT + 100)
    # the locked die shows its real 3; the three that rolled flicker 6s
    assert [t for t in screen.texts if t.isdigit()] == ["3", "6", "6", "6"]
    assert "Total  21" in screen.texts
    assert "Total  12" not in screen.texts  # the real result stays hidden


def test_total_is_the_real_result_once_the_roll_ends(screen):
    tufty.TuftyDisplay().draw(rolled_app(), ROLLED_AT + tufty.ROLL_ANIM_MS)
    assert [t for t in screen.texts if t.isdigit()] == ["3", "3", "3", "3"]
    assert "Total  12" in screen.texts
