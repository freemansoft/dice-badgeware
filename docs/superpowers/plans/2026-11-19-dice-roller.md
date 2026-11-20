# Dice Roller Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Badgeware dice app for the Tufty 2350 (up to six dice, 4–20 faces, lock/roll/configure, saved config), structured so Badger and Blinky displays can be added later, with a local updatable badgeware-wasm simulator for testing.

**Architecture:** Pure-Python core files (`dice`, `dice_config`, `dice_layout`, `dice_input`, `dice_app`) with no Badgeware dependencies, tested with pytest on the host. One display file per badge (`display_tufty.py`) that only draws, chosen in `__init__.py` from `badge.model`. A local simulator (`sim/`) runs the real firmware and the unmodified app in Pimoroni's WebAssembly build, headless under Node for tests and in a browser for looking.

**Tech Stack:** MicroPython (Badgeware firmware v3.1.1), CPython 3.11 + pytest for host tests, ruff + mpy-cross, Node 18 for the headless simulator, `gh` CLI for simulator updates.

**Spec:** `docs/superpowers/specs/2026-11-19-dice-roller-design.md`

## Global Constraints

- App folder: `apps/dice_roller/` (menu label **Dice Roller**); device path `/system/apps/dice_roller`.
- Firmware's `launch()` already `chdir`s into the app folder and puts it on `sys.path`: app modules import each other by bare name (`import dice`), no path hacks.
- Core files (`dice.py`, `dice_config.py`, `dice_layout.py`, `dice_input.py`, `dice_app.py`) must not reference any Badgeware builtin (`badge`, `screen`, `BUTTON_*`, `State`, `color`, …) and must import under CPython.
- Only `__init__.py` touches `badge.pressed/held`, `badge.model` and `State`. Only `display_*.py` draws.
- MicroPython-compatible code: no f-string `=` specifier, no `dataclasses`, no `typing` imports, no walrus in comprehensions.
- Values: dice 1–6 (default 4), faces 4–20 (default 6), any whole number; clamp, never wrap.
- Saved config: `State` name `dice_roller` → `/state/dice_roller.json`, shape `{"count": int, "faces": [6 ints]}`.
- Timings: `LONG_PRESS_MS = 800`, `STARTUP_IGNORE_MS = 400`, `ROLL_ANIM_MS = 500`.
- Lint: `.venv/bin/ruff check --config vendor/tufty2350/ci/ruff.toml apps/dice_roller`.
- Dev env: `python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt`.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **All dice locked, then DOWN:** nothing changes: no values, no animation, no change-counter bump, no crash. (Task 5)
2. **Saved file hand-edited or damaged** (count 0/99/"x", faces too short/long, strings, booleans, floats, not a dict): app starts with repaired values, never raises. (Task 2)
3. **The menu's launch press:** B (or UP) still down when the app starts must not open configure or fire unlock-all. (Task 4)
4. **Fewer dice after configure while the roll-screen highlight was on a now-missing die:** highlight resets to die 1, no IndexError. (Task 5)
5. **UP held for a long time:** unlock-all fires exactly once per hold, only on the roll screen; releasing and pressing again restarts the timer. (Task 4)

---

### Task 1: Tooling and `dice.py`

**Files:**
- Create: `.gitignore`, `requirements-dev.txt`, `apps/dice_roller/dice.py`, `tests/conftest.py`, `tests/test_dice.py`
- Create (submodule): `vendor/tufty2350` at tag `v3.1.1`

**Interfaces:**
- Produces: `dice.MIN_FACES = 4`, `MAX_FACES = 20`, `DEFAULT_FACES = 6`, `MAX_DICE = 6`; `class Die(faces: int, value: int = 1)` with attributes `faces`, `value`, `locked` (False), `roll(randint) -> bool`, `toggle_lock() -> None`; `class DiceSet(faces_list: list[int])` with `dice: list[Die]`, `__len__`, `roll_unlocked(randint) -> list[int]` (indices rolled, ascending), `toggle_lock(index) -> None`, `unlock_all() -> None`, `total() -> int`. `randint(lo, hi)` is inclusive like `random.randint`.
- `tests/conftest.py` puts `apps/dice_roller` on `sys.path` so tests `import dice` etc.

- [ ] **Step 1: Tooling**

`.gitignore`: `.venv/`, `__pycache__/`, `.pytest_cache/`, `sim/dist/`, `.DS_Store`, `.claude/settings.local.json`.
`requirements-dev.txt`: `pytest`, `ruff`, `mpy-cross`, `mpremote`.
Run: `git submodule add https://github.com/pimoroni/tufty2350 vendor/tufty2350 && git -C vendor/tufty2350 checkout v3.1.1`
Run: `python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt`
Expected: `vendor/tufty2350/ci/ruff.toml` exists; `.venv/bin/pytest --version` prints a version.

- [ ] **Step 2: Write the failing tests** in `tests/test_dice.py`

```python
def fixed(v):
    return lambda lo, hi: v

def test_die_roll_uses_one_to_faces():
    calls = []
    d = dice.Die(20)
    assert d.roll(lambda lo, hi: calls.append((lo, hi)) or 17) is True
    assert calls == [(1, 20)] and d.value == 17

def test_locked_die_does_not_roll():
    d = dice.Die(6, value=3); d.toggle_lock()
    assert d.roll(fixed(5)) is False and d.value == 3

def test_toggle_lock_twice_unlocks():
    d = dice.Die(6); d.toggle_lock(); d.toggle_lock()
    assert d.locked is False

def test_roll_unlocked_returns_rolled_indices():
    s = dice.DiceSet([6, 6, 6]); s.toggle_lock(1)
    assert s.roll_unlocked(fixed(4)) == [0, 2]
    assert [d.value for d in s.dice] == [4, 1, 4]

def test_all_locked_roll_changes_nothing():
    s = dice.DiceSet([6, 8]); s.toggle_lock(0); s.toggle_lock(1)
    assert s.roll_unlocked(fixed(5)) == [] and [d.value for d in s.dice] == [1, 1]

def test_unlock_all():
    s = dice.DiceSet([6, 6]); s.toggle_lock(0); s.toggle_lock(1); s.unlock_all()
    assert not any(d.locked for d in s.dice)

def test_total_and_len():
    s = dice.DiceSet([6, 20, 4]); s.roll_unlocked(fixed(3))
    assert s.total() == 9 and len(s) == 3
```

- [ ] **Step 3: Run** `.venv/bin/pytest tests/test_dice.py -q` → FAIL (`No module named 'dice'`).
- [ ] **Step 4: Implement `apps/dice_roller/dice.py`** to the interface above.
- [ ] **Step 5: Run** `.venv/bin/pytest tests/test_dice.py -q` → 7 passed; `.venv/bin/ruff check --config vendor/tufty2350/ci/ruff.toml apps/dice_roller` → no errors; `.venv/bin/python -m mpy_cross -o /dev/null apps/dice_roller/dice.py` → no output.
- [ ] **Step 6: Commit** `git add .gitignore .gitmodules vendor/tufty2350 requirements-dev.txt apps tests && git commit -m "Add dev tooling, firmware submodule and dice model"`

---

### Task 2: `dice_config.py` (defaults and repair)

**Files:** Create `apps/dice_roller/dice_config.py`, `tests/test_dice_config.py`

**Interfaces:**
- Consumes: `dice.MIN_FACES`, `MAX_FACES`, `DEFAULT_FACES`, `MAX_DICE`.
- Produces: `STATE_NAME = "dice_roller"`, `MIN_COUNT = 1`, `MAX_COUNT = 6`, `DEFAULT_COUNT = 4`, `defaults() -> dict` (a fresh `{"count": 4, "faces": [6]*6}` each call), `repair(data) -> dict` (always a new valid dict, never raises, never mutates `data`).

Repair rules: a value is numeric if it is `int` or `float` and not `bool`; numeric → `int(value)` (truncates) then clamp; anything else → default (count 4, faces 6). `data` not a dict → `defaults()`. `faces` not a list → `[6]*6`; shorter → pad with 6; longer → first six.

- [ ] **Step 1: Write the failing tests**

```python
def test_defaults(): assert dice_config.defaults() == {"count": 4, "faces": [6] * 6}
def test_defaults_are_fresh(): a = dice_config.defaults(); a["faces"][0] = 9; assert dice_config.defaults()["faces"][0] == 6
def test_valid_kept(): d = {"count": 2, "faces": [4, 20, 6, 8, 10, 12]}; assert dice_config.repair(d) == d
def test_count_clamped(): assert [dice_config.repair({"count": c, "faces": [6]*6})["count"] for c in (0, -3, 7, 99)] == [1, 1, 6, 6]
def test_count_not_numeric(): assert [dice_config.repair({"count": c, "faces": [6]*6})["count"] for c in ("x", None, True, [3])] == [4, 4, 4, 4]
def test_faces_clamped(): assert dice_config.repair({"count": 6, "faces": [2, 50, 4, 20, 3, 21]})["faces"] == [4, 20, 4, 20, 4, 20]
def test_faces_padded_and_trimmed():
    assert dice_config.repair({"count": 1, "faces": [8]})["faces"] == [8, 6, 6, 6, 6, 6]
    assert dice_config.repair({"count": 1, "faces": [8] * 9})["faces"] == [8] * 6
def test_faces_bad_items(): assert dice_config.repair({"count": 1, "faces": ["d6", None, False, 7.9, 12, 6]})["faces"] == [6, 6, 6, 7, 12, 6]
def test_not_a_dict(): assert dice_config.repair("garbage") == dice_config.defaults()
def test_faces_not_a_list(): assert dice_config.repair({"count": 3, "faces": 8}) == {"count": 3, "faces": [6] * 6}
def test_missing_keys(): assert dice_config.repair({}) == dice_config.defaults()
def test_input_not_mutated(): d = {"count": 0, "faces": [1]}; dice_config.repair(d); assert d == {"count": 0, "faces": [1]}
```

- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_dice_config.py -q` → FAIL (no module).
- [ ] **Step 3: Implement** `defaults()` and `repair(data)` per the rules.
- [ ] **Step 4: Run** tests → 12 passed; ruff and mpy-cross clean on the new file.
- [ ] **Step 5: Commit** `"Add dice config defaults and repair"`

---

### Task 3: `dice_layout.py` (slot positions for any screen)

**Files:** Create `apps/dice_roller/dice_layout.py`, `tests/test_dice_layout.py`

**Interfaces:**
- Produces: `grid_slots(width: int, height: int) -> list[tuple[int, int, int]]`: six `(cx, cy, half)` tuples, row-major (slots 0–2 top row, 3–5 bottom), the home menu's 3×2 grid (160×120: centres x 32/80/128, y 42/90, squircle half-size 20) scaled to fit.

Formula (`s = min(width / 160, height / 120)`, `col = i % 3`, `row = i // 3`):
`cx = round(width / 2 + (col - 1) * 48 * s)`, `cy = round(height / 2 + (row * 48 - 18) * s)`, `half = round(20 * s)`.

- [ ] **Step 1: Write the failing tests**

```python
def test_tufty_hires():
    assert dice_layout.grid_slots(320, 240) == [(64, 84, 40), (160, 84, 40), (256, 84, 40), (64, 180, 40), (160, 180, 40), (256, 180, 40)]

def test_menu_lores_matches_menu():
    assert dice_layout.grid_slots(160, 120) == [(32, 42, 20), (80, 42, 20), (128, 42, 20), (32, 90, 20), (80, 90, 20), (128, 90, 20)]

def test_badger_fits_on_screen():
    for cx, cy, half in dice_layout.grid_slots(264, 176):
        assert cx - half >= 0 and cx + half <= 264 and cy - half >= 24 and cy + half <= 176
```

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → 3 passed; ruff and mpy-cross clean.
- [ ] **Step 5: Commit** `"Add grid layout for dice slots"`

---

### Task 4: `dice_input.py` (buttons → actions)

**Files:** Create `apps/dice_roller/dice_input.py`, `tests/test_dice_input.py`

**Interfaces:**
- Produces:
  - Button names: `A = "A"`, `B = "B"`, `C = "C"`, `UP = "UP"`, `DOWN = "DOWN"`.
  - Screens: `ROLL_SCREEN = "roll_screen"`, `CONFIG_SCREEN = "config_screen"`.
  - Actions: `LEFT = "left"`, `RIGHT = "right"`, `LOCK = "lock"`, `UNLOCK_ALL = "unlock_all"`, `ROLL = "roll"`, `CONFIGURE = "configure"`, `INC = "inc"`, `DEC = "dec"`, `ACCEPT = "accept"`.
  - `LONG_PRESS_MS = 800`, `STARTUP_IGNORE_MS = 400`.
  - `class InputMapper()` with `actions(screen: str, pressed: set, held: set, now: int) -> list[str]`. `pressed` = buttons that went down this frame; `held` = buttons down now.

Rules:
- The first call records `now` as the start. Until `now - start >= STARTUP_IGNORE_MS`, return `[]` and record nothing (a button down from launch never starts a long press).
- Roll screen: A→LEFT, C→RIGHT, UP pressed→LOCK, DOWN→ROLL, B→CONFIGURE. Config screen: A→LEFT, C→RIGHT, UP→INC, DOWN→DEC, B→ACCEPT.
- Several presses in one frame: actions in button order A, C, UP, DOWN, B, then any UNLOCK_ALL.
- Long press: a UP press (after the ignore window) records its time. While UP stays in `held` on the roll screen and `now - pressed_at >= LONG_PRESS_MS`, emit UNLOCK_ALL once for that hold. UP not in `held` clears the record.

- [ ] **Step 1: Write the failing tests**

```python
R, K = dice_input.ROLL_SCREEN, dice_input.CONFIG_SCREEN

def started():
    m = dice_input.InputMapper(); m.actions(R, set(), set(), 0); return m

def test_launch_press_ignored():
    m = dice_input.InputMapper()
    assert m.actions(R, {"B"}, {"B"}, 0) == []
    assert m.actions(R, {"B"}, {"B"}, 399) == []
    assert m.actions(R, {"B"}, {"B"}, 400) == [dice_input.CONFIGURE]

def test_up_held_from_launch_never_unlocks_all():
    m = dice_input.InputMapper(); m.actions(R, {"UP"}, {"UP"}, 0)
    assert all(m.actions(R, set(), {"UP"}, t) == [] for t in range(100, 3000, 100))

def test_roll_screen_mapping():
    m = started()
    got = [m.actions(R, {b}, {b}, 1000 + i)[0] for i, b in enumerate(["A", "C", "UP", "DOWN", "B"])]
    assert got == ["left", "right", "lock", "roll", "configure"]

def test_config_screen_mapping():
    m = started()
    got = [m.actions(K, {b}, {b}, 1000 + i)[0] for i, b in enumerate(["A", "C", "UP", "DOWN", "B"])]
    assert got == ["left", "right", "inc", "dec", "accept"]

def test_long_up_fires_once():
    m = started()
    assert m.actions(R, {"UP"}, {"UP"}, 1000) == ["lock"]
    assert m.actions(R, set(), {"UP"}, 1799) == []
    assert m.actions(R, set(), {"UP"}, 1800) == ["unlock_all"]
    assert m.actions(R, set(), {"UP"}, 2600) == []

def test_release_restarts_long_press():
    m = started()
    m.actions(R, {"UP"}, {"UP"}, 1000); m.actions(R, set(), set(), 1300)
    m.actions(R, {"UP"}, {"UP"}, 1400)
    assert m.actions(R, set(), {"UP"}, 2100) == []
    assert m.actions(R, set(), {"UP"}, 2200) == ["unlock_all"]

def test_no_unlock_all_on_config_screen():
    m = started(); m.actions(K, {"UP"}, {"UP"}, 1000)
    assert m.actions(K, set(), {"UP"}, 2000) == []

def test_same_frame_order():
    m = started()
    assert m.actions(R, {"B", "A", "DOWN"}, {"B", "A", "DOWN"}, 1000) == ["left", "roll", "configure"]
```

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → 8 passed; ruff and mpy-cross clean.
- [ ] **Step 5: Commit** `"Add button-to-action mapping with long press"`

---

### Task 5: `dice_app.py` (screens and state)

**Files:** Create `apps/dice_roller/dice_app.py`, `tests/test_dice_app.py`

**Interfaces:**
- Consumes: `dice.DiceSet`, `dice` and `dice_config` limits, `dice_input` screen and action constants.
- Produces: `class DiceApp(config: dict, randint)` where `config` is already repaired. Attributes read by displays: `screen`, `cursor`, `count`, `faces` (list of 6), `dice` (DiceSet), `changes` (int), `rolled` (list of indices), `rolled_at` (int or None). Methods: `apply(action: str, now: int) -> None`, `config() -> dict` (`{"count", "faces"}` copy), `take_save() -> dict | None`.

Behaviour:
- Init: copy count and faces; `dice = DiceSet(faces[:count])`; roll all; `rolled = []`, `rolled_at = None`; `screen = ROLL_SCREEN`; `cursor = 0`; `changes = 0`; remember `config()` as the saved snapshot.
- Roll screen: LEFT/RIGHT move `cursor` modulo `len(dice)`; LOCK toggles `dice[cursor]`; UNLOCK_ALL unlocks all; ROLL rolls unlocked and, only if any rolled, sets `rolled`/`rolled_at = now`; CONFIGURE → config screen, `cursor = 0`.
- Config screen: `cursor` 0 = count field, `k` ≥ 1 = die `k - 1`; LEFT/RIGHT modulo `count + 1`; INC/DEC on 0 change count clamped 1–6, on `k` change `faces[k-1]` clamped 4–20; ACCEPT: if `config()` differs from the snapshot, queue it for `take_save()` and update the snapshot; rebuild `dice` from `faces[:count]`, roll all, `rolled = list(range(count))`, `rolled_at = now`, `cursor = 0`, back to roll screen.
- An action that doesn't belong to the current screen does nothing. `changes` goes up by 1 for every action that changed anything visible, and not otherwise.

- [ ] **Step 1: Write the failing tests** with this helper (the stub returns `box[0]`, capped at `hi`; tests change `a.box[0]` to control later rolls):

```python
def make(count=4, faces=None, v=3):
    box = [v]
    a = dice_app.DiceApp(dice_config.repair({"count": count, "faces": faces or [6] * 6}),
                         lambda lo, hi: min(box[0], hi))
    a.box = box
    return a
```

```python
def test_starts_on_roll_screen():
    a = make(count=4)
    assert a.screen == ROLL_SCREEN and a.cursor == 0 and len(a.dice) == 4 and [d.value for d in a.dice.dice] == [3] * 4

def test_left_right_wrap():
    a = make(count=4); a.apply(LEFT, 1); assert a.cursor == 3
    a.apply(RIGHT, 2); assert a.cursor == 0

def test_right_crosses_rows():
    a = make(count=6); [a.apply(RIGHT, t) for t in range(3)]; assert a.cursor == 3

def test_lock_toggles_highlighted():
    a = make(); a.apply(RIGHT, 1); a.apply(LOCK, 2); assert a.dice.dice[1].locked
    a.apply(LOCK, 3); assert not a.dice.dice[1].locked

def test_roll_only_unlocked():
    a = make(count=3, v=3); a.apply(LOCK, 1)  # lock die 0
    a.box[0] = 5; a.apply(ROLL, 100)
    assert a.rolled == [1, 2] and a.rolled_at == 100
    assert [d.value for d in a.dice.dice] == [3, 5, 5]

def test_all_locked_roll_changes_nothing():
    a = make(count=2)
    a.apply(LOCK, 1); a.apply(RIGHT, 2); a.apply(LOCK, 3)
    before = (a.changes, a.rolled_at, [d.value for d in a.dice.dice])
    a.apply(ROLL, 500)
    assert (a.changes, a.rolled_at, [d.value for d in a.dice.dice]) == before

def test_unlock_all():
    a = make(); a.apply(LOCK, 1); a.apply(RIGHT, 2); a.apply(LOCK, 3); a.apply(UNLOCK_ALL, 4)
    assert not any(d.locked for d in a.dice.dice)

def test_configure_and_clamps():
    a = make(count=6); a.apply(CONFIGURE, 1); assert (a.screen, a.cursor) == (CONFIG_SCREEN, 0)
    a.apply(INC, 2); assert a.count == 6
    for t in range(10): a.apply(DEC, 3 + t)
    assert a.count == 1
    a.apply(RIGHT, 20); [a.apply(INC, 21 + t) for t in range(30)]; assert a.faces[0] == 20
    [a.apply(DEC, 60 + t) for t in range(30)]; assert a.faces[0] == 4

def test_config_cursor_wraps_over_count_plus_one():
    a = make(count=2); a.apply(CONFIGURE, 1); a.apply(LEFT, 2); assert a.cursor == 2

def test_hidden_dice_keep_faces():
    a = make(count=4, faces=[6, 6, 6, 12, 6, 6]); a.apply(CONFIGURE, 1)
    a.apply(DEC, 2); a.apply(INC, 3); assert a.faces[3] == 12 and a.count == 4

def test_accept_after_fewer_dice_resets_highlight():
    a = make(count=6); [a.apply(RIGHT, t) for t in range(5)]; assert a.cursor == 5
    a.apply(CONFIGURE, 10); a.apply(DEC, 11); a.apply(DEC, 12); a.apply(ACCEPT, 13)
    assert a.screen == ROLL_SCREEN and a.cursor == 0 and len(a.dice) == 4
    assert a.rolled == [0, 1, 2, 3] and a.rolled_at == 13 and not any(d.locked for d in a.dice.dice)
    a.apply(LOCK, 14)  # no IndexError

def test_take_save():
    a = make(count=4); assert a.take_save() is None
    a.apply(CONFIGURE, 1); a.apply(ACCEPT, 2); assert a.take_save() is None
    a.apply(CONFIGURE, 3); a.apply(INC, 4); a.apply(ACCEPT, 5)
    assert a.take_save() == {"count": 5, "faces": [6] * 6} and a.take_save() is None

def test_changes_counter():
    a = make(); c = a.changes
    a.apply(INC, 1); assert a.changes == c          # not a roll-screen action
    a.apply(RIGHT, 2); assert a.changes == c + 1
```

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → all pass; ruff and mpy-cross clean.
- [ ] **Step 5: Commit** `"Add dice app state and screen logic"`

---

### Task 6: Tufty display, entry point and icon

**Files:**
- Create: `apps/dice_roller/display_tufty.py`, `apps/dice_roller/__init__.py`, `tools/make_icon.py`, `apps/dice_roller/icon.png`, `tests/test_make_icon.py`

**Interfaces:**
- Consumes: `DiceApp` attributes (Task 5), `dice_layout.grid_slots`, `dice_input` constants, `dice_config.STATE_NAME/defaults/repair`.
- Produces (pinned for the simulator tests in Task 7):
  - `display_tufty.TuftyDisplay()` — sets `badge.mode(HIRES)`; `needs_redraw(app, now) -> True`; `draw(app, now) -> None`.
  - Colours (RGB): `BACKGROUND = (10, 10, 16)`, `ROLL_HEADER = (28, 28, 40)` filling y 0–39 on the roll screen, `CONFIG_HEADER = (20, 90, 160)` filling y 0–39 on the configure screen, `PALETTE = [(255, 140, 0), (40, 120, 255), (230, 50, 60), (40, 190, 80), (240, 210, 40), (150, 80, 220)]` for die bodies by slot, `LOCKED_BODY = (50, 50, 60)`, `HIGHLIGHT = (255, 255, 255)`.
  - Die body: rounded square of half-size `half` centred on the slot, radius 10. Highlight: a `HIGHLIGHT` rounded square of half-size `half + 4` drawn behind the highlighted die. Locked: body in `LOCKED_BODY` with a small "LOCK" tag in its bottom quarter. Nothing is drawn at the probe point `(cx - half + 8, cy - half + 8)` except the body fill. Header text starts at x ≥ 10 so the header probe `(4, 4)` sees only the header fill.
  - Slots with no die: nothing drawn (background).
  - Roll screen: value centred in the body, at least 40 px tall (pixel font at integer scale, centred with `measure_text`); `TOTAL n` and short hints in the header. During `ROLL_ANIM_MS = 500` after `app.rolled_at`, dice in `app.rolled` show `random.randint(1, faces)` each frame instead of their value.
  - Configure screen: `DICE n` in the header (highlight box around it when `cursor == 0`), each die body labelled `d<faces>`, highlight ring on die `cursor - 1`, hints `UP/DOWN change  B done`.

`__init__.py` (no tests of its own; covered by Task 7):
- Seed `random` from `os.urandom(4)` inside `try`.
- `BUTTONS = {BUTTON_A: "A", BUTTON_B: "B", BUTTON_C: "C", BUTTON_UP: "UP", BUTTON_DOWN: "DOWN"}`; `DISPLAYS = {"tufty": TuftyDisplay}`.
- `config = dice_config.defaults(); State.load(dice_config.STATE_NAME, config); config = dice_config.repair(config)`.
- `update()`: `now = badge.ticks`; build `pressed`/`held` name sets from `badge.pressed()`/`badge.held()`; feed `InputMapper.actions(app.screen, ...)` into `app.apply`; `State.save(STATE_NAME, cfg)` when `app.take_save()` returns a dict; `display.draw(app, now)`.
- Unknown `badge.model`: `update()` draws "Dice Roller: <model> not supported yet" and does nothing else.
- Last line: `run(update)`.

`tools/make_icon.py`: port `../claude-buddy-badgeware/tools/make_icon.py` (stdlib PNG writer, `build_png(rows) -> bytes`); ART = 24×24 orange rounded die (`#` = `(255, 140, 0, 255)`) with five white pips (`o`), `.` transparent; writes `apps/dice_roller/icon.png`.

- [ ] **Step 1: Failing test** `tests/test_make_icon.py`: `build_png(ART)` starts with `b"\x89PNG\r\n\x1a\n"` and its IHDR width/height are 24/24; `len(ART) == 24 and all(len(r) == 24 for r in ART)`. Run → FAIL.
- [ ] **Step 2: Implement** `tools/make_icon.py`, run `python3 tools/make_icon.py`; test → pass; `file apps/dice_roller/icon.png` → `PNG image data, 24 x 24`.
- [ ] **Step 3: Implement** `display_tufty.py` and `__init__.py`.
- [ ] **Step 4: Verify** `for f in apps/dice_roller/*.py; do .venv/bin/python -m mpy_cross -o /dev/null "$f"; done` → no output; ruff → clean; `.venv/bin/pytest -q` → all pass.
- [ ] **Step 5: Commit** `"Add Tufty display, app entry point and icon"`

---

### Task 7: Local simulator

**Files:**
- Create from `../MoodBadger2350/sim/` (read each before copying): `sim/boot.py`, `sim/index.html`, `sim/stage.py`, `sim/stubs/powman.py`, `sim/stubs/pcf85063a.py`, `sim/wasm/tufty/micropython.mjs`, `sim/wasm/tufty/micropython.wasm`
- Create: `sim/wasm/VERSION.json`, `sim/run_headless.mjs` (rewritten), `tests/test_sim.py`

**Interfaces:**
- Produces: `python3 sim/stage.py` → `sim/dist/tufty/` (+ `sim/dist/index.html`); `node sim/run_headless.mjs --model tufty --steps "B,UP:1200" --frames out.json`.
- `out.json`: `{"status": "ok" | "<error>", "width": 320, "height": 240, "frames": [[grey bytes]...], "log": [stdout/stderr lines]}`. `frames[0]` = the latest frame 500 ms after the first frame; `frames[i]` = the latest frame 500 ms after step `i` is released. Grey = round mean of R, G, B.
- Step syntax: comma-separated `NAME` or `NAME:ms` (hold time, default 150 ms), `NAME` ∈ A, B, C, UP, DOWN, HOME. Bitmask as MoodBadger's: HOME 0x20, A 0x10, B 0x08, C 0x04, UP 0x02, DOWN 0x01.
- `sim/wasm/VERSION.json`: `{"wasm": {"repo": "pimoroni/badgeware-wasm", "commit": "8cc5b05a1a07a823eb68ca1952b3603fe4d769bf", "run_id": 35841227054, "date": "2026-09-23"}, "firmware": {"tufty": "v3.1.1"}}` (the build MoodBadger2350 committed; see its `sim/wasm/SOURCE.md`).

Changes from MoodBadger's copies: `stage.py` `MODELS = ("tufty",)`, app tree `apps/dice_roller` → `/system/apps/dice_roller`, landing page title "Dice Roller Simulator"; `boot.py` launches `/system/apps/dice_roller`; `index.html` title and key help (`a`/`b`/`c`, ↑/↓, `h`).

- [ ] **Step 1: Port the files and stage.** Run `python3 sim/stage.py` → `staged N files in sim/dist/tufty`.
- [ ] **Step 2: Write `tests/test_sim.py`** (skip all if `node` missing; a module-scoped fixture stages once; helper `run(steps)` returns the parsed JSON; `grey(frame, x, y) = frame[y * 320 + x]`; slots from `dice_layout.grid_slots(320, 240)`; probe = `(cx - half + 8, cy - half + 8)`):

```python
def test_boots_to_four_dice():
    r = run("")
    f = r["frames"][0]
    assert r["status"] == "ok" and (r["width"], r["height"]) == (320, 240)
    assert not any("- ERROR" in line for line in r["log"])
    assert all(grey(f, *probe(i)) > 90 for i in range(4))
    assert all(grey(f, *probe(i)) < 30 for i in (4, 5))
    assert grey(f, 4, 4) < 50                       # roll header

def test_b_opens_configure_and_b_returns():
    f0, f1, f2 = run("B,B")["frames"]
    assert grey(f1, 4, 4) > 70 and grey(f2, 4, 4) < 50

def test_up_locks_highlighted_die():
    f0, f1 = run("UP")["frames"]
    assert grey(f0, *probe(0)) > 90 and grey(f1, *probe(0)) < 70 and grey(f1, *probe(1)) > 90

def test_long_up_unlocks_all():
    frames = run("UP,C,UP,UP:1200")["frames"]
    assert grey(frames[3], *probe(0)) < 70
    assert grey(frames[4], *probe(0)) > 90 and grey(frames[4], *probe(1)) > 90

def test_configure_five_dice():
    f = run("B,UP,B")["frames"][-1]
    assert grey(f, *probe(4)) > 90 and grey(f, *probe(5)) < 30

def test_rolling_does_not_error():
    r = run("DOWN,DOWN,DOWN")
    assert r["status"] == "ok" and not any("- ERROR" in line for line in r["log"])
```

- [ ] **Step 3: Write `sim/run_headless.mjs`** to the interface above (start from MoodBadger's runner: same host functions `blitrgba`, `sim_buttons`, `sim_gpio_get`, manifest loading, 60 s timeout).
- [ ] **Step 4: Run** `.venv/bin/pytest tests/test_sim.py -v` → 6 passed. If a pixel check fails, write that frame to PGM → PNG (as MoodBadger's `badge-verify` skill shows) and look at it before changing code or thresholds.
- [ ] **Step 5: Look** `python3 -m http.server -d sim/dist 8000`, open `http://localhost:8000/tufty/`, try every button on both screens (Claude in Chrome if connected, otherwise ask the user).
- [ ] **Step 6: Commit** `"Add local badgeware-wasm simulator and simulator tests"`

---

### Task 8: Simulator update tool

**Files:** Create `tools/update_sim.py`, `tests/test_update_sim.py`

**Interfaces:**
- Consumes: `sim/wasm/VERSION.json` (Task 7), `sim/stage.py`.
- Produces (stdlib only; all `gh` calls go through one function so tests can replace it):
  - `gh_json(args: list[str]) -> object` — runs `gh <args>` and parses stdout as JSON.
  - `latest_build_run(runs: list[dict]) -> dict | None` — newest (`createdAt`) run with `workflowName == "build"`, `headBranch == "main"`, `conclusion == "success"`; input is `gh run list -R pimoroni/badgeware-wasm --json databaseId,headSha,headBranch,workflowName,conclusion,createdAt --limit 30`.
  - `latest_release_tag(releases: list[dict]) -> str | None` — newest (`publishedAt`) not `isPrerelease`, not `isDraft`; input is `gh release list -R pimoroni/<model>2350 --json tagName,isPrerelease,isDraft,publishedAt`.
  - `artifact_name(model: str) -> str` → `"badgeware-<model>2350-asyncify"`.
  - `main(argv: list[str]) -> int`:
    - `--check`: print pinned vs latest for the wasm run and each model's firmware; return 0 if all current, 1 if anything newer.
    - default (update): for each model in `VERSION.json["firmware"]`: `gh run download -R pimoroni/badgeware-wasm <run> -n <artifact> -D <tmpdir>`; require `micropython.mjs` and `micropython.wasm` in it, else stop with an error and change nothing; replace `sim/wasm/<model>/`; `git -C vendor/<model>2350 fetch --tags` and `checkout <tag>`; rewrite `VERSION.json` (commit = run's `headSha`, `run_id`, `date` = `createdAt[:10]`); run `sim/stage.py`; print the next step: `.venv/bin/pytest tests/test_sim.py`.
    - `--run ID` and `--firmware-tag TAG` override the "latest" choices.
    - `gh` missing or not logged in: print how to fix (`gh auth login`) and return 2.

- [ ] **Step 1: Write the failing tests**

```python
RUNS = [
  {"databaseId": 1, "headSha": "a", "headBranch": "main", "workflowName": "build", "conclusion": "success", "createdAt": "2026-09-11T00:00:00Z"},
  {"databaseId": 2, "headSha": "b", "headBranch": "v3.1.0", "workflowName": "build", "conclusion": "success", "createdAt": "2026-09-24T00:00:00Z"},
  {"databaseId": 3, "headSha": "c", "headBranch": "main", "workflowName": "build", "conclusion": "failure", "createdAt": "2026-09-25T00:00:00Z"},
  {"databaseId": 4, "headSha": "d", "headBranch": "main", "workflowName": "build", "conclusion": "success", "createdAt": "2026-09-23T00:00:00Z"},
]
def test_latest_build_run(): assert update_sim.latest_build_run(RUNS)["databaseId"] == 4
def test_latest_build_run_none(): assert update_sim.latest_build_run([]) is None
def test_latest_release_tag():
    rel = [{"tagName": "v4.0.0-ide.1", "isPrerelease": True, "isDraft": False, "publishedAt": "2026-10-05T00:00:00Z"},
           {"tagName": "v3.1.1", "isPrerelease": False, "isDraft": False, "publishedAt": "2026-09-23T00:00:00Z"},
           {"tagName": "v3.1.0", "isPrerelease": False, "isDraft": False, "publishedAt": "2026-09-14T00:00:00Z"}]
    assert update_sim.latest_release_tag(rel) == "v3.1.1"
def test_artifact_name(): assert update_sim.artifact_name("tufty") == "badgeware-tufty2350-asyncify"
def test_check_current_returns_0(monkeypatch, capsys): ...   # gh_json stubbed to return runs whose newest main success is run_id 35841227054 and release v3.1.1 → 0
def test_check_newer_returns_1(monkeypatch, capsys): ...     # newer run → 1, and stdout names both the pinned and the new run id
def test_download_missing_files_changes_nothing(monkeypatch, tmp_path): ...  # stub the download to produce an empty dir → non-zero exit, VERSION.json and sim/wasm untouched
```

(For the three `main` tests, point the tool at a temp copy of `sim/wasm` via a module-level `ROOT` the tests monkeypatch.)

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** `.venv/bin/pytest tests/test_update_sim.py -q` → 7 passed; then `python3 tools/update_sim.py --check` against the real repos → prints both versions and exits 0 or 1 (report which).
- [ ] **Step 5: Commit** `"Add simulator and firmware update tool"`

---

### Task 9: Install tool and README

**Files:** Create `tools/install.py`, `tests/test_install.py`, `README.md`

**Interfaces:**
- `tools/install.py`: port `../claude-buddy-badgeware/tools/install.py` with `APP = "dice_roller"`; same flags (`--dest`, `--no-eject`), same drive detection (`apps/` and `main.py` at the drive root; labels include `TUFTY`); copies `apps/dice_roller/` to `<drive>/apps/dice_roller/`, skipping `__pycache__`.

- [ ] **Step 1: Failing test** `tests/test_install.py`: make a fake drive in `tmp_path` (`apps/`, `main.py`), run `main` with `["--dest", str(tmp_path), "--no-eject"]` (patch `sys.argv`) → every `.py` and `icon.png` from `apps/dice_roller` exists under `tmp_path/apps/dice_roller`, and no `__pycache__` does. Run → FAIL.
- [ ] **Step 2: Implement**; test passes.
- [ ] **Step 3: Write `README.md`**: what it is; buttons table for both screens (from the spec); saved config file and its shape; install (double-tap RESET → `TUFTY` drive → `python3 tools/install.py` → eject → choose **Dice Roller**); development (venv, pytest, ruff, mpy-cross commands from Global Constraints); simulator (stage, browser page and keys, headless runner); updating the simulator (`tools/update_sim.py --check`, then without `--check`, then run the simulator tests, then commit `sim/wasm` and `vendor/tufty2350`); project layout; adding a badge (new `display_<model>.py` + one line in `DISPLAYS`, plus its wasm build and firmware submodule); licence and credits (badgeware-wasm build is Pimoroni's, MIT).
- [ ] **Step 4: Full check** `.venv/bin/pytest -q` → all pass (simulator tests included); ruff and mpy-cross clean.
- [ ] **Step 5: Commit** `"Add install tool and README"`
