---
name: badge-verify
description: How to test and verify a Dice Roller change on both badges (Tufty 2350 colour LCD and Badger 2350 e-ink) - which test layers a change needs, the exact commands (pytest with its fake badges, ruff and mpy-cross, the headless badgeware-wasm simulator for each badge and turning its frames into images, the browser simulator, tools/update_sim.py --check), and the real-hardware checks (badge_info, install, checking the copy from the badge's side) with a hand checklist for each badge. Use it whenever you change apps/dice_roller, tools/ or sim/, bump firmware or the simulator, finish a feature, prepare or review a PR, or the user asks to test, verify, smoke-test, check on the badge, "make sure it still works on the Badger", or try something in the simulator - even if they only say "is it done?". For the install itself use badge-deploy; for firmware, badge-firmware.
---

# Verifying a Dice Roller change on both badges

A change isn't done until it has passed every layer it can break. The
layers get slower and need more of the user's time as you go down; each
catches things the one above can't. Run them in this order and stop to
fix anything that fails before moving on.

Read the `badgeware-platforms` skill first if the change touches app
code: most cross-badge bugs come from the run loop, screen and sleep
differences listed there.

(Adapted from freemansoft/MoodBadger2350.)

## Which layers a change needs

| Change                                                    | Layers                                                                 |
| --------------------------------------------------------- | ---------------------------------------------------------------------- |
| `game/` rules, `saving/record.py`                         | 1, 2                                                                   |
| `devices/tufty.py` or `devices/badger.py` (drawing, look) | 1-4 (look at that badge's page), then 6 on that badge                  |
| `__init__.py`, `devices/buttons.py`, `game/controls.py`   | 1-4 on both pages, then 6 on both badges                               |
| `saving/store.py`, the saved record's format              | 1-3, then 6 (restart, and sleep on the Badger)                         |
| `tools/install.py`, `badge_*.py`, `flash_firmware.py`     | 1, 2, then the tool once against a real badge                          |
| `sim/`                                                    | 1-4                                                                    |
| Simulator or firmware bump (`sim/wasm`, `vendor/*`)       | all, on both badges, after re-checking the `badgeware-platforms` table |

## 1. Unit tests (seconds)

```bash
.venv/bin/pytest -q
```

This includes layer 3 when `node` is installed (skipped without it). The
host tests load the real modules with small fakes written in each test
file, not a shared fake firmware:

- `tests/test_dice.py`, `test_app.py`, `test_controls.py`,
  `test_layout.py`, `test_record.py`: the game and the saved record,
  plain Python.
- `tests/test_entry.py`: `apps/dice_roller/__init__.py` with stand-ins
  for the Badgeware builtins, driven frame by frame.
- `tests/test_tufty_display.py`, `test_badger_display.py`: each display
  against a fake badge (when the Badger refreshes, polls and waits).
- `tests/test_install.py`, `test_badge_tools.py`, `test_badge_check.py`,
  `test_update_sim.py`: the tools, with no badge, drive or network.
- `tests/test_readme.py`, `test_platform_skill.py`,
  `test_prettier_version.py`, `test_ruff_config.py`: the docs and
  configs.

Write the failing test before the change (superpowers TDD). A test that
passes before the change tests nothing. Don't pipe pytest into `tail`
or `grep` without `set -o pipefail`: the pipe hides a failure.

## 2. Lint and MicroPython syntax (seconds)

```bash
.venv/bin/ruff check .
find apps/dice_roller -name '*.py' -print0 | xargs -0 -n1 .venv/bin/python -m mpy_cross -o /dev/null
```

CPython accepts things MicroPython doesn't; mpy-cross catches them. The
ruff config extends Pimoroni's `vendor/tufty2350/ci/ruff.toml`, which
lists Badgeware's builtins, so an undefined name is an error. It covers
the whole repository, not only the app. `ruff format` is not used.

If the change touches Markdown, also run
`npx --yes prettier@$(cat .prettier-version) --config .prettierrc.json --check <files>`
(see the `dice-docs` skill). The pre-commit hook runs ruff, mpy-cross
and prettier on what is staged, and CI runs all of layers 1 and 2.

## 3. Headless simulator (seconds per run)

```bash
python3 sim/stage.py
node sim/run_headless.mjs --model tufty --steps "B,UP,B,DOWN" --frames /tmp/tufty.json
node sim/run_headless.mjs --model badger --steps "UP,DOWN" --frames /tmp/badger.json
```

This runs the real firmware Python and the unmodified app in Pimoroni's
badgeware-wasm builds (`sim/wasm/<model>/`). `--steps` takes button
names, each with an optional hold in ms (`UP:1200`); `--state` starts
from a saved record, as after a restart or a Badger wake. The JSON has
`status`, `width`, `height`, `frames` (RGB, one after launch and one per
step), `refreshes` per step, the saved `state` and the app's `log` (a
crash prints `- ERROR:`). `tests/test_sim.py` (Tufty) and
`tests/test_sim_badger.py` (Badger) check pixels in these frames through
`tests/simrun.py`.

To look at a frame without a browser, write it as an image and read it:

```bash
python3 - <<'EOF'
import json
d = json.load(open("/tmp/badger.json"))
open("/tmp/frame.ppm", "wb").write(b"P6 %d %d 255\n" % (d["width"], d["height"]) + bytes(d["frames"][-1]))
EOF
sips -s format png /tmp/frame.ppm --out /tmp/frame.png   # macOS; then Read the PNG
```

Use the session's scratchpad instead of `/tmp` when there is one.

## 4. Browser simulator (the user looks)

```bash
python3 sim/stage.py && python3 -m http.server -d sim/dist 8000
```

Open `http://localhost:8000/tufty/` and `/badger/`. Click the page, then
`a`, `b`, `c` are A, B, C, the arrow keys UP and DOWN, `h` HOME. If a
browser tool is connected, check both pages yourself; otherwise ask the
user to look. The simulator doesn't model sleep, battery power, the
e-ink refresh time or the real screen's colours; those need layer 6.

## 5. Simulator and firmware versions

```bash
python3 tools/update_sim.py --check
```

Compares the pinned badgeware-wasm build and firmware tag
(`sim/wasm/VERSION.json`) with the latest; exits 1 if newer ones exist.
It needs the GitHub CLI, logged in. A newer build is a separate change
(README, "Updating the simulator"), not part of the current one: report
it and offer it.

## 6. Real badges (the user's hands)

Use the `badge-deploy` skill for the install (it checks the firmware
first and hands off to `badge-firmware` if it is old).

- **Two badges plugged in:** the tools ask for `--port`; `mpremote devs`
  names each one (`Tufty 2350`, `Badger 2350`). A Badger on battery
  sleeps and drops off USB: ask the user to plug it in and press RESET.
- **Every badge tool ends with `machine.reset()`.** A Badger then
  reopens the app it was showing; a Tufty shows the menu. Don't read the
  badge while the user is checking what the screen shows: ask first,
  then read.

Steps:

1. `.venv/bin/python tools/badge_info.py`: model, firmware current,
   whether the Dice Roller is installed, the saved dice.
2. Install with the `badge-deploy` skill. Expect "Installed and checked
   N files" and "Ejected".
3. Check the copy from the badge's side:
   `.venv/bin/python tools/badge_check.py files`. Expect "The badge's
   copy matches." and no "missing", "different size", "not in the app"
   or "macOS junk" lines.
4. Hand checklist below, for each badge the change can affect. Ask the
   user to report anything that looks wrong at each step.

### Tufty 2350 checklist

1. Choose **Dice Roller** in the menu: the last roll comes back, locks
   included; the B press that opened it didn't also open Setup.
2. Labels sit beside the buttons: Left, Setup, Right along the bottom,
   Lock and Roll beside UP and DOWN.
3. A and C move the highlight, wrapping across both rows.
4. UP locks (grey, `LOCK`); UP again unlocks; UP held about a second
   unlocks all.
5. DOWN rolls only the unlocked dice; they and the total flicker for
   about half a second, then settle.
6. B opens Setup; A/C move, UP/DOWN change the count (2-6) and faces
   (4-20), stopping at the ends; B accepts with a fresh roll.
7. HOME opens the menu; reopen the app: the roll is as it was.
8. Colours look right on the real screen (dark red dice, grey locked).

### Badger 2350 checklist

1. Open **Dice Roller**: the last roll comes back, locks included.
2. Each press gives one full refresh of about a second, straight to the
   final dice and total (no animation); a press during a refresh is
   dropped.
3. A/C move, UP locks, DOWN rolls, B opens Setup and accepts.
4. Hold UP until the screen has changed twice: all dice unlock.
5. The four greys read clearly: white dice, grey locked dice, black
   title bar, dark grey Setup title bar.
6. Unplug USB and wait over 30 s: the badge sleeps. Any button wakes it
   where it was, locks included, and that press doesn't also roll.
7. HOME opens the menu.

## Reporting

Say which layers ran and their results (test counts, the firmware
verdict, the badge-side file check, which checklist items the user
confirmed), and name any layer you skipped and why. In a PR's test
plan, tick only what actually ran.
