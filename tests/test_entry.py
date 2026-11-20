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
        FakeDisplay.events.append(("init",))

    def begin_frame(self):
        FakeDisplay.events.append(("begin",))

    def end_frame(self, app, now):
        FakeDisplay.events.append(("end", app.screen, now))


@pytest.fixture
def entry(monkeypatch):
    """Load the entry file for a model; returns (module, badge, state, frame)."""

    def load(model, saved=None):
        badge = FakeBadge(model)
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
        monkeypatch.setitem(sys.modules, "display_tufty", types.SimpleNamespace(TuftyDisplay=FakeDisplay))
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


def test_display_owns_each_frame(entry):
    _, _, _, frame = entry("tufty")
    frame()
    frame()
    assert FakeDisplay.events == [("init",), ("begin",), ("end", "roll_screen", 0), ("begin",), ("end", "roll_screen", 500)]


def test_accepting_a_change_saves_it(entry):
    _, _, state, frame = entry("tufty")
    frame()
    for buttons in ([B], [], [UP], [], [B], []):
        frame(*buttons)
    assert state.saved["dice_roller"] == {"count": 5, "faces": [6] * 6}


def test_saved_config_is_loaded_and_repaired(entry):
    module, _, _, _ = entry("tufty", saved={"dice_roller": {"count": 99, "faces": [20]}})
    assert module.app.count == 6
    assert module.app.faces == [20, 6, 6, 6, 6, 6]


def test_unsupported_model_shows_message_and_updates_display(entry):
    _, _, _, frame = entry("badger")
    frame()
    frame()
    assert any(call[0] == "text" for call in builtins.screen.calls)
    assert [c for c in builtins.display.calls if c[0] == "update"] == [("update", ())]
