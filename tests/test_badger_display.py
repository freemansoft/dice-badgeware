"""badger.py against a fake badge: when it refreshes the e-ink,
when it waits for a press, and what it writes.

The refresh-and-wait order matters on the Badger: its run() loop only calls
update(), so the display pushes frames, polls and waits itself. Pixels are
checked in the simulator (tests/test_sim_badger.py).
"""

import builtins
import types

import pytest
from devices import badger
from game.app import DiceApp
from game.controls import CONFIGURE, ROLL
from saving import record


class FakeScreen:
    def __init__(self):
        self.texts = []
        self.font = self.pen = self.antialias = None

    def measure_text(self, text, size):
        return (len(text) * size // 2, size)

    def text(self, text, _x, _y, _size):
        self.texts.append(text)

    def __getattr__(self, name):  # rectangle, shape, line, clear...: no-ops
        return lambda *_args: None


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
        "font": types.SimpleNamespace(load=lambda _path: object(), sins=object()),
        "image": types.SimpleNamespace(X4=4),
    }
    for name, value in fakes.items():
        monkeypatch.setattr(builtins, name, value, raising=False)
    return e


def app():
    """Four d6; every roll lands on 3."""
    return DiceApp(record.repair({"count": 4}), lambda _lo, _hi: 3)


def test_first_frame_refreshes_then_waits(env):
    d = badger.BadgerDisplay()
    d.end_frame(app(), 0)
    assert env.calls == ["update", ("wait", 30_000)]


def test_no_change_no_refresh(env):
    d = badger.BadgerDisplay()
    a = app()
    d.end_frame(a, 0)
    env.calls.clear()
    d.end_frame(a, 100)
    assert env.calls == [("wait", 30_000)]


def test_change_refreshes_once(env):
    d = badger.BadgerDisplay()
    a = app()
    d.end_frame(a, 0)
    env.calls.clear()
    a.apply(ROLL, 100)
    d.end_frame(a, 100)
    assert env.calls == ["update", ("wait", 30_000)]


def test_polls_instead_of_waiting_while_held(env):
    d = badger.BadgerDisplay()
    a = app()
    d.end_frame(a, 0)
    env.calls.clear()
    env.held = ["UP"]
    d.end_frame(a, 100)
    assert env.calls == ["poll"]


def test_press_seen_by_the_refresh_is_handled_next_frame(env):
    d = badger.BadgerDisplay()
    env.pressed = ["A"]  # the poll inside badge.update() saw A
    d.end_frame(app(), 0)
    assert env.calls == ["update"]


def test_roll_draws_final_values_and_total(env):
    a = app()
    a.apply(ROLL, 0)
    badger.BadgerDisplay().end_frame(a, 0)  # the same instant as the roll
    assert [t for t in env.screen.texts if t.isdigit()] == ["3", "3", "3", "3"]
    assert "Total  12" in env.screen.texts


def test_each_screen_names_what_its_buttons_do(env):
    a = app()
    display = badger.BadgerDisplay()
    display.end_frame(a, 0)
    roll = set(env.screen.texts)
    env.screen.texts.clear()
    a.apply(CONFIGURE, 100)
    display.end_frame(a, 100)
    setup = set(env.screen.texts)
    assert {"Roll Baby Roll", "Left", "Setup", "Right", "Lock", "hold: all", "Roll", "d6"} <= roll
    assert {"Setup", "Dice  4", "d6", "Left", "Done", "Right", "More", "Less"} <= setup
    assert not {"Lock", "hold: all", "Roll", "Roll Baby Roll"} & setup
