# Dice Roller for Badgeware

A dice app for Pimoroni's [Tufty 2350](https://shop.pimoroni.com/products/tufty-2350)
badge (Badgeware firmware). Roll two to six dice, each with 4 to 20 faces,
lock the ones you want to keep, and reroll the rest, Yahtzee-style.

It is built so the Badger 2350 and Blinky 2350 can be added later by
writing one display file each (see [Adding a badge](#adding-a-badge)).

## Buttons

### Roll screen (where the app starts)

| Button | Action |
| --- | --- |
| A / C | Move the highlight left / right; wraps across both rows |
| UP | Lock the highlighted die (press again to unlock it) |
| UP, held about a second | Unlock all dice |
| DOWN | Roll every unlocked die |
| B | Open the configure screen |

The header shows the total. Locked dice are dark grey and labelled `LOCK`.

### Configure screen

| Button | Action |
| --- | --- |
| A / C | Move between the dice count and each die |
| UP / DOWN | Increase / decrease what is highlighted |
| B | Accept and go back to rolling (a fresh roll, all dice unlocked) |

Dice count: 2–6. Faces per die: 4–20. Values stop at the ends rather than
wrapping. The dice are spread evenly in rows spaced like the home menu's
icons: 2 or 3 in one row, 4 as 2+2, 5 as 3+2, 6 as 3+3.

HOME always returns to the Badgeware menu.

## Saved setup

The configuration is saved when you accept it, in `/state/dice_roller.json`
on the badge:

```json
{ "count": 4, "faces": [6, 6, 6, 6, 6, 6] }
```

`faces` holds all six dice, so lowering the count and raising it again
brings dice back as they were. The first launch uses 4 six-sided dice. A
hand-edited or damaged file is repaired on load (values pulled into range,
anything unreadable replaced by the defaults). Rolls and locks are not
saved.

## Install

1. Connect the Tufty with a USB-C data cable and **double-tap RESET** on
   the back. It mounts as a drive named `TUFTY`.
2. Run `python3 tools/install.py`. It finds the drive, copies
   `apps/dice_roller/` into its `apps/` folder, and on macOS and Linux
   ejects it. (Or copy the folder by hand, then eject.)
3. The badge restarts into the menu. Choose **Dice Roller**.

Always eject before pressing RESET or unplugging, or files on the badge
can be cut short.

## Development

```sh
git submodule update --init          # vendor/tufty2350: Pimoroni's firmware, pinned to a release
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
```

| Task | Command |
| --- | --- |
| All tests (unit + simulator) | `.venv/bin/pytest` |
| Lint the app with Pimoroni's rules | `.venv/bin/ruff check --config vendor/tufty2350/ci/ruff.toml apps/dice_roller` |
| Lint tools and tests | `.venv/bin/ruff check tools tests` |
| Check MicroPython syntax | `for f in apps/dice_roller/*.py; do .venv/bin/python -m mpy_cross -o /dev/null "$f"; done` |
| Regenerate the icon | `python3 tools/make_icon.py` |

The simulator tests need Node (18 or later) and are skipped without it.

### Project layout

```
apps/dice_roller/        the app (copied to the badge)
  __init__.py            entry: picks the display from badge.model, buttons, saving
  dice.py                Die and DiceSet                      (plain Python)
  dice_config.py         saved-setup defaults and repair      (plain Python)
  dice_app.py            the two screens and their state      (plain Python)
  dice_input.py          buttons -> actions, long press       (plain Python)
  dice_layout.py         where dice go on any screen size     (plain Python)
  display_tufty.py       drawing on the Tufty (the only Tufty-specific file)
  icon.png               24x24 menu icon (tools/make_icon.py)
sim/                     local simulator (below)
tests/                   pytest: every plain-Python file, plus the simulator
tools/install.py         copy the app to the badge's USB drive
tools/make_icon.py       regenerate icon.png
tools/update_sim.py      check for and pull newer simulator builds and firmware
vendor/tufty2350         Pimoroni's Tufty firmware (git submodule)
docs/superpowers/        design and implementation plan
```

### Simulator

`sim/` runs the real Tufty firmware Python and the unmodified app inside
Pimoroni's WebAssembly MicroPython build from
[pimoroni/badgeware-wasm](https://github.com/pimoroni/badgeware-wasm).

```sh
python3 sim/stage.py                       # builds sim/dist/ (not committed)
python3 -m http.server -d sim/dist 8000    # then open http://localhost:8000/tufty/
```

Click the page, then use `a`, `b`, `c` for A, B, C, the arrow keys for
UP and DOWN, and `h` for HOME.

Headless, for tests and quick checks:

```sh
node sim/run_headless.mjs --model tufty --steps "B,UP,B,DOWN,UP:1200" --frames out.json
```

`--steps` is a comma-separated list of buttons, each optionally with a
hold time in milliseconds. `out.json` holds a 320×240 grey frame after
each step, plus the app's console output. `tests/test_sim.py` checks
pixels in these frames.

The simulator doesn't model sleep, battery power or the real screen's
colours, so check those on a badge.

### Updating the simulator

`sim/wasm/VERSION.json` records which badgeware-wasm build and which
firmware release are in use. badgeware-wasm publishes the build the
simulator needs only as a CI artifact, which GitHub deletes after 90
days, so the downloaded build is committed here.

```sh
python3 tools/update_sim.py --check   # pinned vs latest; exits 1 if newer
python3 tools/update_sim.py           # download the newest build, move the firmware submodule, re-stage
.venv/bin/pytest                      # does the app still work on the new versions?
git add sim/wasm vendor && git commit -m "Update simulator to ..."
```

It needs the [GitHub CLI](https://cli.github.com), logged in (`gh auth
login`). `--run <id>` and `--firmware-tag <tag>` pick specific versions.

### Adding a badge

1. Write `apps/dice_roller/display_<model>.py` with a class that has
   `draw(app, now)` and `needs_redraw(app, now)`. Read `display_tufty.py`
   for what `app` provides; `app.changes` goes up on every visible
   change, so an e-ink display (Badger) can redraw only then.
2. Add it to `DISPLAYS` in `apps/dice_roller/__init__.py`.
3. For the simulator: `git submodule add https://github.com/pimoroni/<model>2350 vendor/<model>2350`,
   run `python3 tools/update_sim.py --models tufty,<model>`, and add the
   model to `MODELS` in `sim/stage.py` and `sim/run_headless.mjs`.

### Claude Code

The repository carries Claude Code skills in `.claude/skills/` (the
Superpowers set and Anthropic's skill-creator; sources and licences in
`.claude/skills/README.md`). A start-up hook in `.claude/settings.json`
loads the `using-superpowers` skill into each session.

## Licence and credits

- `sim/wasm/` is Pimoroni's MIT-licensed
  [badgeware-wasm](https://github.com/pimoroni/badgeware-wasm) build;
  `vendor/tufty2350` keeps its own licence.
- `tools/install.py` and `tools/make_icon.py` are adapted from
  claude-buddy-badgeware; the simulator loader follows the approach of
  MoodBadger2350's `sim/`.
- Button layout and menu spacing follow Pimoroni's Badgeware launcher.
