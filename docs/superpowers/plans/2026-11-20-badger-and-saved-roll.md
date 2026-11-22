# Badger 2350 Support and Saved Last Roll Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Save the last roll (values and locks) with the setup on every badge, restore it at launch, and add a Badger 2350 e-ink display, testable in the local simulator.

**Architecture:**

- The plain-Python core learns to restore and save a roll:
  - `dice_config.repair` accepts `values` and `locked`;
  - `DiceApp` restores them and queues a save after each roll and each accept;
  - `InputMapper` gets a configurable ignore window.
- A new `display_badger.py` implements the existing `begin_frame` / `end_frame` contract for e-ink:
  - it refreshes only on change;
  - it uses no animation;
  - it waits with the firmware's `wait_for_button_or_alarm`.
- The simulator gains a `badger` model alongside `tufty`.

**Tech Stack:** MicroPython (Badgeware v3.1.1), CPython 3 + pytest for host tests, Node 18+ for the badgeware-wasm simulator, ruff, mpy-cross, gh CLI.

**Spec:** `docs/superpowers/specs/2026-11-20-badger-and-saved-roll-design.md` (builds on `docs/superpowers/specs/2026-11-19-dice-roller-design.md`)

## Global Constraints

**Code**

- Core files (`dice*.py`) use no Badgeware names. Only `__init__.py` and `display_*.py` touch the badge.
- App code must compile with mpy-cross and pass `ruff check --config vendor/tufty2350/ci/ruff.toml apps/dice_roller`.
  - No `zip(strict=)`.
  - Use `"{}".format()`, which the firmware's ruff rules accept.
- Tools and tests must pass `ruff check tools tests`.

**Saved file**

- The file is `/state/dice_roller.json`:
  `{"count", "faces": [6], "values": [6], "locked": [6]}`.
- `values` and `locked` appear together, or not at all.
- Saved after every roll that rolled at least one die, and after Setup → Done.
- Never saved on lock, unlock all, a highlight move, or a Setup edit.

**Badger behaviour**

- Badger shades, equal-channel only:
  - BLACK (0,0,0)
  - DARK (96,96,96)
  - LIGHT (160,160,160)
  - WHITE (255,255,255)
- Never `color.light_grey`.
- Badger: no roll animation. Dice and the total go straight to their new values.
- Badger: never call `badge.mode(HIRES)`.
- Badger sleep timeout: 30 000 ms, through `wait_for_button_or_alarm(timeout=…)`.
- Presses during a Badger refresh are dropped. Refreshes block, using the default mode.

**Tufty**

- The Tufty's look and animation are unchanged.

**Simulator**

- `sim/` is Pimoroni's code plus our loader. Don't lint `sim/`.

## Review Focus

1. **An old save file** (no `values`) keeps its setup and rolls fresh, without crashing. Covered by Task 1, `test_old_file_has_no_roll`.
2. **A hand-edited file whose values exceed their faces** (e.g. value 9 on a d4) is clamped and still shows. Covered by Task 1, `test_values_clamped_to_their_faces`.
3. **Lowering the count, then rolling**, keeps the hidden dice's saved values. Covered by Task 2, `test_hidden_slots_keep_saved_values`.
4. **Rolling with every die locked** doesn't save, so it doesn't wear the flash for nothing. Covered by Task 2, `test_all_locked_roll_does_not_save`.
5. **Holding UP on the Badger** still unlocks all, even though the badge waits for presses between refreshes. Covered by Task 4, `test_polls_instead_of_waiting_while_held`, and the Task 5 sim test `test_badger_long_up_unlocks_all`.

---

### Task 1: Saved roll in the repaired config

**Files:**

- Modify: `apps/dice_roller/dice_config.py` (`repair`, module docstring)
- Test: `tests/test_dice_config.py`

**Interfaces:**

- Produces: `repair(data) -> dict`.
  - It always has `count` (int 2–6) and `faces` (6 ints, 4–20).
  - When a saved roll survives, it also has `values` (6 ints, each 1..faces[i]) and `locked` (6 bools).
  - The keys are absent otherwise.
  - It never raises.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_dice_config.py`)

```python
ROLL = {"count": 4, "faces": [6] * 6, "values": [3, 5, 1, 6, 2, 2],
        "locked": [False, True, False, False, False, False]}


def test_saved_roll_kept():
    r = dice_config.repair(ROLL)
    assert r["values"] == [3, 5, 1, 6, 2, 2]
    assert r["locked"] == [False, True, False, False, False, False]


def test_old_file_has_no_roll():
    assert dice_config.repair({"count": 3, "faces": [8] * 6}) == {"count": 3, "faces": [8] * 6}


@pytest.mark.parametrize("values", [[1, 2, 3], "x", None, [1] * 7])
def test_bad_values_mean_no_roll(values):
    r = dice_config.repair({**ROLL, "values": values})
    assert "values" not in r and "locked" not in r


def test_values_clamped_to_their_faces():
    r = dice_config.repair({"count": 6, "faces": [4, 20, 6, 6, 6, 6],
                            "values": [9, 0, "x", 6, None, 2.7], "locked": [False] * 6})
    assert r["values"] == [4, 1, 1, 6, 1, 2]


def test_locked_only_true_counts():
    r = dice_config.repair({**ROLL, "locked": [True, 1, "yes", None, False, True]})
    assert r["locked"] == [True, False, False, False, False, True]


@pytest.mark.parametrize("locked", [None, [True], "x"])
def test_bad_locked_means_unlocked(locked):
    data = dict(ROLL)
    if locked is None:
        del data["locked"]
    else:
        data["locked"] = locked
    assert dice_config.repair(data)["locked"] == [False] * 6
```

(Add `import pytest` at the top if it isn't there.)

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/pytest tests/test_dice_config.py -q`
Expected: the new tests FAIL (KeyError `values` / extra keys); old tests pass.

- [ ] **Step 3: Implement in `repair`**
  - **values:** a `list` of exactly `MAX_DICE` entries is kept. Each entry goes through `_whole(v, 1, 1, faces[i])`, after `faces` is repaired.
  - **locked:** a `list` of exactly `MAX_DICE` entries gives `[x is True for x in locked]`. Anything else gives `[False] * MAX_DICE`.
  - **Docstring:** describe the two new keys.

- [ ] **Step 4: Run to verify they pass**

Run: `.venv/bin/pytest tests/test_dice_config.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add apps/dice_roller/dice_config.py tests/test_dice_config.py
git commit -m "Saved config can carry the last roll: values and locks, repaired on load"
```

---

### Task 2: DiceApp restores the roll and saves after each roll

**Files:**

- Modify: `apps/dice_roller/dice_app.py`
- Test: `tests/test_dice_app.py` (replace `test_take_save`; add the tests below)

**Interfaces:**

- Consumes: the `repair()` output from Task 1.
- Produces:
  - `DiceApp(config, randint)`:
    - when `"values" in config`, it shows `values[:count]` and `locked[:count]` without calling `randint`;
    - `rolled == []`, `rolled_at is None`, `screen == ROLL_SCREEN`, `cursor == 0`;
    - otherwise it rolls fresh, as today.
  - `take_save()` returns `{"count", "faces", "values", "locked"}` (6-entry lists, new list objects) once after:
    - a ROLL that rolled at least one die;
    - every ACCEPT.

    It returns `None` otherwise.

  - Slots beyond `count` keep their values and locks from the config, defaulting to `1` and `False`.

- [ ] **Step 1: Write the failing tests**

```python
def never(lo, hi):
    raise AssertionError("rolled")


def saved_roll(count=3, values=(2, 5, 4, 1, 1, 1), locked=(False, True) + (False,) * 4):
    return dice_config.repair({"count": count, "faces": [6] * 6,
                               "values": list(values), "locked": list(locked)})


def test_restores_saved_roll_without_rolling():
    a = dice_app.DiceApp(saved_roll(), never)
    assert values(a) == [2, 5, 4]
    assert [d.locked for d in a.dice.dice] == [False, True, False]
    assert a.rolled == [] and a.rolled_at is None
    assert a.screen == ROLL_SCREEN and a.cursor == 0


def test_roll_queues_save_with_values_and_locks():
    a = make(count=3)
    a.apply(LOCK, 0)
    a.box[0] = 5
    a.apply(ROLL, 10)
    assert a.take_save() == {"count": 3, "faces": [6] * 6, "values": [3, 5, 5, 1, 1, 1],
                             "locked": [True, False, False, False, False, False]}
    assert a.take_save() is None


def test_lock_and_unlock_do_not_save():
    a = make()
    for action in (LOCK, RIGHT, LOCK, UNLOCK_ALL, LEFT):
        a.apply(action, 0)
    assert a.take_save() is None


def test_all_locked_roll_does_not_save():
    a = make(count=2)
    a.apply(LOCK, 0)
    a.apply(RIGHT, 0)
    a.apply(LOCK, 0)
    a.apply(ROLL, 0)
    assert a.take_save() is None


def test_accept_always_saves_the_new_roll():
    a = make(count=2)
    a.apply(LOCK, 0)
    a.apply(CONFIGURE, 0)
    a.box[0] = 4
    a.apply(ACCEPT, 0)
    saved = a.take_save()
    assert saved["values"][:2] == [4, 4] and saved["locked"] == [False] * 6


def test_hidden_slots_keep_saved_values():
    a = dice_app.DiceApp(saved_roll(count=2, values=(2, 3, 4, 5, 6, 1), locked=(False,) * 6),
                         lambda lo, hi: 1)
    a.apply(ROLL, 0)
    assert a.take_save()["values"] == [1, 1, 4, 5, 6, 1]
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/pytest tests/test_dice_app.py -q`
Expected: the new tests FAIL (restore rolls with `never`; take_save returns `None` after a roll).

- [ ] **Step 3: Implement in `dice_app.py`**
  - Keep 6-slot lists `self._values` and `self._locked`, from the config or defaults.
  - Build the dice from them when restoring.
  - `_queue_save()` copies the shown dice into the first `count` slots and sets `_pending_save`. Call it from ROLL (only when `rolled`) and from `_accept`.
  - Drop the `_saved` comparison.
  - Update the module docstring: the core now restores and saves the last roll.

- [ ] **Step 4: Run to verify they pass**

Run: `.venv/bin/pytest tests/test_dice_app.py -q`
Expected: all pass, including the edited `test_take_save` replacement.

- [ ] **Step 5: Commit**

```bash
git add apps/dice_roller/dice_app.py tests/test_dice_app.py
git commit -m "Restore the saved roll at launch; save after each roll and accept"
```

---

### Task 3: The waking press counts; entry saves and restores the roll

**Files:**

- Modify: `apps/dice_roller/dice_input.py` (`InputMapper.__init__`)
- Modify: `apps/dice_roller/__init__.py`
- Test: `tests/test_dice_input.py`, `tests/test_entry.py`

**Interfaces:**

- Consumes: Task 2's `DiceApp` and `take_save`.
- Produces: `InputMapper(ignore_ms=STARTUP_IGNORE_MS)`. Inputs are ignored while `now - start < ignore_ms`.
- `__init__.py` passes `0` when `badge.woken_by_button()` is true.
- The fake `FakeBadge` in `tests/test_entry.py` gains a `woken` flag and `woken_by_button()`. The `entry` loader gains `woken=False`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_dice_input.py`:

```python
def test_no_ignore_window_when_woken():
    m = InputMapper(ignore_ms=0)
    assert m.actions(ROLL_SCREEN, {B}, {B}, 0) == [CONFIGURE]
```

In `tests/test_entry.py`:

- Replace `test_saves_only_when_a_change_is_accepted`.
- Add `woken` support to `FakeBadge` and to the `entry` loader.

```python
def test_roll_saves_and_relaunch_restores(entry):
    module, _, state, frame = entry("tufty")
    frame()
    frame(UP)
    frame()
    assert state.saved == {}  # a lock alone is not saved
    frame(DOWN)
    saved = state.saved["dice_roller"]
    assert saved["locked"][0] is True and len(saved["values"]) == 6
    shown = [d.value for d in module.app.dice.dice]
    again, _, _, _ = entry("tufty", saved=state.saved)
    assert [d.value for d in again.app.dice.dice] == shown
    assert again.app.dice.dice[0].locked


def test_waking_press_is_not_ignored(entry):
    module, _, _, frame = entry("tufty", woken=True)
    frame(B)
    assert module.app.screen == "config_screen"


def test_menu_press_is_ignored_at_launch(entry):
    module, _, _, frame = entry("tufty")
    frame(B)
    assert module.app.screen == "roll_screen"
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/pytest tests/test_dice_input.py tests/test_entry.py -q`
Expected: FAIL. `InputMapper` takes no `ignore_ms`, and the entry ignores the waking B.

- [ ] **Step 3: Implement**
  - Add the `ignore_ms` parameter.
  - In `__init__.py`: `InputMapper(0 if badge.woken_by_button() else STARTUP_IGNORE_MS)`. Import `STARTUP_IGNORE_MS`.
  - Saving already goes through `take_save`, so no other change is needed.
  - Update the README's "Saved setup" section (spec: "What is not saved"):
    - the new JSON;
    - that the last roll and locks come back at launch;
    - that changes before Done, locks changed since the last roll, and the highlight position are not saved.

- [ ] **Step 4: Run to verify they pass**

Run: `.venv/bin/pytest -q`
Expected: all pass (sim tests included).

- [ ] **Step 5: Commit**

```bash
git add apps/dice_roller/dice_input.py apps/dice_roller/__init__.py tests/test_dice_input.py tests/test_entry.py README.md
git commit -m "The press that wakes the badge acts; document what is saved"
```

---

### Task 4: Badger simulator

**Files:**

- Create: submodule `vendor/badger2350` (pimoroni/badger2350 at `v3.1.1`)
- Create: `sim/wasm/badger/micropython.{mjs,wasm}` (fetched)
- Modify: `sim/wasm/VERSION.json` (fetched)
- Modify: `sim/stage.py` (`MODELS`, `LANDING`)
- Modify: `sim/run_headless.mjs` (`MODELS`, `--state`, frames without a refresh, `refreshes`, `state` output)
- Modify: `sim/index.html` (canvas aspect ratio from the blit size)
- Create: `tests/simrun.py`
- Modify: `tests/test_sim.py` (use `tests/simrun.py`)
- Create: `tests/test_sim_badger.py`

**Interfaces:**

- Produces: `node sim/run_headless.mjs --model badger --steps … --frames out.json [--state in.json]`.
  - Before boot, `--state` writes that file to `/state/dice_roller.json`.
  - Output gains `"refreshes"`: frames blitted during each step, `len == steps + 1`. Entry 0 is the count before the first settle.
  - Output gains `"state"`: the text of `/state/dice_roller.json` at the end, or `null`.
  - A step with no new frame pushes the latest frame again, instead of failing.
- Produces: `tests/simrun.py` with `simulate(model, steps, out_path, state_path=None) -> dict`, the parsed output.
  - It asserts that the output file exists, that status is `"ok"`, and that no log line contains `"- ERROR"`.

- [ ] **Step 1: Fetch the firmware and build**

```bash
git submodule add https://github.com/pimoroni/badger2350 vendor/badger2350
git -C vendor/badger2350 checkout -q v3.1.1
python3 tools/update_sim.py --run 35841227054 --firmware-tag v3.1.1 --models tufty,badger
```

Expected:

- `sim/wasm/badger/micropython.wasm` exists.
- `VERSION.json` has `"firmware": {"badger": "v3.1.1", "tufty": "v3.1.1"}`.
- `git diff --stat sim/wasm/tufty` is empty.

If `update_sim.py` does not know `badger`, fix it there, with a test in `tests/test_update_sim.py`.

- [ ] **Step 2: Write the failing sim test** (`tests/test_sim_badger.py`)

```python
def test_badger_boots_and_draws(tmp_path):
    result = simulate("badger", "", tmp_path / "f.json")
    assert (result["width"], result["height"]) == (264, 176)
    assert len(result["frames"]) == 1
```

Skip the test without Node, as `test_sim.py` does.

- [ ] **Step 3: Run to verify it fails**

Run: `.venv/bin/pytest tests/test_sim_badger.py -q`
Expected: FAIL (`badger` not in `MODELS`, or `sim/dist/badger` missing).

- [ ] **Step 4: Implement the simulator changes**
  - Change the four sim files listed under Files.
  - Move the shared runner out of `tests/test_sim.py` into `tests/simrun.py`, keeping the Tufty tests' behaviour.
  - `index.html` sets `canvas.style.aspectRatio = w + " / " + h` on each blit.
  - If the Badger build needs host functions the Tufty's didn't, add them to `run_headless.mjs` and `index.html`, and note why in a comment.
  - At this point the app shows the "not supported" message on the Badger. That is the expected frame.

- [ ] **Step 5: Run to verify it passes**

Run: `.venv/bin/pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add .gitmodules vendor/badger2350 sim tests
git commit -m "Simulator: add the Badger 2350 (badgeware-wasm build and firmware v3.1.1)"
```

---

### Task 5: Badger display

**Files:**

- Create: `apps/dice_roller/display_badger.py`
- Modify: `apps/dice_roller/__init__.py` (`DISPLAYS`, import)
- Test: `tests/test_display_badger.py` (host, fake badge), `tests/test_sim_badger.py` (pixels), `tests/test_entry.py`

**Interfaces:**

- Consumes:
  - `DiceApp` fields: `screen`, `cursor`, `count`, `faces`, `dice`, `changes`;
  - `LABELS` and `HOLD_LABELS`;
  - `grid_slots`;
  - the simulator runner from Task 4.
- Produces: `display_badger.BadgerDisplay` with `begin_frame()` and `end_frame(app, now)`.
- Produces: module constants that tests import.

| Constant                          | Value                                              |
| --------------------------------- | -------------------------------------------------- |
| `WIDTH`                           | 264                                                |
| `HEIGHT`                          | 176                                                |
| `HEADER_H`                        | 22                                                 |
| `BAR_TOP`                         | 158                                                |
| `COLUMN_LEFT`                     | 218                                                |
| `DICE_AREA`                       | `(0, 22, 218, 136)`                                |
| `LABEL_X`                         | `{A: 44, B: 128, C: 212}`                          |
| `LABEL_Y`                         | `{UP: 58, DOWN: 142}`                              |
| `BLACK`, `DARK`, `LIGHT`, `WHITE` | the four shades from Global Constraints            |
| `BODY_INSET`                      | 7 (the die body is `half - 7`)                     |
| `LOCK_INSET`                      | 3 (the locked grey box is `half - 3`)              |
| `FRAME_OUT`                       | 1 (the highlight ring runs from `half + 1` inward) |
| `FRAME_W`                         | 3                                                  |
| `SLEEP_AFTER_MS`                  | 30_000                                             |

These values fit 2–6 dice inside `DICE_AREA`. For 4 dice, `grid_slots` gives `half` = 28. Fonts and sizes are the builder's choice.

- [ ] **Step 1: Write the failing host tests** (`tests/test_display_badger.py`)

Build an `env` fixture and set its fakes on `builtins`, as `tests/test_display_tufty.py` does. It needs `screen`, `color`, `shape`, `font` and `image`, plus:

| Fake                                | What it does                                                                                                                    |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `env.calls`                         | One list that every fake appends to.                                                                                            |
| `badge.update()`                    | Appends `"update"`.                                                                                                             |
| `badge.poll()`                      | Appends `"poll"`.                                                                                                               |
| `badge.pressed()`                   | Returns `env.pressed`, initially `[]`.                                                                                          |
| `badge.held()`                      | Returns `env.held`, initially `[]`.                                                                                             |
| `wait_for_button_or_alarm(timeout)` | Appends `("wait", timeout)`.                                                                                                    |
| `env.screen`                        | A `FakeScreen` like the one in `tests/test_display_tufty.py`, recording `texts`, with `line`/`circle`/`clear` no-ops as needed. |

`app()` is `dice_app.DiceApp(dice_config.repair({"count": 4}), lambda lo, hi: 3)`.

```python
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


def test_roll_draws_final_values_and_total(env):
    a = app()  # 4 d6 at 3 each, via randint lambda lo, hi: 3
    a.apply(ROLL, 0)
    display_badger.BadgerDisplay().end_frame(a, 0)  # same instant as the roll
    assert [t for t in env.screen.texts if t.isdigit()] == ["3", "3", "3", "3"]
    assert "Total  12" in env.screen.texts
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/pytest tests/test_display_badger.py -q`
Expected: FAIL (`ModuleNotFoundError: display_badger`).

- [ ] **Step 3: Implement `BadgerDisplay`**

`__init__`:

- set `badge.default_clear` to the white pen and `screen.antialias = image.X4`;
- load MonaSans, falling back to `font.sins`;
- precompute `grid_slots` layouts for 2–6 dice;
- don't call `badge.mode`.

`begin_frame`: does nothing.

`end_frame`: the refresh-and-wait order is not derivable from the tests alone, so follow it exactly:

```python
def end_frame(self, app, now):
    fresh = False
    if self.drawn is None or app.changes != self.drawn:
        self.draw(app)
        badge.update()  # pushes, clears the buffer, polls
        self.drawn = app.changes
        fresh = True
    if fresh and (badge.pressed() or badge.held()):
        return  # the poll inside update() saw a button: handle it next frame
    if badge.held():
        badge.poll()  # keep polling so a long press is measured
        return
    wait_for_button_or_alarm(timeout=SLEEP_AFTER_MS)
```

The drawing follows the spec's "Badger screen" section:

- a white background;
- the roll header is BLACK with WHITE text: "Roll Baby Roll" on the left, "Total N" on the right;
- the setup header is DARK with WHITE text: "Setup" on the left, "Dice N" on the right. When the cursor is 0, the count sits in a WHITE pill with BLACK text;
- an unlocked die is a WHITE body with a 2 px BLACK outline, a BLACK value and a "dN" label;
- a locked die adds a LIGHT box, filled at `half - LOCK_INSET` and drawn before the body;
- the highlight is a BLACK ring, `FRAME_W` wide, with its outer edge at `half + FRAME_OUT`;
- labels come from `LABELS` and `HOLD_LABELS`, in BLACK, centred on `LABEL_X` along the bottom bar and on `LABEL_Y` at the column centre `(COLUMN_LEFT + WIDTH) // 2`;
- a 1 px BLACK line separates the bars from the dice area.

- [ ] **Step 4: Register it and update the entry tests**
  - In `__init__.py`: `DISPLAYS = {"tufty": TuftyDisplay, "badger": BadgerDisplay}`.
  - In `tests/test_entry.py`:
    - stub `display_badger` in `sys.modules` like `display_tufty`;
    - `test_unsupported_model_shows_message_and_updates_display` uses `"blinky"`;
    - add a test that `entry("badger")` gets the fake display's events.

- [ ] **Step 5: Write the Badger sim tests** (append to `tests/test_sim_badger.py`)

Sequences are shared and cached per module, as in `test_sim.py`. Shade bands:

- black, every channel < 40;
- dark, 41–120;
- light, 121–215;
- white, > 215.

Probe points:

- a die body: `cx, cy + half - BODY_INSET - 3`, which is inside the body and below the value text;
- a locked box: `cx, cy - half + 1`, inside the grey band.

Tests:

- `test_badger_boots_to_four_white_dice`: at boot, four bodies are white and none has a light-grey box.
- `test_badger_labels_beside_every_button`: dark pixels near every `LABEL_X` and `LABEL_Y`, on both screens.
- `test_badger_lock_draws_grey_box` (steps `UP`): die 0 has a light box and a white body; die 1 has no box.
- `test_badger_long_up_unlocks_all` (steps `UP,C,UP:1200`): after the last step, no die has a box.
- `test_badger_setup_header_is_dark_grey` (steps `B`): the header pixel at `(4, 4)` is dark; on the roll screen it is black.
- `test_badger_roll_refreshes_once` (steps `DOWN`): `refreshes[1] == 1`.
- `test_badger_relaunch_restores_the_roll`:
  - Run 1 uses steps `UP,DOWN` and writes `state`.
  - Run 2 uses `--state` with that text and steps `""`.
  - Run 2's `frames[0]` must equal run 1's last frame.
  - `json.loads(state)["locked"][0] is True`.

- [ ] **Step 6: Run everything**

Run:

```bash
.venv/bin/pytest -q
.venv/bin/ruff check --config vendor/tufty2350/ci/ruff.toml apps/dice_roller
.venv/bin/ruff check tools tests
for f in apps/dice_roller/*.py; do .venv/bin/python -m mpy_cross -o /dev/null "$f"; done
```

Expected: all pass. Lint is clean, and mpy-cross reports nothing.

- [ ] **Step 7: Commit**

```bash
git add apps/dice_roller tests
git commit -m "Badger 2350 display: four greys, grey box for locked dice, refresh only on change"
```

---

### Task 6: Docs

**Files:**

- Modify: `README.md`
- Modify: `apps/dice_roller/__init__.py` docstring
- Modify: `display_tufty.py` docstring, only if it mentions Badger plans

- [ ] **Step 1: Update the README**
  - Add the Badger to the intro and to Install (the drive is named `BADGER`; `tools/install.py` already finds it).
  - Add a "Badger notes" paragraph:
    - there is no roll animation;
    - each change is a full refresh of about a second;
    - presses during a refresh are dropped;
    - hold UP until the screen has changed twice to unlock all;
    - the badge sleeps after 30 s on battery, and any button wakes it where you left off.
  - Under Simulator: `http://localhost:8000/badger/` and `--model badger`.
  - Under Updating the simulator: `--models tufty,badger`, and committing `vendor/badger2350`.
  - Under Adding a badge: the Badger is done; Blinky remains.

- [ ] **Step 2: Verify**

Run: `.venv/bin/pytest -q && git diff --stat`
Expected: all pass; only doc files changed.

- [ ] **Step 3: Commit**

```bash
git add README.md apps/dice_roller/__init__.py
git commit -m "README: Badger 2350 support, simulator and notes"
```
