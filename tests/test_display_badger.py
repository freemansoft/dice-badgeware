"""display_badger.py against a fake badge: when it refreshes the e-ink,
when it waits for a press, and what it writes.

The refresh-and-wait order matters on the Badger: its run() loop only calls
update(), so the display pushes frames, polls and waits itself. Pixels are
checked in the simulator (tests/test_sim_badger.py).
"""

import builtins
import types

import dice_app
import dice_config
import display_badger
import pytest
from dice_input import ROLL


class FakeScreen:
    def __init__(self):
        self.texts = []
        self.font = self.pen = self.antialias = None

    def measure_text(self, text, size):
        return (len(text) * size // 2, size)

    def text(self, text, x, y, size):
        self.texts.append(text)

    def __getattr__(self, name):  # rectangle, shape, line, clear...: no-ops
        return lambda *args: None


class Env:
    def __init__(self):
        self.calls = []
        self.pressed = []
        self.held = []
        self.screen = FakeScreen()


@pytest.fixture
def env(monkeypatch):
    e = Env()
    badge = types.SimpleNamespace(
        default_clear=None,
        update=lambda: e.calls.append("update"),
        poll=lambda: e.calls.append("poll"),
        pressed=lambda: e.pressed,
        held=lambda: e.held,
    )
    fakes = {
        "badge": badge,
        "screen": e.screen,
        "wait_for_button_or_alarm": lambda timeout: e.calls.append(("wait", timeout)),
        "color": types.SimpleNamespace(rgb=lambda r, g, b: (r, g, b)),
        "shape": types.SimpleNamespace(rounded_rectangle=lambda *a: a, rectangle=lambda *a: a),
        "font": types.SimpleNamespace(load=lambda path: object(), sins=object()),
        "image": types.SimpleNamespace(X4=4),
    }
    for name, value in fakes.items():
        monkeypatch.setattr(builtins, name, value, raising=False)
    return e


def app():
    """Four d6; every roll lands on 3."""
    return dice_app.DiceApp(dice_config.repair({"count": 4}), lambda lo, hi: 3)


def test_first_frame_refreshes_then_waits(env):
    d = display_badger.BadgerDisplay()
    d.end_frame(app(), 0)
    assert env.calls == ["update", ("wait", 30_000)]


def test_no_change_no_refresh(env):
    d = display_badger.BadgerDisplay()
    a = app()
    d.end_frame(a, 0)
    env.calls.clear()
    d.end_frame(a, 100)
    assert env.calls == [("wait", 30_000)]


def test_change_refreshes_once(env):
    d = display_badger.BadgerDisplay()
    a = app()
    d.end_frame(a, 0)
    env.calls.clear()
    a.apply(ROLL, 100)
    d.end_frame(a, 100)
    assert env.calls.count("update") == 1


def test_polls_instead_of_waiting_while_held(env):
    d = display_badger.BadgerDisplay()
    a = app()
    d.end_frame(a, 0)
    env.calls.clear()
    env.held = ["UP"]
    d.end_frame(a, 100)
    assert env.calls == ["poll"]


def test_press_seen_by_the_refresh_is_handled_next_frame(env):
    d = display_badger.BadgerDisplay()
    env.pressed = ["A"]  # the poll inside badge.update() saw A
    d.end_frame(app(), 0)
    assert env.calls == ["update"]


def test_roll_draws_final_values_and_total(env):
    a = app()
    a.apply(ROLL, 0)
    display_badger.BadgerDisplay().end_frame(a, 0)  # the same instant as the roll
    assert [t for t in env.screen.texts if t.isdigit()] == ["3", "3", "3", "3"]
    assert "Total  12" in env.screen.texts
