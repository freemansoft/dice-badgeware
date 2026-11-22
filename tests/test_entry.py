"""apps/dice_roller/__init__.py against a fake Badgeware.

The entry file is the only one that touches the badge, so it is loaded
here with stand-ins for the Badgeware builtins and a fake display module,
and driven frame by frame.
"""

import builtins
import importlib.util
import sys
import types
from typing import ClassVar

import pytest
from conftest import ROOT

ENTRY = ROOT / "apps" / "dice_roller" / "__init__.py"
A, B, C, UP, DOWN = 1, 2, 3, 4, 5


class FakeBadge:
    def __init__(self, model):
        self.model = model
        self.ticks = 0
        self.down = set()
        self.went_down = set()
        self.woken = False

    def woken_by_button(self):
        return self.woken

    def pressed(self):
        return list(self.went_down)

    def held(self):
        return list(self.down)


class FakeState:
    def __init__(self):
        self.saved = {}

    def load(self, name, data):
        data.update(self.saved.get(name, {}))
        return name in self.saved

    def save(self, name, data):
        self.saved[name] = dict(data)


class Recorder:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def record(*args, **kwargs):
            self.calls.append((name, args))
        return record


class FakeDisplay:
    events: ClassVar[list] = []

    def __init__(self):
        FakeDisplay.events.append(("init", type(self).__name__))

    def begin_frame(self):
        FakeDisplay.events.append(("begin",))

    def end_frame(self, app, now):
        FakeDisplay.events.append(("end", app.screen, now))


class FakeTufty(FakeDisplay):
    pass


class FakeBadger(FakeDisplay):
    pass


@pytest.fixture
def entry(monkeypatch):
    """Load the entry file for a model; returns (module, badge, state, frame)."""

    def load(model, saved=None, woken=False):
        badge = FakeBadge(model)
        badge.woken = woken
        state = FakeState()
        state.saved.update(saved or {})
        loop = {}
        fakes = {
            "badge": badge,
            "State": state,
            "run": lambda update: loop.setdefault("update", update),
            "BUTTON_A": A, "BUTTON_B": B, "BUTTON_C": C, "BUTTON_UP": UP, "BUTTON_DOWN": DOWN,
            "color": types.SimpleNamespace(rgb=lambda *a: a),
            "screen": Recorder(),
            "display": Recorder(),
        }
        for name, value in fakes.items():
            monkeypatch.setattr(builtins, name, value, raising=False)
        FakeDisplay.events = []
        monkeypatch.setitem(sys.modules, "devices.tufty", types.SimpleNamespace(TuftyDisplay=FakeTufty))
        monkeypatch.setitem(sys.modules, "devices.badger", types.SimpleNamespace(BadgerDisplay=FakeBadger))
        spec = importlib.util.spec_from_file_location("dice_roller_entry", ENTRY)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        def frame(*buttons):
            badge.went_down = set(buttons) - badge.down
            badge.down = set(buttons)
            result = loop["update"]()
            badge.ticks += 500
            return result

        return module, badge, state, frame

    return load


@pytest.mark.parametrize(("model", "display"), [("tufty", "FakeTufty"), ("badger", "FakeBadger")])
def test_each_badge_gets_its_display_and_it_owns_each_frame(entry, model, display):
    _, _, _, frame = entry(model)
    frame()
    frame()
    assert FakeDisplay.events == [
        ("init", display), ("begin",), ("end", "roll_screen", 0), ("begin",), ("end", "roll_screen", 500),
    ]


def test_roll_saves_and_relaunch_restores(entry):
    module, _, state, frame = entry("tufty")
    frame()
    frame(UP)
    assert state.saved["dice_roller"]["locked"][0] is True  # a lock is saved
    frame()
    frame(DOWN)
    saved = state.saved["dice_roller"]
    assert saved["locked"][0] is True and len(saved["values"]) == 6
    shown = [d.value for d in module.app.dice.dice]
    again, _, _, _ = entry("tufty", saved=state.saved)
    assert [d.value for d in again.app.dice.dice] == shown
    assert again.app.dice.dice[0].locked


def test_waking_press_only_wakes(entry):
    # the badge may have slept on another screen; a press must not act on
    # a screen the user wasn't looking at
    module, _, state, frame = entry("tufty", woken=True)
    frame(DOWN)
    assert state.saved == {} and module.app.rolled == []


def test_menu_press_is_ignored_at_launch(entry):
    module, _, _, frame = entry("tufty")
    frame(B)
    assert module.app.screen == "roll_screen"


def test_saved_config_is_loaded_and_repaired(entry):
    module, _, _, _ = entry("tufty", saved={"dice_roller": {"count": 99, "faces": [20]}})
    assert module.app.count == 6
    assert module.app.faces == [20, 6, 6, 6, 6, 6]


def test_saves_keep_the_dice_beyond_the_count(entry):
    # Lowering the count and pressing Done saves; the four dice put away
    # keep their values from the loaded record in the file. (Raising the
    # count again and pressing Done re-rolls every die, so those values
    # are kept, not shown.)
    saved = {"count": 6, "faces": [6] * 6, "values": [1, 2, 3, 4, 5, 6], "locked": [False] * 6}
    _, _, state, frame = entry("tufty", saved={"dice_roller": saved})
    frame()  # launch: presses are ignored for the first 400 ms
    frame(B)
    for _ in range(4):
        frame()
        frame(DOWN)
    frame()
    frame(B)
    saved = state.saved["dice_roller"]
    assert saved["count"] == 2
    assert saved["values"][2:] == [3, 4, 5, 6]


def test_unsupported_model_shows_message_and_updates_display(entry):
    _, _, _, frame = entry("blinky")
    frame()
    frame()
    texts = [call[1][0] for call in builtins.screen.calls if call[0] == "text"]
    assert texts == ["Dice Roller:", "blinky not", "supported"] * 2
    assert [c for c in builtins.display.calls if c[0] == "update"] == [("update", ())]
